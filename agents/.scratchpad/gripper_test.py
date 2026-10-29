"""Gripper-only experiment. Default: offline tests. Set TROSSEN_GRIPPER_LIVE=1 for hardware."""

import doctest
import math
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import trossen_arm as arm

TARGET_IP = "192.168.1.4"
CYCLES = 12
TRAVEL_M = 0.002  # Two millimeters, not a full closure.
MOVE_SECONDS = 3.0  # Slow motion relative to the small travel.
EFFORT_CAP_N = 20.0  # Lowest vendor-demo value; supervised retry after 10 N produced no travel.
VELOCITY_CAP_M_S = 0.25  # Original manufacturer bound; trajectory speed is set by MOVE_SECONDS.
POSITION_TOLERANCE_M = 0.001  # Allow sub-mm closed offset; below factory 4 mm tolerance.
MIN_MEASURED_TRAVEL_M = TRAVEL_M / 2  # Require real motion, not just loose endpoint agreement.
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
    print(f"FEEDBACK gripper={actual}, modes={modes}, effort={driver.get_gripper_effort()}, "
          f"compensation={driver.get_gripper_compensation_effort()}", flush=True)
    error = driver.get_error_information()
    if error != "No error":
        raise RuntimeError(f"Controller reports an error: {error}")
    if (len(positions) != len(baseline)
            or modes != [arm.Mode.idle] * 6 + [arm.Mode.position]):
        raise RuntimeError("Unexpected arm state; stopping")
    if any(not math.isfinite(x) or abs(x - b) > ARM_DRIFT_LIMIT_RAD
           for x, b in zip(positions, baseline)):
        raise RuntimeError(f"Arm joint drift: baseline={baseline}, actual={positions}")
    if not math.isfinite(actual) or abs(actual - target) > POSITION_TOLERANCE_M:
        raise RuntimeError(f"Gripper failed target: target={target}, actual={actual}")
    return actual


def exercise(driver, report=announce, clear_known_fault=False, cycles=CYCLES):
    """
    Command. Configure only the labeled follower, run small cycles, then clean up.

    Args:
        driver: Trossen driver, or the offline test double.
        report: Console action logger. No audio is sent during operation.
        clear_known_fault (bool): One-time recovery only for our recorded velocity-limit fault.
        cycles (int): Requested cycles; use one for recovery validation.
    Returns:
        int: Completed open-close cycles; 12 by default. Errors propagate.
    """
    if not isinstance(cycles, int) or not 1 <= cycles <= CYCLES:
        raise ValueError(f"cycles must be between 1 and {CYCLES}")
    configured = False
    enabled = False
    try:
        driver.configure(arm.Model.wxai_v0, arm.StandardEndEffector.wxai_v0_follower,
                         TARGET_IP, clear_known_fault, CONNECT_TIMEOUT_SECONDS)
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
        limit_fields = ("position_min", "position_max", "position_tolerance",
                        "velocity_max", "velocity_tolerance", "effort_max", "effort_tolerance")
        original_limits = [tuple(getattr(limit, field) for field in limit_fields) for limit in limits]
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
        gripper_limit.effort_max = EFFORT_CAP_N
        gripper_limit.velocity_max = VELOCITY_CAP_M_S
        driver.set_joint_limits(limits)
        readback = driver.get_joint_limits()
        applied = readback[-1]
        if len(readback) != 7 or [tuple(getattr(limit, field) for field in limit_fields)
                                  for limit in readback[:-1]] != original_limits[:-1]:
            raise RuntimeError("Arm joint limits changed unexpectedly")
        for index, field in enumerate(limit_fields):
            if field not in ("velocity_max", "effort_max") and getattr(applied, field) != original_limits[-1][index]:
                raise RuntimeError(f"Unexpected gripper limit change: {field}")
        if not (0 < applied.effort_max <= EFFORT_CAP_N
                and 0 < applied.velocity_max <= VELOCITY_CAP_M_S * 1.00001):
            raise RuntimeError("Controller did not accept reduced gripper limits")
        report("Enabling the right gripper now. It may move slightly to its starting position.")
        enabled = True
        driver.set_gripper_mode(arm.Mode.position)
        if list(driver.get_modes()) != [arm.Mode.idle] * 6 + [arm.Mode.position]:
            raise RuntimeError("Position mode was not enabled; refusing the first target")
        driver.set_gripper_position(initial_target, MOVE_SECONDS, True)
        previous = check_feedback(driver, baseline, initial_target)
        if abs(initial_target - lower) > POSITION_TOLERANCE_M:
            report("Closing the right gripper by at most two millimeters to start the test.")
            driver.set_gripper_position(lower, MOVE_SECONDS, True)
            previous = check_feedback(driver, baseline, lower)
        for cycle in range(1, cycles + 1):
            for word, target in (("Opening", upper), ("Closing", lower)):
                report(f"{word} the right gripper two millimeters. Cycle {cycle} of {cycles}.")
                driver.set_gripper_position(target, MOVE_SECONDS, True)
                actual = check_feedback(driver, baseline, target)
                direction = 1 if word == "Opening" else -1
                if direction * (actual - previous) < MIN_MEASURED_TRAVEL_M:
                    raise RuntimeError(f"Insufficient measured {word}: {previous} -> {actual}")
                previous = actual
                print(f"VERIFIED cycle={cycle} action={word} target={target:.6f} "
                      f"actual={actual:.6f}", flush=True)
        return cycles
    finally:
        primary_error = sys.exception()
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
                    try:
                        driver.cleanup()
                    except RuntimeError as cleanup_error:
                        if primary_error is not None:
                            raise BaseExceptionGroup("Motion and cleanup both failed",
                                                     [primary_error, cleanup_error])
                        raise
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

    def set_fake_mode(mode):
        """
        Command. Update the mock gripper state, not real hardware.

        Args:
            mode: Simulated gripper mode.
        Returns:
            None; set_fake_mode(arm.Mode.position) updates the mock's final mode.
        """
        driver.get_modes.return_value[-1] = mode

    driver.set_gripper_mode.side_effect = set_fake_mode
    driver.get_arm_positions.return_value = [0.0] * 6
    driver.get_joint_limits.return_value = [SimpleNamespace(
        position_min=0.0, position_max=0.04, position_tolerance=0.004,
        effort_max=100.0, effort_tolerance=300.0, velocity_max=0.005, velocity_tolerance=0.0,
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
    assert driver.get_joint_limits.return_value[-1].velocity_max == VELOCITY_CAP_M_S
    assert driver.get_joint_limits.return_value[0].velocity_max == 0.005
    driver.get_gripper_position.side_effect = None
    driver.get_gripper_position.return_value = 0.01
    driver.set_gripper_mode.side_effect = None
    driver.set_gripper_position.reset_mock()
    try:
        exercise(driver, Mock())
    except RuntimeError as error:
        assert "Position mode was not enabled" in str(error)
    else:
        raise AssertionError("Idle gripper incorrectly accepted as position-controlled")
    driver.set_gripper_position.assert_not_called()
    driver.set_gripper_mode.side_effect = set_fake_mode
    driver.cleanup.side_effect = RuntimeError("mock cleanup failed")
    try:
        exercise(driver, Mock())
    except ExceptionGroup as errors:
        assert "Gripper failed target" in str(errors.exceptions[0])
        assert "mock cleanup failed" in str(errors.exceptions[1])
    else:
        raise AssertionError("Primary failure was not preserved alongside cleanup failure")
    print("PASS: planner, cycles, offsets, mode guard, gripper-only limit restoration, abort, and combined cleanup failures. No hardware used.")


if __name__ == "__main__":
    if os.environ.get("TROSSEN_GRIPPER_LIVE") == "1":
        completed = exercise(arm.TrossenArmDriver())
        print(f"SUCCESS: {completed} small open-close cycles verified.", flush=True)
    else:
        self_check()
