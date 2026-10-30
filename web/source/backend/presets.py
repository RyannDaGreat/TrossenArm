"""Arm presets driven only by existing SDK-owner threads."""
import math
import threading
import time

import trossen_arm as arm

DURATION_SECONDS = 8.0
HEARTBEAT_SECONDS = 0.5
READ_DEADLINE_SECONDS = 0.15
SETTLE_SECONDS = 1.0
POSITION_ERROR_RAD = 0.03
INITIAL_OFFSET_RAD = 0.002
SPEED_LIMIT_RAD_S = 1.0
STATIONARY_SPEED_RAD_S = 0.05
ROLES = ("follower_left", "follower_right", "leader_left", "leader_right")


def tall_target(current, bounds):
    """
    Pure function. Derive the tall WXAI pose, keeping base yaw and normalizing both wrist axes.

    Args: current: six radians; bounds: six (minimum, maximum) radian pairs.
    Returns: Six finite angles within unchanged nominal controller bounds.
    Examples:
        >>> q = tall_target([0.2, 0, 0, 0, 0, 0.3], [(-3.14, 3.14)]*2 + [(-2.35, 2.356194496)] + [(-3.14, 3.14)]*3)
        >>> [round(v, 3) for v in q]
        [0.2, 1.305, 2.356, 0.519, 0.0, 0.0]
    """
    if len(current) != 6 or len(bounds) != 6 or not all(math.isfinite(v) for v in current):
        raise ValueError("Expected six finite angles and six joint bounds")
    if not all(math.isfinite(lo) and math.isfinite(hi) and lo < hi for lo, hi in bounds):
        raise ValueError("Invalid joint bounds")
    elbow = bounds[2][1]
    upper, forearm = 0.264, math.hypot(0.245, 0.06)  # Official WXAI DH link lengths, meters.
    angle = elbow + math.atan2(0.06, 0.245)
    shoulder = math.atan2(upper - forearm*math.cos(angle), forearm*math.sin(angle))
    target = [current[0], shoulder, elbow, shoulder+math.pi/2-elbow, 0.0, 0.0]
    if not all(lo <= value <= hi for value, (lo, hi) in zip(target, bounds)):
        raise ValueError("Tall pose does not fit the current factory limits")
    return target


# Previously visually aligned follower headings; leaders share encoder angles for copying.
UP_BASE_RADIANS = {"left": math.radians(91.2), "right": math.radians(-87.6)}


def up_target(role, current, bounds):
    """
    Pure function. Prepare a tall pose with the matching pair's standard base angle.

    Args: role: known arm role; current: six radians; bounds: six factory intervals.
    Returns: Six angles, including a common base target for each leader/follower pair.
    Examples:
        >>> bounds = [(-math.pi, math.pi)]*2 + [(0, 2.356194496)] + [(-math.pi, math.pi)]*3
        >>> a = up_target("leader_right", [0]*6, bounds)
        >>> b = up_target("follower_right", [-2, 0, 0, 0, 0, 0], bounds)
        >>> a == b, round(math.degrees(a[0]), 1)
        (True, -87.6)
    """
    if role not in ROLES:
        raise ValueError("Unknown arm role")
    target = tall_target(current, bounds)
    target[0] = UP_BASE_RADIANS[role.rsplit("_", 1)[1]]
    if not bounds[0][0] <= target[0] <= bounds[0][1]:
        raise ValueError("Up base heading does not fit the current factory limits")
    return target


class Released(Exception):
    """Expected stop or loss of live browser intent."""


class Presets:
    """One shared intent lock; motor calls remain on each arm's existing owner."""

    def __init__(self, stop):
        """Command. Create disarmed intent and an exclusive lock without hardware access."""
        self.stop = stop
        self.lock = threading.RLock()
        self.pair = None
        self.pairs = {}
        self.available = set()
        self.client = None
        self.sequences = {}
        self.generation = 0
        self.deadline = 0.0
        self.started = None
        self.target = None
        self.state = dict(mode="ready", role=None, active=False, stop_confirmed=True,
                          error=None, remaining_s=0, heading="Align pair base angles; reset wrists and open gripper")

    def snapshot(self):
        """Query. Return visible state and connected arm roles."""
        with self.lock:
            return {**self.state, "available": sorted(self.available)}

    def busy(self, side=None):
        """Query. Report ownership, including an unresolved stop."""
        with self.lock:
            return self.state["role"] is not None and (side is None or self.state["role"].endswith("_"+side))

    def request(self, action, client, sequence, role=None):
        """
        Command. Queue exclusive browser intent, never hardware calls.

        Args: action: start/hold/stop; client: browser token; sequence: increasing number; role: arm.
        Returns: None; start reserves motion until confirmed idle, including during cancellation.
        """
        with self.lock:
            if sequence <= self.sequences.get(client, -1):
                raise ValueError("Stale control request rejected")
            if self.client not in (None, client):
                raise ValueError("Another browser owns the preset")
            if action == "start":
                if role not in ROLES:
                    raise ValueError("Unknown arm role")
                pair = self.pairs.get(role.rsplit("_", 1)[-1], self.pair).snapshot()
                if self.busy() or pair["enabled"] or pair["stop_pending"] or pair["active"] is not False:
                    raise ValueError("Stop the current control mode before starting a preset")
                if role not in self.available or (pair["mode"] != "ready"):
                    raise ValueError("Arm is not ready")
                self.client = client
                self.generation += 1
                self.started = None
                self.state.update(mode="queued", role=role, active=False, stop_confirmed=False,
                                  error=None, remaining_s=DURATION_SECONDS)
                self.deadline = time.monotonic()+HEARTBEAT_SECONDS
            elif action == "hold":
                if not self.busy() or self.state["mode"] not in ("queued", "moving"):
                    raise ValueError("No running preset")
                self.deadline = time.monotonic()+HEARTBEAT_SECONDS
            elif action == "stop":
                if self.busy():
                    self.deadline = 0
                    self.generation += 1
                    if self.state["mode"] != "stop_unconfirmed":
                        self.state.update(mode="stopping", active=None)
            else:
                raise ValueError("Unknown preset action")
            self.sequences[client] = sequence

    def connected(self, role):
        """Command. Mark a configured arm available. Args: role: owner role. Returns: None."""
        if role in ROLES:
            with self.lock:
                self.available.add(role)

    def unavailable(self, role, error):
        """Command. Retire a failed owner; never claim its stop succeeded. Args: role, error: failure. Returns: None."""
        with self.lock:
            self.available.discard(role)
            if self.state["role"] == role:
                detail = self.state["error"] if self.state["mode"] == "stop_unconfirmed" else None
                self.state.update(mode="stop_unconfirmed", active=None, stop_confirmed=False, error=detail or str(error))

    def require_intent(self, generation, tick_started):
        """Query. Reject cancellation or late reads before each write. Args: generation, tick_started: tokens. Returns: None or raises."""
        with self.lock:
            if self.stop.is_set() or generation != self.generation or time.monotonic() >= self.deadline:
                raise Released("Stopped or browser heartbeat expired")
        if time.monotonic()-tick_started > READ_DEADLINE_SECONDS:
            raise ValueError("Preset reads exceeded the control deadline")

    def halt(self, role, sdk, error=None):
        """Command. Stop through the owning thread and confirm idle. Args: role, sdk: owner; error: reason. Returns: None."""
        with self.lock:
            if self.state["role"] != role:
                return
            self.state.update(mode="stopping", active=None, stop_confirmed=False)
        sdk("set_all_modes", arm.Mode.idle)
        if list(sdk("get_modes")) != [arm.Mode.idle]*7:
            raise RuntimeError("Preset idle readback not confirmed")
        self.confirm_halted(role, error)

    def confirm_halted(self, role, error=None):
        """Command. Release ownership after the owner verified idle. Args: role, error: stop result. Returns: None."""
        with self.lock:
            if self.state["role"] != role:
                return
            self.state.update(mode="ready", role=None, active=False, stop_confirmed=True,
                              error=error, remaining_s=0)
            self.client, self.started = None, None

    def tick(self, role, sdk):
        """
        Command. Advance one preset using only its existing SDK owner; never create a driver.

        Args: role: owner role; sdk: callable(method, *args), which retires failed drivers.
        Returns: None; queues one eight-second interpolation and monitors its completion.
        """
        with self.lock:
            if self.state["role"] != role or self.state["mode"] == "stop_unconfirmed":
                return
            generation = self.generation
        now = time.monotonic()
        try:
            self.require_intent(generation, now)
            if sdk("get_error_information") != "No error":
                raise ValueError("Controller reports an error; no automatic reset")
            positions = list(sdk("get_all_positions"))
            velocity = list(sdk("get_all_velocities"))
            if len(positions) != 7 or len(velocity) != 7 or not all(math.isfinite(v) for v in positions+velocity):
                raise ValueError("Invalid preset feedback")
            modes = list(sdk("get_modes"))
            self.require_intent(generation, now)
            if self.started is None:
                if modes != [arm.Mode.idle]*7 or max(map(abs, velocity)) > STATIONARY_SPEED_RAD_S:
                    raise ValueError("Preset needs seven idle modes and a stationary arm")
                limits = sdk("get_joint_limits")
                bounds = [(limit.position_min, limit.position_max) for limit in limits]
                self.feedback_bounds = [(limit.position_min-limit.position_tolerance,
                                         limit.position_max+limit.position_tolerance) for limit in limits]
                reference = [max(lo, min(q, hi)) for q, (lo, hi) in zip(positions, bounds)]
                if len(reference) != 7 or max(abs(a-b) for a, b in zip(reference, positions)) > INITIAL_OFFSET_RAD:
                    raise ValueError("Arm outside nominal bounds; supervised alignment required")
                self.target = up_target(role, reference[:6], bounds[:6]) + [bounds[6][1]]
                self.velocity_bounds = [limit.velocity_max + limit.velocity_tolerance for limit in limits]
                self.require_intent(generation, now)
                sdk("set_all_modes", arm.Mode.position)
                self.require_intent(generation, now)
                sdk("set_all_positions", reference, 0.0, False)
                self.require_intent(generation, now)
                sdk("set_all_positions", self.target, DURATION_SECONDS, False)
                self.started = time.monotonic()
                with self.lock:
                    # A stop received during the SDK write remains latched by deadline/generation.
                    if self.generation == generation:
                        self.state.update(mode="moving", active=True)
            else:
                if modes != [arm.Mode.position]*7:
                    raise ValueError("Unexpected preset joint modes")
                if not all(lo <= q <= hi for q, (lo, hi) in zip(positions, self.feedback_bounds)):
                    raise ValueError("Preset feedback exceeded factory tolerance")
                if max(map(abs, velocity[:6])) > SPEED_LIMIT_RAD_S or abs(velocity[6]) > self.velocity_bounds[6]:
                    raise ValueError("Preset speed guard exceeded one radian per second")
                elapsed = time.monotonic()-self.started
                with self.lock:
                    self.state["remaining_s"] = max(0, DURATION_SECONDS-elapsed)
                if elapsed >= DURATION_SECONDS:
                    reached = all(abs(a-b) <= tolerance for a, b, tolerance in zip(positions, self.target, [POSITION_ERROR_RAD]*6+[0.002]))
                    if reached or elapsed >= DURATION_SECONDS+SETTLE_SECONDS:
                        self.halt(role, sdk, None if reached else "Preset did not reach its target")
        except Released as reason:
            self.halt(role, sdk, str(reason))
        except ValueError as error:
            self.halt(role, sdk, str(error))


class PresetGroup:
    """Four independent preset sessions sharing the pair reservation lock."""

    def __init__(self, stop):
        """Command. Allocate intent only; existing threads retain SDK ownership."""
        self.stop, self.lock = stop, threading.RLock()
        self.pair, self.pairs = None, {}
        self.sessions = {role: Presets(stop) for role in ROLES}
        for session in self.sessions.values():
            session.lock = self.lock

    def snapshot(self):
        """Query. Return per-arm progress, stop confirmation, and availability."""
        with self.lock:
            states = {role: session.snapshot() for role, session in self.sessions.items()}
            return {"arms": states, "available": [role for role, state in states.items() if role in state["available"]]}

    def busy(self, side=None):
        """Query. Reserve only the selected pair, or report any reservation."""
        with self.lock:
            return any(session.busy(side) for session in self.sessions.values())

    def request(self, action, client, sequence, role=None):
        """Command. Route ordered intent to an explicit arm; reject ambiguous old clients."""
        with self.lock:
            if role is None:
                owned = [name for name, session in self.sessions.items() if session.client == client and session.busy()]
                if len(owned) != 1:
                    raise ValueError("Choose which arm to control")
                role = owned[0]
            if role not in self.sessions:
                raise ValueError("Unknown arm role")
            session = self.sessions[role]
            session.pair, session.pairs = self.pair, self.pairs
            session.request(action, client, sequence, role)

    def connected(self, role):
        """Command. Mark one arm connected without changing its neighbors."""
        self.sessions[role].connected(role)

    def unavailable(self, role, error):
        """Command. Retain uncertainty for the failed arm only."""
        self.sessions[role].unavailable(role, error)

    def confirm_halted(self, role, error=None):
        """Command. Release an arm only after its owner verifies idle."""
        self.sessions[role].confirm_halted(role, error)

    def halt(self, role, sdk, error=None):
        """Command. Stop through the existing owner of this arm."""
        self.sessions[role].halt(role, sdk, error)

    def tick(self, role, sdk):
        """Command. Advance only this arm's independent eight-second move."""
        self.sessions[role].tick(role, sdk)
