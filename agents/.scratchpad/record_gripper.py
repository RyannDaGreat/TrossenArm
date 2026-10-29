"""Record-only check by default; TROSSEN_GRIPPER_LIVE=1 records the live gripper test."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
from pathlib import Path
from threading import Event
import time

import robot_camera

READY_TIMEOUT_SECONDS = 15
BASELINE_SECONDS = 2  # Show the gripper at rest before and after commands.
CAMERA_TEST_SECONDS = 3  # Short encode/decode check without robot access.


def main(live=False):
    """
    Command. Record the camera, optionally run the gripper test, then join capture.

    Args:
        live (bool): False records only; True sends the guarded gripper commands.
    Returns:
        Path: Saved MP4, e.g. agents/.scratchpad/camera-check-20261028-204500.mp4.
    """
    stop, ready = Event(), Event()
    name = "gripper-motion" if live else "camera-check"
    output = Path(__file__).with_name(f"{name}-{datetime.now():%Y%m%d-%H%M%S}.mp4")
    with ThreadPoolExecutor(max_workers=1) as pool:
        recording = pool.submit(robot_camera.record_video, output, stop, ready)

        def report(message):
            """
            Command. Check capture health and print a motion action without speech.

            Args:
                message (str): Current action, e.g. 'Opening the right gripper'.
            Returns:
                None; raises if recording has stopped or failed.
            """
            if recording.done():
                recording.result()
                raise RuntimeError("Recording ended before the robot test")
            print(message, flush=True)

        try:
            if not ready.wait(READY_TIMEOUT_SECONDS):
                if recording.done():
                    recording.result()
                raise TimeoutError("Camera did not produce a recorded frame; no robot commands sent")
            report("Camera recording is ready")
            if live:
                import trossen_arm
                from gripper_test import exercise
                time.sleep(BASELINE_SECONDS)
                recover = os.environ.get("TROSSEN_CLEAR_KNOWN_VELOCITY_FAULT") == "1"
                from gripper_test import CYCLES
                completed = exercise(trossen_arm.TrossenArmDriver(), report,
                                     clear_known_fault=recover, cycles=1 if recover else CYCLES)
                print(f"Motion result: {completed} small open-close cycles", flush=True)
                time.sleep(BASELINE_SECONDS)
            else:
                time.sleep(CAMERA_TEST_SECONDS)
        finally:
            stop.set()
            recording.result()
    print(f"SAVED {output}", flush=True)
    return output


if __name__ == "__main__":
    main(live=os.environ.get("TROSSEN_GRIPPER_LIVE") == "1")
