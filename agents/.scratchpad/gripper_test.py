"""Gripper-only experiment. Default: offline tests. Set TROSSEN_GRIPPER_LIVE=1 for hardware."""

import doctest
import math
import os
from types import SimpleNamespace
from unittest.mock import Mock

import trossen_arm as arm

TARGET_IP = "192.168.1.4"
CYCLES = 12
TRAVEL_M = 0.002  # Two millimeters, not a full closure.
MOVE_SECONDS = 3.0  # Slow motion relative to the small travel.
EFFORT_CAP_N = 10.0  # Above the vendor's 7 N friction example; below its 20 N demo.
VELOCITY_CAP_M_S = 0.005  # Five millimeters per second.
POSITION_TOLERANCE_M = 0.0005  # Feedback must resolve the two-millimeter motion.
ARM_DRIFT_LIMIT_RAD = 0.005  # Stop if a braked joint changes by about 0.29 degrees.
CONNECT_TIMEOUT_SECONDS = 5.0


def motion_interval(position, minimum, maximum, tolerance=0.0):
    """
    Pure function. Choose a two-millimeter interval inside the gripper bounds.

    Args:
        position, minimum, maximum (float): Current position and bounds, in meters.
        tolerance (float): Reported factory feedback tolerance; acceptance is capped at 1 mm.
    Returns:
        tuple[float, float]: Lower and upper targets in meters.
    Examples:
        >>> motion_interval(0.01, 0.0, 0.04)
        (0.01, 0.012)
        >>> motion_interval(0.04, 0.0, 0.04)
        (0.038, 0.04)
        >>> motion_interval(-0.000736, 0.0, 0.04, 0.004)
        (0.0, 0.002)
    """
    if not all(math.isfinite(x) for x in (position, minimum, maximum, tolerance)):
        raise ValueError("Nonfinite gripper position or bounds")
    accepted_offset = min(tolerance, TRAVEL_M / 2)
    if (tolerance < 0 or not minimum - accepted_offset <= position <= maximum + accepted_offset
            or maximum - minimum < TRAVEL_M):
        raise ValueError("Gripper position/bounds do not allow the planned travel")
    lower = max(minimum, min(position, maximum - TRAVEL_M))
    return lower, lower + TRAVEL_M


def announce(message):
    """
    Command. Print an action label; do not send audio or notifications.

    Args:
        message (str): Brief action label.
    Returns:
        None.
    Example:
        announce("Opening the right gripper.")  # Prints the label; returns None.
    """
    print(message, flush=True)


def check_feedback(driver, baseline, target):
    """
    Query. Check gripper feedback and confirm arm joints remain braked and still.

    Args:
        driver: Connected driver with fresh controller feedback.
        baseline (list[float]): Six arm joint positions in radians.
        target (float): Gripper position in meters.
    Returns:
        float: Measured gripper position, e.g. 0.012 for a 12 mm target.
    """
    positions = list(driver.get_arm_positions())
    modes = list(driver.get_modes())
    actual = driver.get_gripper_position()
    error = driver.get_error_information()
    if error != "No error":
        raise RuntimeError(f"Controller reports an error: {error}")
    if len(positions) != len(baseline) or modes[:-1] != [arm.Mode.idle] * 6:
        raise RuntimeError("Unexpected arm state; stopping")
    if any(not math.isfinite(x) or abs(x - b) > ARM_DRIFT_LIMIT_RAD
           for x, b in zip(positions, baseline)):
        raise RuntimeError(f"Arm joint drift: baseline={baseline}, actual={positions}")
    if not math.isfinite(actual) or abs(actual - target) > POSITION_TOLERANCE_M:
        raise RuntimeError(f"Gripper failed target: target={target}, actual={actual}")
    return actual


def exercise(driver, report=announce):
    """
    Command. Configure only the labeled follower, run small cycles, then clean up.

    Args:
        driver: Trossen driver, or the offline test double.
        report: Console action logger. No audio is sent during operation.
    Returns:
        int: Completed open-close cycles; 12 on success. Errors propagate.
    """
    configured = False
    enabled = False
    try:
        driver.configure(arm.Model.wxai_v0, arm.StandardEndEffector.wxai_v0_follower,
                         TARGET_IP, False, CONNECT_TIMEOUT_SECONDS)
        configured = True
        modes = list(driver.get_modes())
        baseline = list(driver.get_arm_positions())
        limits = driver.get_joint_limits()
        initial = driver.get_gripper_position()
        print(f"INITIAL modes={modes}, arm={baseline}, gripper={initial}, "
              f"errors={driver.get_error_information()}", flush=True)
        if driver.get_error_information() != "No error":
            raise RuntimeError("Controller reports an error; refusing activation")
        if modes != [arm.Mode.idle] * 7 or len(baseline) != 6 or len(limits) != 7:
            raise RuntimeError("Expected seven idle joints; refusing to override existing control")
        if not all(math.isfinite(x) for x in baseline):
            raise RuntimeError("Nonfinite arm feedback")
        gripper_limit = limits[-1]
        lower, upper = motion_interval(initial, gripper_limit.position_min,
                                       gripper_limit.position_max, gripper_limit.position_tolerance)
        initial_target = max(lower, min(initial, upper))
        print(f"PLAN initial={initial}, initial_target={initial_target}, lower={lower}, "
              f"upper={upper}, factory_tolerance={gripper_limit.position_tolerance}", flush=True)
        print(f"ORIGINAL gripper effort_max={gripper_limit.effort_max}, "
              f"velocity_max={gripper_limit.velocity_max}", flush=True)
        if not (math.isfinite(gripper_limit.effort_max) and gripper_limit.effort_max > 0
                and math.isfinite(gripper_limit.velocity_max) and gripper_limit.velocity_max > 0):
            raise RuntimeError("Invalid controller limits")
        gripper_limit.effort_max = min(gripper_limit.effort_max, EFFORT_CAP_N)
        gripper_limit.velocity_max = min(gripper_limit.velocity_max, VELOCITY_CAP_M_S)
        driver.set_joint_limits(limits)
        applied = driver.get_joint_limits()[-1]
        if not (0 < applied.effort_max <= EFFORT_CAP_N
                and 0 < applied.velocity_max <= VELOCITY_CAP_M_S * 1.00001):
            raise RuntimeError("Controller did not accept reduced gripper limits")
        report("Enabling the right gripper now. It may move slightly to its starting position.")
        enabled = True
        driver.set_gripper_mode(arm.Mode.position)
        driver.set_gripper_position(initial_target, MOVE_SECONDS, True)
        check_feedback(driver, baseline, initial_target)
        if abs(initial_target - lower) > POSITION_TOLERANCE_M:
            report("Closing the right gripper by at most two millimeters to start the test.")
            driver.set_gripper_position(lower, MOVE_SECONDS, True)
            check_feedback(driver, baseline, lower)
        for cycle in range(1, CYCLES + 1):
            for word, target in (("Opening", upper), ("Closing", lower)):
                report(f"{word} the right gripper two millimeters. Cycle {cycle} of {CYCLES}.")
                driver.set_gripper_position(target, MOVE_SECONDS, True)
                actual = check_feedback(driver, baseline, target)
                print(f"VERIFIED cycle={cycle} action={word} target={target:.6f} "
                      f"actual={actual:.6f}", flush=True)
        return CYCLES
    finally:
        if configured:
            try:
                if enabled:
                    report("Returning the right gripper to idle now.")
            finally:
                try:
                    driver.set_gripper_mode(arm.Mode.idle)
                    print(f"FINAL modes={driver.get_modes()}, "
                          f"gripper={driver.get_gripper_position()}, "
                          f"errors={driver.get_error_information()}", flush=True)
                finally:
                    driver.cleanup()
                    print("Driver cleanup complete; electrical power is not switched off.", flush=True)


def self_check():
    """
    Command. Run offline planner and mocked driver tests; never contact hardware.

    Returns:
        None. Raises on a failed check; prints PASS on success.
    Example:
        self_check()  # Tests 12 cycles and cleanup, then returns None.
    """
    announce("OFFLINE TEST: all hardware calls below are mocked.")
    assert doctest.testmod().failed == 0
    for invalid in ((float("nan"), 0, 0.04), (0.05, 0, 0.04), (0, 0, 0.001),
                    (-0.0011, 0, 0.04, 0.004), (-0.0007, 0, 0.04, 0.0001)):
        try:
            motion_interval(*invalid)
        except ValueError:
            pass  # Expected rejection is the behavior under test.
        else:
            raise AssertionError(f"Invalid interval accepted: {invalid}")
    driver = Mock()
    driver.get_modes.return_value = [arm.Mode.idle] * 7
    driver.get_arm_positions.return_value = [0.0] * 6
    driver.get_joint_limits.return_value = [SimpleNamespace(
        position_min=0.0, position_max=0.04, position_tolerance=0.004,
        effort_max=100.0, velocity_max=0.25,
    ) for _ in range(7)]
    driver.get_gripper_position.side_effect = [0.01, 0.01] + [0.012, 0.01] * CYCLES + [0.01]
    driver.get_error_information.return_value = "No error"
    assert exercise(driver, Mock()) == CYCLES
    assert driver.set_gripper_position.call_count == 1 + CYCLES * 2
    driver.set_arm_modes.assert_not_called()
    driver.set_all_modes.assert_not_called()
    driver.cleanup.assert_called_once()
    driver.get_gripper_position.side_effect = None
    driver.get_gripper_position.return_value = 0.03
    driver.cleanup.reset_mock()
    try:
        exercise(driver, Mock())
    except RuntimeError as error:
        assert "Gripper failed target" in str(error)
    else:
        raise AssertionError("Missing feedback did not stop the test")
    driver.cleanup.assert_called_once()
    driver.get_gripper_position.side_effect = [-0.000736, 0.0] + [0.002, 0.0] * CYCLES + [0.0]
    assert exercise(driver, Mock()) == CYCLES
    print("PASS: offline planner, 12-cycle flow, bounded offset, failed-motion abort, and cleanup. No hardware used.")


if __name__ == "__main__":
    if os.environ.get("TROSSEN_GRIPPER_LIVE") == "1":
        completed = exercise(arm.TrossenArmDriver())
        print(f"SUCCESS: {completed} small open-close cycles verified.", flush=True)
    else:
        self_check()
