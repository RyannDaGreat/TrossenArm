"""Single-owner, operator-held left-arm following; absolute seven-joint mapping, upright engagement, no automatic homing."""
import logging
import math
from functools import partial
import threading
import time

import trossen_arm as arm
from presets import tall_target

LOG = logging.getLogger("puppet")
LOOP_HZ = 50
HEARTBEAT_SECONDS = 0.5
SESSION_SECONDS = 60
MAX_STEP_TIME = 0.1  # Reject five missed periods; never turn a stall into a large catch-up step.
SPEED_RAD_S = 0.5
GRIPPER_SPEED_M_S = 0.02
TARGET_HORIZON_SECONDS = 3 / LOOP_HZ
INITIAL_BOUND_OFFSET_RAD = 0.002
UPRIGHT_TOLERANCE_RAD = 0.06
ALIGNMENT_TOLERANCE_RAD = 0.06
STOP_ORDER = ("follower_left", "leader_left")


def limited_target(current, leader, bounds, speeds, dt):
    """Pure query. Step toward absolute encoder targets with per-joint speed/bound caps.

    Args: current, leader: radians plus gripper meters; bounds, speeds: matching limits;
        dt: positive interval up to MAX_STEP_TIME.
    Returns: next target and controller-bound diagnostics. No engagement-relative offset.
    """
    if not 0 < dt <= MAX_STEP_TIME:
        raise ValueError("Missed control deadline")
    if not len(current) == len(leader) == len(bounds) == len(speeds):
        raise ValueError("Joint-vector length mismatch")
    if not all(math.isfinite(x) for values in (current, leader, speeds) for x in values):
        raise ValueError("Nonfinite joint data")
    result, limited = [], []
    for joint, (previous, desired, (lo, hi), speed) in enumerate(zip(current, leader, bounds, speeds)):
        if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi or speed <= 0:
            raise ValueError("Invalid motion limits")
        bounded = max(lo, min(desired, hi))
        if bounded != desired:
            limited.append(dict(joint=joint, requested=desired, bounded=bounded, kind="controller bound"))
        step = speed*dt
        result.append(max(lo, min(hi, previous+max(-step, min(bounded-previous, step)))))
    return result, limited


class StartNotReady(Exception):
    """Recoverable upright/alignment precondition; no activation writes occurred."""


class IntentStopped(Exception):
    """Expected operator cancellation or heartbeat/session expiry, not an SDK fault."""


class LeftPair:
    """One thread owns both SDK instances; HTTP threads only update ordered intent."""

    def __init__(self, stop, publish, presets=None, side="left"):
        """
        Command. Create disarmed state without hardware access.

        Args: stop (Event): server shutdown; publish: callback(role, driver).
        Returns: None; snapshot() initially reports connecting/disarmed.
        """
        if side not in ("left", "right"):
            raise ValueError("Unknown pair side")
        self.side = side
        self.leader, self.follower = f"leader_{side}", f"follower_{side}"
        self.stop_order = (self.follower, self.leader)
        self.stop, self.publish = stop, publish
        self.presets = presets
        self.lock = presets.lock if presets else threading.RLock()
        self.enabled = False
        self.unlimited = False
        self.deadline = 0.0
        self.client = None
        self.sequences = {}
        self.generation = 0
        self.stop_pending = False
        self.drivers = {}
        self.dead = set()
        self.fault = None
        self.state = {"mode": "connecting", "enabled": False, "active": False, "error": None,
                      "stop_confirmed": False, "grippers": "absolute opening", "mapping": "absolute joint positions"}

    def request(self, action, client, sequence):
        """
        Command. Queue monotonic browser intent; never call hardware here.

        Args: action: arm/hold/stop/disarm; client: owner token; sequence: increasing integer.
        Returns: None; request('stop', token, 4) latches a stop until the owner confirms idle.
        """
        with self.lock:
            if action == "arm" and self.presets and self.presets.busy(self.side):
                raise ValueError(f"Wait for {self.side} Up movements to finish before starting puppet mode")
            if self.state["mode"] in ("connecting", "fault", "stop_unconfirmed", "stopped"):
                raise ValueError(self.state["error"] or "Pair not ready")
            if self.stop_pending:
                raise ValueError("Stop pending; wait for confirmed idle")
            if self.client not in (None, client):
                raise ValueError("Another browser owns puppet mode")
            if self.client is None and action != "arm":
                raise ValueError("Puppet mode is not armed")
            if sequence <= self.sequences.get(client, -1):
                raise ValueError("Stale control request rejected")
            if action == "arm":
                if self.state["mode"] != "ready" or self.enabled:
                    raise ValueError("Cannot rearm until the previous engagement stops")
                self.client, self.enabled = client, True
                self.unlimited = False
                self.generation += 1
            elif action == "unlimited":
                if not self.enabled:
                    raise ValueError("Enable puppet mode first")
                self.unlimited = True
                self.deadline = time.monotonic()+HEARTBEAT_SECONDS
            elif action == "hold":
                if not self.enabled:
                    raise ValueError("Enable puppet mode first")
                self.deadline = time.monotonic()+HEARTBEAT_SECONDS
            elif action in ("stop", "disarm"):
                self.enabled, self.deadline, self.stop_pending = False, 0.0, True
                self.generation += 1
            else:
                raise ValueError("Unknown puppet action")
            self.sequences[client] = sequence

    def snapshot(self):
        """Query. Return a state copy; active=None explicitly means stop is unconfirmed."""
        with self.lock:
            return {**self.state, "enabled": self.enabled, "stop_pending": self.stop_pending, "unlimited": self.unlimited}

    def set_state(self, **values):
        """
        Command. Publish owner state under the shared lock.

        Args: values: state fields, e.g. mode='ready'.
        Returns: None.
        """
        with self.lock:
            self.state.update(values)

    def sdk(self, role, method, *args):
        """
        Command. Call an owned SDK method and permanently retire a driver that raises.

        Args: role: arm role; method: SDK method name; args: method arguments.
        Returns: SDK result, e.g. sdk(role, 'get_arm_positions') returns six angles.
        """
        if role in self.dead:
            raise RuntimeError(f"Driver {role} already failed; restart required")
        try:
            return getattr(self.drivers[role], method)(*args)
        except Exception:
            self.dead.add(role)
            raise

    def require_intent(self, generation, tick_started, engaged=None):
        """
        Query. Recheck cancellation and timing immediately before each motor write.

        Args: generation: engagement token; tick_started: monotonic tick start; engaged: session start.
        Returns: None or raises IntentStopped / RuntimeError. Cannot interrupt an already blocked SDK call.
        """
        now = time.monotonic()
        with self.lock:
            if (self.stop.is_set() or self.stop_pending or not self.enabled
                    or generation != self.generation or now >= self.deadline
                    or (engaged is not None and not self.unlimited and now-engaged >= SESSION_SECONDS)):
                raise IntentStopped("Operator released, heartbeat expired, or session ended")
        if now-tick_started > MAX_STEP_TIME:
            raise RuntimeError("Current SDK reads exceeded the control deadline")

    def halt(self):
        """
        Command. Stop healthy follower first, then leader; never reuse a failed SDK instance.

        Returns: bool: True only after both arm mode readbacks confirm idle; failures stay visible.
        """
        with self.lock:
            self.enabled, self.deadline, self.stop_pending = False, 0.0, True
            self.generation += 1
        self.set_state(mode="stopping", active=None, stop_confirmed=False)
        failures = []
        for role in self.stop_order:
            if role not in self.drivers or role in self.dead:
                failures.append(f"{role}: stop cannot be confirmed on failed/unavailable driver")
                continue
            try:
                self.sdk(role, "set_all_modes", arm.Mode.idle)
                if list(self.sdk(role, "get_modes")) != [arm.Mode.idle]*7:
                    raise RuntimeError("Idle readback not confirmed")
                self.publish(role, self.drivers[role])
            except Exception as error:
                self.dead.add(role)
                failures.append(f"{role}: {error}")
                LOG.exception("Stop failed for %s", role)
        confirmed = not failures
        with self.lock:
            self.stop_pending = not confirmed
            if confirmed:
                self.client = None
        detail = "; ".join(filter(None, [self.fault, *failures])) or None
        self.set_state(mode=("fault" if self.fault else "ready") if confirmed else "stop_unconfirmed",
                       active=False if confirmed else None, stop_confirmed=confirmed, error=detail, remaining_s=0)
        return confirmed

    def activate(self, generation, tick_started):
        """
        Command. Validate stationary references, hold follower, then enable leader gravity compensation.

        Args: generation: engagement token; tick_started: current monotonic control start.
        Returns: (leader_reference, follower_reference, bounds); no automatic alignment sweep.
        """
        for role in self.stop_order:
            if list(self.sdk(role, "get_modes")) != [arm.Mode.idle]*7:
                raise RuntimeError("Expected seven idle modes before engagement")
            speeds = list(self.sdk(role, "get_all_velocities"))
            if len(speeds) != 7 or any(not math.isfinite(v) or abs(v) > 0.05 for v in speeds):
                raise StartNotReady("Puppet start cancelled because an arm was moving. Up is available; try puppet mode once both arms have stopped.")
        leader_ref = list(self.sdk(self.leader, "get_all_positions"))
        raw = list(self.sdk(self.follower, "get_all_positions"))
        if len(leader_ref) != 7 or len(raw) != 7 or not all(math.isfinite(q) for q in leader_ref+raw):
            raise RuntimeError("Invalid initial feedback")
        limits = self.sdk(self.follower, "get_joint_limits")
        bounds = [(limit.position_min, limit.position_max) for limit in limits]
        if len(bounds) != 7 or not all(math.isfinite(lo) and math.isfinite(hi) and lo < hi for lo, hi in bounds):
            raise RuntimeError("Invalid follower limits")
        reference = [max(lo, min(q, hi)) for q, (lo, hi) in zip(raw, bounds)]
        if max(abs(a-b) for a, b in zip(raw, reference)) > INITIAL_BOUND_OFFSET_RAD:
            raise RuntimeError("Follower outside bounds; supervised alignment required")
        for q, limit in zip(leader_ref, self.sdk(self.leader, "get_joint_limits")):
            if not limit.position_min-limit.position_tolerance <= q <= limit.position_max+limit.position_tolerance:
                raise RuntimeError("Leader outside factory tolerance")
        for role, values in ((self.leader, leader_ref), (self.follower, raw)):
            own_limits = self.sdk(role, "get_joint_limits")
            own_bounds = [(v.position_min, v.position_max) for v in own_limits]
            upright = tall_target(values[:6], own_bounds[:6])
            if any(abs(a-b) > UPRIGHT_TOLERANCE_RAD for a,b in zip(values[1:6], upright[1:6])) or abs(values[6]-own_bounds[6][1]) > 0.002:
                raise StartNotReady(f"Use Up on both {self.side} arms first: upright, wrists reset, grippers open")
        if any(abs(a-b) > ALIGNMENT_TOLERANCE_RAD for a,b in zip(leader_ref[:6], raw[:6])):
            raise StartNotReady(f"Align the {self.side} base headings before enabling puppet mode")
        self.speeds = [min(SPEED_RAD_S if i < 6 else GRIPPER_SPEED_M_S, limit.velocity_max) for i,limit in enumerate(limits)]
        self.feedback_bounds = [(v.position_min-v.position_tolerance, v.position_max+v.position_tolerance) for v in limits]
        self.velocity_bounds = [v.velocity_max+v.velocity_tolerance for v in limits]
        if any(not math.isfinite(v) or v <= 0 for v in self.speeds+self.velocity_bounds):
            raise RuntimeError("Invalid follower velocity limits")
        self.set_state(mode="arming", active=None, stop_confirmed=False)
        for role, method, args in (
            (self.follower, "set_all_modes", (arm.Mode.position,)),
            (self.follower, "set_all_positions", (reference, 0.0, False)),
            (self.leader, "set_all_modes", (arm.Mode.external_effort,)),
            (self.leader, "set_all_external_efforts", ([0.0]*7, 0.0, False)),
        ):
            self.require_intent(generation, tick_started)
            self.sdk(role, method, *args)
        return leader_ref, reference, bounds

    def run(self):
        """
        Command. Own the left pair until shutdown/fault; powered following requires held intent.

        Returns: None after follower-first stop/cleanup. Faults never auto-resume.
        """
        active = False
        try:
            for role, ip, preset in ((self.leader, "192.168.1.3" if self.side == "left" else "192.168.1.2", arm.StandardEndEffector.wxai_v0_leader),
                                     (self.follower, "192.168.1.5" if self.side == "left" else "192.168.1.4", arm.StandardEndEffector.wxai_v0_follower)):
                self.drivers[role] = arm.TrossenArmDriver()
                self.sdk(role, "configure", arm.Model.wxai_v0, preset, ip, False, 5.0)
            self.set_state(mode="ready")
            if self.presets:
                for role in self.stop_order:
                    self.presets.connected(role)
            last_tick, last_publish = time.monotonic(), 0.0
            while not self.stop.is_set():
                if self.presets:
                    for role in self.stop_order:
                        self.presets.tick(role, partial(self.sdk, role))
                now = time.monotonic()
                dt, last_tick = now-last_tick, now
                with self.lock:
                    held = self.enabled and now < self.deadline
                    pending, generation = self.stop_pending, self.generation
                try:
                    if pending or (active and (not held or (not self.unlimited and now-engaged >= SESSION_SECONDS))):
                        if not self.halt():
                            raise RuntimeError("Stopping failed; use the physical stop")
                        active = False
                    for role in self.stop_order:
                        error = self.sdk(role, "get_error_information")
                        if error != "No error":
                            self.dead.add(role)
                            raise RuntimeError(f"{role}: {error}")
                    if held and not active and not pending:
                        leader_ref, command, bounds = self.activate(generation, now)
                        self.require_intent(generation, now)
                        self.set_state(error=None)
                        engaged, active = time.monotonic(), True
                        last_tick = engaged
                        self.set_state(mode="active", active=True, remaining_s=SESSION_SECONDS, limited=[])
                        LOG.warning("%s puppet active: absolute seven-joint copying engaged from upright", self.side)
                    elif active:
                        if not 0 < dt <= MAX_STEP_TIME:
                            raise RuntimeError(f"Missed control interval: {dt:.3f}s")
                        expected = {self.leader: arm.Mode.external_effort, self.follower: arm.Mode.position}
                        for role, mode in expected.items():
                            if list(self.sdk(role, "get_modes")) != [mode]*7:
                                raise RuntimeError(f"Unexpected {role} modes")
                        feedback = list(self.sdk(self.follower, "get_all_positions"))
                        velocity = list(self.sdk(self.follower, "get_all_velocities"))
                        if len(feedback) != 7 or len(velocity) != 7 or not all(math.isfinite(q) for q in feedback+velocity):
                            raise RuntimeError("Invalid follower feedback")
                        if not all(lo <= q <= hi for q,(lo,hi) in zip(feedback,self.feedback_bounds)):
                            raise RuntimeError("Follower exceeded factory position tolerance")
                        if any(abs(v) > bound for v,bound in zip(velocity,self.velocity_bounds)):
                            raise RuntimeError("Follower exceeded factory velocity tolerance")
                        # Anchor each command to feedback so lag cannot accumulate a large queued move.
                        target, limited = limited_target(feedback, list(self.sdk(self.leader, "get_all_positions")),
                                                         bounds, self.speeds, dt)
                        self.set_state(limited=limited)
                        self.require_intent(generation, now, engaged)
                        self.sdk(self.follower, "set_all_positions", target, TARGET_HORIZON_SECONDS, False)
                        command = target
                        self.set_state(remaining_s=None if self.unlimited else max(0, SESSION_SECONDS-(time.monotonic()-engaged)))
                    if now-last_publish >= 1/20:
                        for role in self.stop_order:
                            try:
                                self.publish(role, self.drivers[role])
                            except Exception:
                                self.dead.add(role)
                                raise
                        last_publish = now
                except StartNotReady as reason:
                    self.halt()
                    active = False
                    self.set_state(error=str(reason))
                except IntentStopped as reason:
                    LOG.info("Operator stop: %s", reason)
                    if not self.halt():
                        raise RuntimeError("Stopping failed; use the physical stop")
                    active = False
                self.stop.wait(1/LOOP_HZ)
        except Exception as error:
            self.fault = str(error)
            self.set_state(mode="stopping", active=None, error=self.fault, stop_confirmed=False)
            LOG.exception("Left pair fault; stopping healthy peer first, no automatic resume")
        finally:
            if self.presets:
                for role in self.stop_order:
                    self.presets.unavailable(role, self.fault or "Owner shutting down")
            confirmed = self.halt()
            if self.presets and confirmed:
                # halt() already verified both idle; release a queued preset only now.
                for role in self.stop_order:
                    self.presets.confirm_halted(role, self.fault or "Server stopped")
            for role in self.stop_order:
                if role not in self.drivers:
                    continue
                try:
                    self.drivers[role].cleanup()
                except Exception as error:
                    prior = self.snapshot().get("error")
                    self.set_state(mode="stop_unconfirmed", active=None, stop_confirmed=False,
                                   error=f"{prior or 'Shutdown'}; {role} cleanup: {error}")
                    LOG.exception("Failed cleanup for %s", role)
