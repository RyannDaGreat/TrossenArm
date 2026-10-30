"""Record two small right-follower gripper cycles at the verified camera profile."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Event
import time
import os

import cv2
import imageio_ffmpeg
import trossen_arm
import robot_camera
from gripper_test import exercise

WIDTH, HEIGHT, FPS = 640, 480, 30
READY_TIMEOUT_SECONDS = 15
BASELINE_SECONDS = 2
CYCLES = 2
STAMP = datetime.now().strftime('%Y%m%d-%H%M%S')


def record(serial, role, stop, ready):
    """
    Command. Encode live (480,640,3) uint8 RGB frames and save review stills.

    Args:
        serial (str): Stable camera serial.
        role (str): Output label.
        stop, ready (Event): Capture lifecycle signals.
    Returns:
        str: MP4 path, such as agents/.scratchpad/gripper-right-20261029.mp4.
    """
    path = Path('agents/.scratchpad') / f'gripper-{role}-{STAMP}.mp4'
    writer = imageio_ffmpeg.write_frames(str(path), (WIDTH, HEIGHT), fps=FPS,
        codec='libx264', pix_fmt_in='rgb24', pix_fmt_out='yuv420p', ffmpeg_log_level='info')
    writer.send(None)
    count = 0
    try:
        with robot_camera.open_camera(serial, width=WIDTH, height=HEIGHT) as camera:
            while not stop.is_set():
                frame = robot_camera.read_bgr(camera, WIDTH, HEIGHT)
                writer.send(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                count += 1
                ready.set()
                if count % FPS == 0:
                    still = path.with_name(f'{path.stem}-{count // FPS:02d}.jpg')
                    if not cv2.imwrite(str(still), frame):
                        raise RuntimeError(f'Cannot save {still}')
                if count % (FPS * 5) == 0:
                    print(f'{role}: recorded {count} frames', flush=True)
    finally:
        writer.close()
    print(f'SAVED {path}: {count} frames', flush=True)
    return str(path)


stop = Event()
with ThreadPoolExecutor(max_workers=2) as pool:
    readiness = [Event(), Event()]
    recordings = [pool.submit(record, serial, role, stop, ready)
                  for (serial, role), ready in zip(
                      [('418643070460', 'right'), ('418643070452', 'top')], readiness)]

    def report(message):
        """
        Command. Print a motion label and propagate any recorder failure.

        Args: message (str): Label from the guarded motion routine.
        Returns: None; report('Opening') prints Opening if recording is healthy.
        """
        for future in recordings:
            if future.done():
                future.result()
                raise RuntimeError('Recorder stopped during motion')
        print(message, flush=True)

    try:
        for ready in readiness:
            if not ready.wait(READY_TIMEOUT_SECONDS):
                report('Checking camera readiness')
                raise TimeoutError('Camera was not ready; no motion sent')
        time.sleep(BASELINE_SECONDS)
        report('Both recordings are ready')
        if os.environ.get('TROSSEN_GRIPPER_LIVE') == '1':
            print('COMPLETED CYCLES:', exercise(trossen_arm.TrossenArmDriver(), report, cycles=CYCLES), flush=True)
        time.sleep(BASELINE_SECONDS)
    finally:
        stop.set()
        for future in recordings:
            future.result()
