"""Local robot observatory; all motor writes stay on existing SDK-owner threads."""
import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging
from pathlib import Path
import struct
import threading
import time
from typing import Literal

import cv2
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import trossen_arm as arm

import robot_camera
from geometry import forward
from puppet import LeftPair
from presets import Presets

LOGGER = logging.getLogger("observatory")
WIDTH, HEIGHT, FPS = 640, 480, 30
JPEG_QUALITY = 78
TELEMETRY_HZ = 20
ACK_TIMEOUT_SECONDS = 5
STATS_WINDOW_SECONDS = 3
SERIAL_ROLES = {"left": "418643070450", "right": "418643070460", "top": "418643070452"}
ARMS = {"leader_right": "192.168.1.2", "leader_left": "192.168.1.3",
        "follower_right": "192.168.1.4", "follower_left": "192.168.1.5"}


@dataclass
class Feed:
    """Mutable capture/encoder state; one replaceable frame per stage, never a FIFO."""
    device: dict
    raw: object = None
    jpeg: object = None
    event: threading.Event = field(default_factory=threading.Event)
    capture_fps: float = 0
    encode_ms: float = 0
    ack_age_ms: float = 0
    frames: int = 0
    error: str | None = None


def assign_roles(devices):
    """
    Pure function. Match known serials, then the single remaining camera as bottom.

    Args:
        devices (list[dict]): Discovered D405 records, including serial or session UID.
    Returns:
        dict: Role to device mapping; raises on missing/extra/ambiguous cameras.
    Examples:
        >>> devices = [{'serial': s} for s in SERIAL_ROLES.values()] + [{'serial': 'fourth'}]
        >>> assign_roles(devices)['bottom']['serial']
        'fourth'
    """
    if len(devices) != 4:
        raise ValueError(f"Expected four D405 cameras; found {devices}")
    roles = {role: robot_camera.select_camera(devices, serial) for role, serial in SERIAL_ROLES.items()}
    remaining = [device for device in devices if device.get("serial") not in SERIAL_ROLES.values()]
    roles["bottom"] = robot_camera.select_camera(remaining)
    return roles


class Observatory:
    """Camera and robot owner; HTTP only queues exclusive operator intent."""

    def __init__(self):
        """Command. Create stop state and empty telemetry, without opening hardware."""
        self.stop = threading.Event()
        self.feeds = {}
        self.arms = {}
        self.threads = []
        self.presets = Presets(self.stop)
        self.pair = LeftPair(self.stop, self.publish, self.presets)
        self.right_pair = LeftPair(self.stop, self.publish, self.presets, side="right")
        self.presets.pair = self.pair
        self.presets.pairs = {"left": self.pair, "right": self.right_pair}

    def start(self):
        """Command. Discover four cameras and start capture, encoder and arm-query threads."""
        self.feeds = {role: Feed(device) for role, device in assign_roles(robot_camera.discover()).items()}
        for role, feed in self.feeds.items():
            self.launch(self.capture, role, feed)
            self.launch(self.encode, role, feed)
        for role, ip in ARMS.items():
            self.arms[role] = {"ip": ip, "error": None, "ready": False}
        self.launch(self.pair.run)
        self.launch(self.right_pair.run)

    def launch(self, function, *args):
        """
        Command. Start a tracked worker; errors are reported by worker boundaries.

        Args: function: worker command; args: positional arguments.
        Returns: None; launch(self.capture, 'top', feed) starts one capture thread.
        """
        thread = threading.Thread(target=function, args=args, daemon=True)
        self.threads.append(thread)
        thread.start()

    def capture(self, role, feed):
        """
        Command. Continuously replace a BGR frame slot; report any capture failure.

        Args: role (str): camera label; feed (Feed): owned raw state.
        Returns: None; frame shape is (480, 640, 3) uint8 BGR, channels (B,G,R).
        """
        recent = deque()
        try:
            serial = feed.device.get("serial")
            uid = feed.device.get("uid") if serial is None else None
            with robot_camera.open_camera(serial, uid, WIDTH, HEIGHT, FPS) as camera:
                while not self.stop.is_set():
                    image = robot_camera.read_bgr(camera, WIDTH, HEIGHT)
                    now = time.monotonic()
                    recent.append(now)
                    while len(recent) > 2 and now - recent[0] > STATS_WINDOW_SECONDS:
                        recent.popleft()
                    feed.frames += 1
                    feed.raw = (feed.frames, now, image)
                    if len(recent) > 1:
                        feed.capture_fps = (len(recent)-1)/(recent[-1]-recent[0])
                    feed.event.set()
        except Exception as error:
            feed.error = str(error)
            LOGGER.exception("Camera %s stopped", role)

    def encode(self, role, feed):
        """
        Command. Encode newest unseen BGR frame to a single replaceable JPEG slot.

        Args: role (str): label; feed (Feed): raw/JPEG state. Input is (480,640,3) BGR.
        Returns: None; feed.jpeg becomes (sequence, read_time, JPEG bytes).
        """
        seen = 0
        try:
            while not self.stop.is_set():
                if not feed.event.wait(0.1):
                    continue
                feed.event.clear()
                sequence, captured, image = feed.raw
                if sequence == seen:
                    continue
                before = time.monotonic()
                success, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                if not success:
                    raise RuntimeError("JPEG encoding failed")
                feed.encode_ms = (time.monotonic()-before)*1000
                feed.jpeg = (sequence, captured, jpeg.tobytes())
                seen = sequence
        except Exception as error:
            feed.error = str(error)
            LOGGER.exception("Encoder %s stopped", role)

    def publish(self, role, driver):
        """
        Command. Publish one owner's current joint/FK telemetry after consistency checks.

        Args: role (str): arm label; driver: exclusively owned connected SDK instance.
        Returns: None; writes (9,3) XYZ frame origins and (4,4) tool transform into arms[role].
        """
        joints = list(driver.get_arm_positions())
        points, tool = forward(joints)
        controller = list(driver.get_cartesian_positions())
        difference = max(abs(a-b) for a, b in zip(tool[:3, 3], controller[:3]))
        error = driver.get_error_information()
        if error != "No error":
            raise RuntimeError(error)
        if difference > 0.005:
            raise RuntimeError(f"FK/controller mismatch {difference:.4f} meters")
        self.arms[role] = {"ip": ARMS[role], "ready": True, "error": None, "at": time.monotonic(),
            "joints": joints, "gripper": driver.get_gripper_position(),
            "modes": [str(mode).split(".")[-1] for mode in driver.get_modes()],
            "points": points.tolist(), "tool": tool.tolist(), "fk_error_m": difference,
            "limits": [{"min": limit.position_min, "max": limit.position_max}
                       for limit in driver.get_joint_limits()[:6]]}

    def telemetry(self, role, ip):
        """
        Command. Own one SDK connection and publish joint/FK reads and execute queued arm presets.

        Args: role (str): arm role; ip (str): controller IP.
        Returns: None; publishes six angles and (9,3) frame origins in local base coordinates.
        """
        driver = arm.TrossenArmDriver()
        configured = False
        failed = False

        def sdk(method, *args):
            """Command. Retire a failed SDK instance. Args: method, args: SDK call. Returns: SDK result."""
            nonlocal failed
            if failed:
                raise RuntimeError("Driver failed; restart required")
            try:
                return getattr(driver, method)(*args)
            except Exception:
                failed = True
                raise

        try:
            preset = getattr(arm.StandardEndEffector, "wxai_v0_leader" if role.startswith("leader") else "wxai_v0_follower")
            driver.configure(arm.Model.wxai_v0, preset, ip, False, 5.0)
            configured = True
            self.presets.connected(role)
            while not self.stop.is_set():
                self.presets.tick(role, sdk)
                self.publish(role, driver)
                self.stop.wait(1/TELEMETRY_HZ)
        except Exception as error:
            failed = True
            self.presets.unavailable(role, error)
            self.arms[role] = {"ip": ip, "ready": False, "error": str(error)}
            LOGGER.exception("Robot telemetry %s stopped", role)
        finally:
            if configured:
                try:
                    if not failed:
                        self.presets.halt(role, sdk, "Server stopped")
                except Exception as error:
                    self.presets.unavailable(role, error)
                    LOGGER.exception("Robot preset stop %s failed", role)
                try:
                    driver.cleanup()
                except Exception as error:
                    self.arms[role] = {"ip": ip, "ready": False, "error": f"Cleanup: {error}"}
                    self.presets.unavailable(role, error)
                    LOGGER.exception("Robot cleanup %s failed", role)
            self.presets.unavailable(role, "Owner stopped")

    def snapshot(self):
        """
        Query. Read current telemetry and measured stream statistics.

        Returns: dict with cameras/arms; rates are measured, not nominal configuration.
        """
        now = time.monotonic()
        return {"now": now, "profile": {"width": WIDTH, "height": HEIGHT, "target_fps": FPS},
                "cameras": {role: {"device": feed.device, "capture_fps": feed.capture_fps,
                    "encode_ms": feed.encode_ms, "ack_age_ms": feed.ack_age_ms,
                    "frames": feed.frames, "age_ms": (now-feed.jpeg[1])*1000 if feed.jpeg else None,
                    "error": feed.error} for role, feed in self.feeds.items()},
                "arms": {role: ({**state, "ready": False, "error": "Telemetry stale"}
                                if state.get("ready") and now-state["at"] > 0.5 else dict(state))
                         for role, state in self.arms.items()},
                "presets": self.presets.snapshot(), "puppet": self.pair.snapshot(), "puppet_right": self.right_pair.snapshot()}

    def close(self):
        """Command. Stop workers and release owned cameras/robot connections."""
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=20)
            if thread.is_alive():
                LOGGER.error("Worker %s did not stop within 20 seconds", thread.name)


hub = Observatory()


@asynccontextmanager
async def lifespan(app):
    """
    Command. Start/stop hardware ownership with the web server lifecycle.

    Args: app: FastAPI instance.
    Yields: None after workers start.
    """
    await asyncio.to_thread(hub.start)
    try:
        yield
    finally:
        await asyncio.to_thread(hub.close)


app = FastAPI(lifespan=lifespan)


@app.get("/api/status")
async def status():
    """Query. Return measured camera rates and arm telemetry as a JSON dictionary."""
    return hub.snapshot()


@app.get("/api/camera/{role}/snapshot.jpg")
async def snapshot(role: str):
    """
    Query. Return newest JPEG or an explicit unavailable response.

    Args: role (str): camera role, e.g. 'top'.
    Returns: JPEG Response, or HTTP 503 if not available.
    """
    feed = hub.feeds.get(role)
    if feed is None or feed.jpeg is None or feed.error:
        return Response("Camera unavailable", status_code=503)
    return Response(feed.jpeg[2], media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.websocket("/ws/camera/{role}")
async def camera_stream(websocket: WebSocket, role: str):
    """
    Command. Send one JPEG at a time; client acknowledges after draw to bound backlog.

    Args: websocket: connection; role (str): camera role.
    Returns: None after disconnect. Packet is uint64 sequence + float64 read time + JPEG.
    """
    if (websocket.url.hostname != "127.0.0.1"
            or websocket.headers.get("origin") != f"http://127.0.0.1:{websocket.url.port}"):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    if role not in hub.feeds:
        await websocket.close(code=1008)
        return
    feed = hub.feeds[role]
    previous = 0
    try:
        while not hub.stop.is_set():
            if feed.error:
                await websocket.send_json({"error": feed.error})
                await websocket.close(code=1011)
                return
            frame = feed.jpeg
            if frame is None or frame[0] == previous:
                await asyncio.sleep(0.002)
                continue
            sequence, captured, jpeg = frame
            await websocket.send_bytes(struct.pack("!Qd", sequence, captured) + jpeg)
            ack = await asyncio.wait_for(websocket.receive_text(), ACK_TIMEOUT_SECONDS)
            if ack != str(sequence):
                raise ValueError("Invalid frame acknowledgement")
            feed.ack_age_ms = (time.monotonic()-captured)*1000
            previous = sequence
    except WebSocketDisconnect:
        return  # Expected browser close.
    except TimeoutError:
        LOGGER.warning("Slow viewer disconnected for %s", role)
        await websocket.close(code=1008)


class PuppetRequest(BaseModel):
    """Validated intent; never contains arbitrary joint targets or controller addresses."""
    side: Literal["left", "right"] = "left"
    action: Literal["arm", "hold", "stop", "disarm", "unlimited"]
    client: str = Field(min_length=8, max_length=80)
    sequence: int = Field(ge=1)


@app.post("/api/puppet")
async def puppet_control(body: PuppetRequest, request: Request):
    """
    Command. Accept same-origin loopback operator intent for the sole paired owner.

    Args: body: action/client token; request: HTTP context.
    Returns: Current pair state, e.g. mode='ready', enabled=True after arming.
    """
    if (request.client.host not in ("127.0.0.1", "::1") or request.url.hostname != "127.0.0.1"
            or request.headers.get("origin") != f"http://127.0.0.1:{request.url.port}"):
        raise HTTPException(403, "Controls require this local dashboard origin")
    try:
        pair = hub.pair if body.side == "left" else hub.right_pair
        pair.request(body.action, body.client, body.sequence)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return pair.snapshot()


class PresetRequest(BaseModel):
    """Named presets only; arbitrary joint targets and controller addresses are rejected."""
    model_config = {"extra": "forbid"}
    action: Literal["start", "hold", "stop"]
    role: Literal["follower_left", "follower_right", "leader_left", "leader_right"] | None = None
    client: str = Field(min_length=8, max_length=80)
    sequence: int = Field(ge=1)


@app.post("/api/presets")
async def preset_control(body: PresetRequest, request: Request):
    """Command. Queue same-origin preset intent. Args: body, request: HTTP input. Returns: Preset state."""
    if (request.client.host not in ("127.0.0.1", "::1") or request.url.hostname != "127.0.0.1"
            or request.headers.get("origin") != f"http://127.0.0.1:{request.url.port}"):
        raise HTTPException(403, "Controls require this local dashboard origin")
    try:
        hub.presets.request(body.action, body.client, body.sequence, body.role)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return hub.presets.snapshot()


app.mount("/", StaticFiles(directory=Path(__file__).parents[1] / "frontend/dist", html=True), name="frontend")
