"""Staged upright experiment: one driver owner, visual approval between quarter-waypoints."""
import json
import math
import os
from pathlib import Path
import sys
import time

from PIL import Image
import cv2
import trossen_arm as arm

import robot_camera
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "web/source/backend"))
from geometry import forward

ROLE = os.environ.get("TROSSEN_MOTION_ROLE")
if ROLE is not None and ROLE not in {"leader_left", "leader_right", "follower_right", "follower_left"}:
    raise ValueError(f"Unsupported motion role: {ROLE}")
POSE = os.environ.get("TROSSEN_MOTION_POSE", "upright")
if POSE not in {"upright", "tall", "north"}:
    raise ValueError(f"Unknown pose: {POSE}")
SCRATCH = Path("agents/.scratchpad") / (f"{ROLE}-{POSE}-motion" if POSE != "upright" else f"{ROLE}-motion" if ROLE else "")
APPROVAL = SCRATCH / "upright-approval.txt"
STAGE_SECONDS = float(os.environ.get("TROSSEN_STAGE_SECONDS", "8"))
MIN_STAGE_SECONDS = 8 / 3  # User-authorized maximum speed increase over the verified 8-second stages.
if not math.isfinite(STAGE_SECONDS) or not MIN_STAGE_SECONDS <= STAGE_SECONDS <= 8:
    raise ValueError("Stage duration must be between 8/3 and 8 seconds")
CHECK_SECONDS = 0.05  # 20 Hz controller-error and stop checks.
APPROVAL_TIMEOUT_SECONDS = 300.0  # Never leave an unattended position hold indefinitely.
JOINT_ERROR_RAD = 0.03  # About 1.7 degrees of final joint agreement.
CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480  # Verified four-camera USB profile on both Macs.


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
    views = [("top", "418643070452", None), ("bottom", None, bottom["uid"])]
    if POSE == "north":
        views.append(("wrist", "418643070450" if ROLE == "follower_left" else "418643070460", None))
    for role, serial, uid in views:
        with robot_camera.open_camera(serial, uid, width=CAMERA_WIDTH, height=CAMERA_HEIGHT) as camera:
            path = SCRATCH / f"upright-stage-{stage}-{role}.png"
            bgr = robot_camera.read_bgr(camera, CAMERA_WIDTH, CAMERA_HEIGHT)
            Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).save(path)
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
        limits = driver.get_joint_limits()[:6]
        for index, (value, limit) in enumerate(zip(current, limits)):
            if not limit.position_min-limit.position_tolerance <= value <= limit.position_max+limit.position_tolerance:
                raise RuntimeError(f"Joint {index} starts outside factory bounds: {value}")
        assert max(abs(a-b) for a, b in zip(current, plan["start"])) < JOINT_ERROR_RAD
        snapshots(0)
        initial = [max(limit.position_min, min(value, limit.position_max))
                   for value, limit in zip(current, limits)]
        print("Initial in-bound target:", initial, "from measured:", current, flush=True)
        # Activate once; never re-enable with a potentially stale target between stages.
        driver.set_arm_modes(arm.Mode.position)
        driver.set_arm_positions(initial, 2.0, True)
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
