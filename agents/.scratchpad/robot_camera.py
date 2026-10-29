"""D405 RGB access without fixed USB ports or OS camera indices.

macOS uses native UVC because the SDK cannot set USB power state here.
Windows/Linux use the RealSense SDK. Those platforms need hardware validation.
Only one D405 is auto-selected; multiple matching cameras fail explicitly.
"""

from contextlib import contextmanager
import subprocess
import sys
import time

import imageio_ffmpeg

import cv2
import numpy as np

WIDTH, HEIGHT, FPS = 1280, 720, 30
FRAME_TIMEOUT_MS = 5000
WARMUP_FRAMES = FPS  # One second for automatic exposure to settle.
INTEL_USB_VID, D405_USB_PID = 0x8086, 0x0B5B


def discover():
    """
    Query. Discover D405 cameras using native device identity, not stored ports.

    Returns:
        list[dict]: Names plus current native index (Mac) or stable serial (SDK).
        Example: [{"name": "Intel RealSense D405", "serial": "123"}].
    """
    if sys.platform == "darwin":
        from cv2_enumerate_cameras import enumerate_cameras
        return [{"name": camera.name, "index": camera.index, "backend": camera.backend}
                for camera in enumerate_cameras()
                if camera.vid == INTEL_USB_VID and camera.pid == D405_USB_PID]
    import pyrealsense2 as rs
    context = rs.context()
    return [{"name": device.get_info(rs.camera_info.name),
             "serial": device.get_info(rs.camera_info.serial_number)}
            for device in context.query_devices()
            if "D405" in device.get_info(rs.camera_info.name)]


def select_camera(devices):
    """
    Pure function. Require a single discovered D405 rather than guessing a role.

    Args:
        devices (list[dict]): D405 records from discover().
    Returns:
        dict: The sole device, preserving its current capture identifier.
    Examples:
        >>> select_camera([{"name": "D405", "index": 1204}])
        {'name': 'D405', 'index': 1204}
        >>> select_camera([{"name": "D405", "serial": "123"}])
        {'name': 'D405', 'serial': '123'}
    """
    if len(devices) != 1:
        raise RuntimeError(f"Expected one D405, found {devices}; do not guess camera roles")
    return devices[0]


@contextmanager
def open_camera():
    """
    Command. Start the unique D405 and stop it when the context exits.

    Yields:
        Native capture object: 1280×720 RGB reads at requested 30 fps.
    Example:
        with open_camera() as camera: rgb = read_rgb(camera)  # (720, 1280, 3)

    Tested on macOS hardware. Windows/Linux hardware paths are untested.
    """
    selected = select_camera(discover())
    if sys.platform == "darwin":
        camera = cv2.VideoCapture(selected["index"], selected["backend"])
        stop = camera.release
    else:
        import pyrealsense2 as rs
        camera = rs.pipeline()
        config = rs.config()
        config.enable_device(selected["serial"])
        config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.rgb8, FPS)
        camera.start(config)
        stop = camera.stop
    try:
        if sys.platform == "darwin":
            if not camera.isOpened():
                raise RuntimeError(f"Cannot open {selected}")
            for key, value in ((cv2.CAP_PROP_FRAME_WIDTH, WIDTH),
                               (cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT),
                               (cv2.CAP_PROP_FPS, FPS)):
                if not camera.set(key, value):
                    raise RuntimeError(f"Camera rejected property {key}={value}")
        print(f"Camera selected: {selected}; requested {WIDTH}x{HEIGHT} at {FPS} fps", flush=True)
        for _ in range(WARMUP_FRAMES):
            read_rgb(camera)
        yield camera
    finally:
        stop()
        print("Camera stopped", flush=True)


def read_rgb(camera):
    """
    Command. Consume and copy the next RGB frame from the selected D405.

    Args:
        camera: Capture object yielded by open_camera().
    Returns:
        numpy.ndarray: (H, W, C) uint8 RGB, e.g. (720, 1280, 3), channels (R, G, B).
    Example:
        read_rgb(camera).shape  # (720, 1280, 3)

    Tested on macOS hardware. Windows/Linux hardware paths are untested.
    """
    if sys.platform == "darwin":
        success, bgr = camera.read()
        if not success:
            raise RuntimeError("D405 UVC frame read failed")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    else:
        color = camera.wait_for_frames(FRAME_TIMEOUT_MS).get_color_frame()
        if not color:
            raise RuntimeError("D405 returned no color frame")
        rgb = np.asanyarray(color.get_data()).copy()
    if rgb.shape != (HEIGHT, WIDTH, 3) or rgb.dtype != np.uint8:
        raise RuntimeError(f"Unexpected RGB frame: shape={rgb.shape}, dtype={rgb.dtype}")
    return rgb


def record_video(path, stop, ready, max_seconds=120):
    """
    Command. Record the selected D405 to H.264 MP4 until stop is signaled.

    Args:
        path (str): Output MP4 path; must not exist.
        stop, ready (threading.Event): Stop request and first-written-frame signal.
        max_seconds (float): Recording watchdog duration.
    Returns:
        int: Number of RGB frames encoded, e.g. 90 for about three seconds.
    Example:
        # Run in a thread, wait for ready, then set stop; result is the frame count.
        # Future.result() returns 90 for a three-second capture at 30 fps.
    """
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-n",
               "-f", "rawvideo", "-pixel_format", "rgb24",
               "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS),
               "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "fast",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)]
    with open_camera() as camera:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
        count = 0
        started = time.monotonic()
        try:
            while not stop.is_set():
                if time.monotonic() - started > max_seconds:
                    raise TimeoutError("Recording watchdog expired")
                encoder.stdin.write(read_rgb(camera).tobytes())
                encoder.stdin.flush()
                count += 1
                ready.set()
                if count % (FPS * 5) == 0:
                    print(f"Recording: {count} frames", flush=True)
        finally:
            encoder.stdin.close()
            try:
                exit_code = encoder.wait(timeout=10)
            except subprocess.TimeoutExpired:
                encoder.kill()
                encoder.wait()
                raise
            if exit_code != 0:
                raise RuntimeError(f"Video encoder failed with exit {exit_code}")
    if count == 0:
        raise RuntimeError("No camera frames were recorded")
    print(f"Video complete: {path}, {count} frames", flush=True)
    return count
