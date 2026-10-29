"""Run the staged controller entirely with mocks, including mode ownership and cleanup."""
import itertools
import json
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace

import raise_arm
import trossen_arm as arm

folder = Path("agents/.scratchpad/upright-test")
folder.mkdir(exist_ok=True)
plan = json.loads(Path("agents/.scratchpad/upright-plan.json").read_text())
(folder / "upright-plan.json").write_text(json.dumps(plan))
robot = Mock()
state = {"q": plan["start"], "mode": arm.Mode.idle}


def set_positions(q, duration, blocking):
    """
    Command. Update mock feedback immediately.

    Args: q: six mock angles; duration and blocking: ignored mock timing.
    Returns: None, e.g. set_positions([0]*6, 8, False) stores six zeros.
    """
    state["q"] = q


def set_mode(mode):
    """
    Command. Update mock arm modes without changing the gripper.

    Args: mode: simulated Mode.
    Returns: None; set_mode(Mode.position) stores that mode.
    """
    state["mode"] = mode


def positions():
    """Query. Return current mock joint angles, for example six zeros."""
    return state["q"]


def modes():
    """Query. Return six current mock arm modes plus idle gripper, for example seven idle modes."""
    return [state["mode"]] * 6 + [arm.Mode.idle]


def approval():
    """Query. Approve the next simulated stage, e.g. '1' after the initial hold."""
    return str(robot.set_arm_positions.call_count)


robot.get_joint_limits.return_value = [SimpleNamespace(position_min=lo, position_max=hi,
                                                     position_tolerance=0.02) for lo, hi in plan["limits"]]
robot.get_arm_positions.side_effect = positions
robot.get_modes.side_effect = modes
robot.set_arm_positions.side_effect = set_positions
robot.set_arm_modes.side_effect = set_mode
robot.get_error_information.return_value = "No error"
file = Mock()
file.read_text.side_effect = approval
with patch.object(raise_arm, "SCRATCH", folder), patch.object(raise_arm, "APPROVAL", file), \
     patch.object(raise_arm.arm, "TrossenArmDriver", return_value=robot), \
     patch.object(raise_arm, "snapshots") as images, \
     patch.object(raise_arm.time, "monotonic", side_effect=itertools.count(0, 10)):
    raise_arm.run()
assert robot.set_arm_positions.call_count == 5
assert state["mode"] == arm.Mode.idle
robot.set_gripper_mode.assert_not_called()
robot.cleanup.assert_called_once()
assert images.call_count == 5
assert json.loads((folder / "upright-status.json").read_text())["stage"] == 4
print("PASS: all four mocked stages, continuous owner, gripper unchanged, final idle/cleanup.")
