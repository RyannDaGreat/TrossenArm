"""Single-owner, operator-held left-arm following; no gripper copying or automatic homing."""
import logging
import math
import threading
import time

import trossen_arm as arm

LOG = logging.getLogger("puppet")
LOOP_HZ = 50
HEARTBEAT_SECONDS = 0.5
SESSION_SECONDS = 60
MAX_STEP_TIME = 0.1  # Reject five missed periods; never turn a stall into a large catch-up step.
SPEED_RAD_S = 0.25
TARGET_HORIZON_SECONDS = 3 / LOOP_HZ  # Interpolate each small update over three ticks, rather than step instantly.
EXCURSION_RAD = 0.25
TRACKING_RAD = 0.08
MEASURED_SPEED_RAD_S = 0.75
INITIAL_BOUND_OFFSET_RAD = 0.002
STOP_ORDER = ("follower_left", "leader_left")


def limited_target(current, leader, leader_ref, follower_ref, bounds, dt):
    """
    Pure function. Relative joint mapping with range, excursion and command-rate caps.

    Args:
        current, leader, leader_ref, follower_ref: Equal-length finite radian lists.
        bounds: Per-joint (minimum, maximum) radian pairs.
        dt (float): Positive validated interval, at most 0.1 seconds.
    Returns:
        tuple[list, list]: Next command and explicit per-joint saturation details.
    Examples:
        >>> limited_target([0], [0.1], [0], [0], [(-1, 1)], 0.02)
        ([0.005], [])
        >>> limited_target([0], [1], [0], [0], [(-1, 1)], 0.02)[1][0]['kind']
        'trial excursion'
    """
    if not 0 < dt <= MAX_STEP_TIME:
        raise ValueError("Missed control deadline")
    if not len(current) == len(leader) == len(leader_ref) == len(follower_ref) == len(bounds):
        raise ValueError("Joint-vector length mismatch")
    if not all(math.isfinite(x) for values in (current, leader, leader_ref, follower_ref) for x in values):
        raise ValueError("Nonfinite joint data")
    result, limited = [], []
    for joint, (previous, value, origin, reference, (minimum, maximum)) in enumerate(zip(current, leader, leader_ref, follower_ref, bounds)):
        desired = reference+value-origin
        lower, upper = max(minimum, reference-EXCURSION_RAD), min(maximum, reference+EXCURSION_RAD)
        bounded = max(lower, min(desired, upper))
        if bounded != desired:
            limited.append({"joint": joint, "requested": desired, "bounded": bounded,
                            "kind": "controller bound" if bounded in (minimum, maximum) else "trial excursion"})
        step = SPEED_RAD_S*dt
        result.append(previous+max(-step, min(bounded-previous, step)))
    return result, limited


class IntentStopped(Exception):
    """Expected operator cancellation or heartbeat/session expiry, not an SDK fault."""


class LeftPair:
    """One thread owns both SDK instances; HTTP threads only update ordered intent."""

    def __init__(self, stop, publish):
        """
        Command. Create disarmed state without hardware access.

        Args: stop (Event): server shutdown; publish: callback(role, driver).
        Returns: None; snapshot() initially reports connecting/disarmed.
        """
        self.stop, self.publish = stop, publish
        self.lock = threading.Lock()
        self.enabled = False
        self.deadline = 0.0
        self.client = None
        self.sequences = {}
        self.generation = 0
        self.stop_pending = False
        self.drivers = {}
        self.dead = set()
        self.fault = None
        self.state = {"mode": "connecting", "enabled": False, "active": False, "error": None,
                      "stop_confirmed": False, "grippers": "idle / not linked", "mapping": "relative joint offsets"}

    def request(self, action, client, sequence):
        """
        Command. Queue monotonic browser intent; never call hardware here.

        Args: action: arm/hold/stop/disarm; client: owner token; sequence: increasing integer.
        Returns: None; request('stop', token, 4) latches a stop until the owner confirms idle.
        """
        with self.lock:
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
                self.generation += 1
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
            return {**self.state, "enabled": self.enabled, "stop_pending": self.stop_pending}

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
                    or (engaged is not None and now-engaged >= SESSION_SECONDS)):
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
        for role in STOP_ORDER:
            if role not in self.drivers or role in self.dead:
                failures.append(f"{role}: stop cannot be confirmed on failed/unavailable driver")
                continue
            try:
                self.sdk(role, "set_arm_modes", arm.Mode.idle)
                if list(self.sdk(role, "get_modes"))[:6] != [arm.Mode.idle]*6:
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
        for role in STOP_ORDER:
            if list(self.sdk(role, "get_modes")) != [arm.Mode.idle]*7:
                raise RuntimeError("Expected seven idle modes before engagement")
            speeds = list(self.sdk(role, "get_arm_velocities"))
            if len(speeds) != 6 or any(not math.isfinite(v) or abs(v) > 0.05 for v in speeds):
                raise RuntimeError("Hold the leader still before engagement")
        leader_ref = list(self.sdk("leader_left", "get_arm_positions"))
        raw = list(self.sdk("follower_left", "get_arm_positions"))
        if len(leader_ref) != 6 or len(raw) != 6 or not all(math.isfinite(q) for q in leader_ref+raw):
            raise RuntimeError("Invalid initial feedback")
        limits = self.sdk("follower_left", "get_joint_limits")[:6]
        bounds = [(limit.position_min, limit.position_max) for limit in limits]
        if len(bounds) != 6 or not all(math.isfinite(lo) and math.isfinite(hi) and lo < hi for lo, hi in bounds):
            raise RuntimeError("Invalid follower limits")
        reference = [max(lo, min(q, hi)) for q, (lo, hi) in zip(raw, bounds)]
        if max(abs(a-b) for a, b in zip(raw, reference)) > INITIAL_BOUND_OFFSET_RAD:
            raise RuntimeError("Follower outside bounds; supervised alignment required")
        for q, limit in zip(leader_ref, self.sdk("leader_left", "get_joint_limits")[:6]):
            if not limit.position_min-limit.position_tolerance <= q <= limit.position_max+limit.position_tolerance:
                raise RuntimeError("Leader outside factory tolerance")
        self.set_state(mode="arming", active=None, stop_confirmed=False)
        for role, method, args in (
            ("follower_left", "set_arm_modes", (arm.Mode.position,)),
            ("follower_left", "set_arm_positions", (reference, 0.0, False)),
            ("leader_left", "set_arm_modes", (arm.Mode.external_effort,)),
            ("leader_left", "set_arm_external_efforts", ([0.0]*6, 0.0, False)),
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
            for role, ip, preset in (("leader_left", "192.168.1.3", arm.StandardEndEffector.wxai_v0_leader),
                                     ("follower_left", "192.168.1.5", arm.StandardEndEffector.wxai_v0_follower)):
                self.drivers[role] = arm.TrossenArmDriver()
                self.sdk(role, "configure", arm.Model.wxai_v0, preset, ip, False, 5.0)
            self.set_state(mode="ready")
            last_tick, last_publish = time.monotonic(), 0.0
            while not self.stop.is_set():
                now = time.monotonic()
                dt, last_tick = now-last_tick, now
                with self.lock:
                    held = self.enabled and now < self.deadline
                    pending, generation = self.stop_pending, self.generation
                try:
                    if pending or (active and (not held or now-engaged >= SESSION_SECONDS)):
                        if not self.halt():
                            raise RuntimeError("Stopping failed; use the physical stop")
                        active = False
                    for role in STOP_ORDER:
                        error = self.sdk(role, "get_error_information")
                        if error != "No error":
                            self.dead.add(role)
                            raise RuntimeError(f"{role}: {error}")
                    if held and not active and not pending:
                        leader_ref, command, bounds = self.activate(generation, now)
                        self.require_intent(generation, now)
                        follower_ref = list(command)
                        engaged, active = time.monotonic(), True
                        last_tick = engaged
                        self.set_state(mode="active", active=True, remaining_s=SESSION_SECONDS, limited=[])
                        LOG.warning("Left puppet active: relative references latched; grippers idle")
                    elif active:
                        if not 0 < dt <= MAX_STEP_TIME:
                            raise RuntimeError(f"Missed control interval: {dt:.3f}s")
                        expected = {"leader_left": arm.Mode.external_effort, "follower_left": arm.Mode.position}
                        for role, mode in expected.items():
                            if list(self.sdk(role, "get_modes")) != [mode]*6+[arm.Mode.idle]:
                                raise RuntimeError(f"Unexpected {role} modes")
                        feedback = list(self.sdk("follower_left", "get_arm_positions"))
                        velocity = list(self.sdk("follower_left", "get_arm_velocities"))
                        if len(feedback) != 6 or len(velocity) != 6 or not all(math.isfinite(q) for q in feedback+velocity):
                            raise RuntimeError("Invalid follower feedback")
                        if max(abs(a-b) for a, b in zip(feedback, command)) > TRACKING_RAD:
                            raise RuntimeError("Follower tracking error exceeded trial bound")
                        fastest = max(range(6), key=lambda index: abs(velocity[index]))
                        if abs(velocity[fastest]) > MEASURED_SPEED_RAD_S:
                            raise RuntimeError(f"Follower joint {fastest} measured {velocity[fastest]:.3f} rad/s; "
                                               f"trial speed guard is ±{MEASURED_SPEED_RAD_S:.3f} rad/s. "
                                               "Both arms are being stopped; this is not an obstacle detector.")
                        target, limited = limited_target(command, list(self.sdk("leader_left", "get_arm_positions")),
                                                         leader_ref, follower_ref, bounds, dt)
                        self.set_state(limited=limited)
                        self.require_intent(generation, now, engaged)
                        self.sdk("follower_left", "set_arm_positions", target, TARGET_HORIZON_SECONDS, False)
                        command = target
                        self.set_state(remaining_s=max(0, SESSION_SECONDS-(time.monotonic()-engaged)))
                    if now-last_publish >= 1/20:
                        for role in STOP_ORDER:
                            try:
                                self.publish(role, self.drivers[role])
                            except Exception:
                                self.dead.add(role)
                                raise
                        last_publish = now
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
            self.halt()
            for role in STOP_ORDER:
                if role not in self.drivers:
                    continue
                try:
                    self.drivers[role].cleanup()
                except Exception as error:
                    prior = self.snapshot().get("error")
                    self.set_state(mode="stop_unconfirmed", active=None, stop_confirmed=False,
                                   error=f"{prior or 'Shutdown'}; {role} cleanup: {error}")
                    LOG.exception("Failed cleanup for %s", role)
