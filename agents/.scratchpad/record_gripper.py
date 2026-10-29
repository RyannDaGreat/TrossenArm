"""Record-only check by default; TROSSEN_GRIPPER_LIVE=1 records the live gripper test."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import subprocess
from pathlib import Path
from threading import Event
import time

import robot_camera

READY_TIMEOUT_SECONDS = 15
BASELINE_SECONDS = 2  # Show the gripper at rest before and after commands.
CAMERA_TEST_SECONDS = 3  # Short encode/decode check without robot access.


def sing_after_motion():
    """
    Command. Send the requested public-domain verse after verified movement.

    Returns:
        None; posts a spoken message to the user's audio topic, not a completion notification.
    Example:
        sing_after_motion()  # Sends Yankee Doodle once; returns None.
    """
    message = ("The right gripper is opening and closing fully for about one minute. "
               "Yankee Doodle went to town, riding on a pony; stuck a feather in his cap, "
               "and called it macaroni. Yankee Doodle, keep it up; Yankee Doodle dandy; "
               "mind the music and the step, and with the girls be handy.")
    subprocess.run(["curl", "--show-error", "--fail", "--max-time", "15",
                    "--data-binary", message, "https://ntfy.sh/stark_comma"], check=True)


def main(live=False):
    """
    Command. Record the camera, optionally run the gripper test, then join capture.

    Args:
        live (bool): False records only; True sends the guarded gripper commands.
    Returns:
        Path: Saved MP4, e.g. agents/.scratchpad/camera-check-20261028-204500.mp4.
    """
    stop, ready = Event(), Event()
    full_stroke = os.environ.get("TROSSEN_GRIPPER_FULL_STROKE") == "1"
    serial = os.environ.get("TROSSEN_CAMERA_SERIAL")
    name = ("gripper-full-stroke" if full_stroke else "gripper-motion") if live else "camera-check"
    output = Path(__file__).with_name(f"{name}-{datetime.now():%Y%m%d-%H%M%S}.mp4")
    with ThreadPoolExecutor(max_workers=1) as pool:
        recording = pool.submit(robot_camera.record_video, output, stop, ready, serial=serial)

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
                full_cycles = 4  # Four 16-second cycles meet the requested minute.
                completed = exercise(trossen_arm.TrossenArmDriver(), report,
                                     clear_known_fault=recover,
                                     cycles=full_cycles if full_stroke else (1 if recover else CYCLES),
                                     full_stroke=full_stroke,
                                     on_motion=sing_after_motion if full_stroke else None)
                print(f"Motion result: {completed} {'full' if full_stroke else 'small'} open-close cycles", flush=True)
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
