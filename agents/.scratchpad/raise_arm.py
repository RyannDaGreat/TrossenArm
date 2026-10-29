"""Staged upright experiment: one driver owner, visual approval between quarter-waypoints."""
import json
import os
from pathlib import Path
import sys
import time

from PIL import Image
import trossen_arm as arm

import robot_camera
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "web/source/backend"))
from geometry import forward

ROLE = os.environ.get("TROSSEN_MOTION_ROLE")
if ROLE is not None and ROLE not in {"leader_left", "leader_right", "follower_right"}:
    raise ValueError(f"Unsupported motion role: {ROLE}")
SCRATCH = Path("agents/.scratchpad") / (f"{ROLE}-motion" if ROLE else "")
APPROVAL = SCRATCH / "upright-approval.txt"
STAGE_SECONDS = 8.0
CHECK_SECONDS = 0.05  # 20 Hz controller-error and stop checks.
APPROVAL_TIMEOUT_SECONDS = 300.0  # Never leave an unattended position hold indefinitely.
JOINT_ERROR_RAD = 0.03  # About 1.7 degrees of final joint agreement.


def snapshots(stage):
    """
    Command. Save top and bottom camera images for stage review.

    Args:
        stage (int): Completed stage number.
    Returns:
        None; snapshots(1) writes upright-stage-1-top.png and -bottom.png.
    """
    devices = robot_camera.discover()
    bottom = robot_camera.select_camera([device for device in devices if device.get("serial") is None])
    for role, serial, uid in (("top", "418643070452", None), ("bottom", None, bottom["uid"])):
        with robot_camera.open_camera(serial, uid) as camera:
            path = SCRATCH / f"upright-stage-{stage}-{role}.png"
            Image.fromarray(robot_camera.read_rgb(camera)).save(path)
            print(f"Review image: {path}", flush=True)


def run():
    """
    Command. Execute approved stages, preserve gripper idle, and brake on exit.

    Returns:
        None; a successful run writes upright-status.json with stage 4 and skyward direction.
    """
    plan = json.loads((SCRATCH / "upright-plan.json").read_text())
    driver = arm.TrossenArmDriver()
    configured = False
    try:
        driver.configure(arm.Model.wxai_v0,
                         getattr(arm.StandardEndEffector, plan.get("preset", "wxai_v0_follower")),
                         plan["ip"], False, 5.0)
        configured = True
        current = list(driver.get_arm_positions())
        assert list(driver.get_modes()) == [arm.Mode.idle] * 7
        assert driver.get_error_information() == "No error"
        for index, (value, limit) in enumerate(zip(current, driver.get_joint_limits()[:6])):
            if not limit.position_min-limit.position_tolerance <= value <= limit.position_max+limit.position_tolerance:
                raise RuntimeError(f"Joint {index} starts outside factory bounds: {value}")
        assert max(abs(a-b) for a, b in zip(current, plan["start"])) < JOINT_ERROR_RAD
        snapshots(0)
        # Activate once; never re-enable with a potentially stale target between stages.
        driver.set_arm_modes(arm.Mode.position)
        driver.set_arm_positions(current, 2.0, True)
        for stage, fraction in enumerate(plan["fractions"], 1):
            deadline = time.monotonic() + APPROVAL_TIMEOUT_SECONDS
            print(f"Waiting for approval {stage}; all arm joints held, gripper idle.", flush=True)
            while APPROVAL.read_text().strip() != str(stage):
                if APPROVAL.read_text().strip() == "stop":
                    raise KeyboardInterrupt("Operator requested stop")
                if driver.get_error_information() != "No error":
                    raise RuntimeError(driver.get_error_information())
                if list(driver.get_modes()) != [arm.Mode.position] * 6 + [arm.Mode.idle]:
                    raise RuntimeError("Unexpected modes during visual review")
                if time.monotonic() > deadline:
                    raise TimeoutError("Visual review timeout")
                time.sleep(CHECK_SECONDS)
            target = [a + fraction*(b-a) for a, b in zip(plan["start"], plan["target"])]
            for q, (lo, hi) in zip(target, plan["limits"]):
                assert lo <= q <= hi
            print(f"MOVING stage={stage} duration={STAGE_SECONDS} target={target}", flush=True)
            driver.set_arm_positions(target, STAGE_SECONDS, False)
            until = time.monotonic() + STAGE_SECONDS
            while time.monotonic() < until:
                if APPROVAL.read_text().strip() == "stop":
                    raise KeyboardInterrupt("Operator requested stop")
                if driver.get_error_information() != "No error":
                    raise RuntimeError(driver.get_error_information())
                if list(driver.get_modes()) != [arm.Mode.position] * 6 + [arm.Mode.idle]:
                    raise RuntimeError("Unexpected control modes")
                time.sleep(CHECK_SECONDS)
            actual = list(driver.get_arm_positions())
            if max(abs(a-b) for a, b in zip(actual, target)) > JOINT_ERROR_RAD:
                raise RuntimeError(f"Joint target mismatch: {target} vs {actual}")
            _, transform = forward(actual)
            status = {"stage": stage, "joints": actual,
                      "tool_xyz": transform[:3, 3].tolist(), "tool_forward": transform[:3, 0].tolist()}
            (SCRATCH / "upright-status.json").write_text(json.dumps(status, indent=2) + "\n")
            print("VERIFIED", status, flush=True)
            snapshots(stage)
        print(f"POSE COMPLETE: {plan.get('role', 'follower_right')}", flush=True)
    finally:
        if configured:
            try:
                driver.set_arm_modes(arm.Mode.idle)
                print("FINAL", driver.get_modes(), driver.get_error_information(), flush=True)
            finally:
                driver.cleanup()


if __name__ == "__main__":
    assert os.environ.get("TROSSEN_ARM_UPRIGHT_LIVE") == "1", "Explicit live authorization required"
    run()
