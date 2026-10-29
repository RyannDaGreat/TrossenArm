"""Inspect native UVC discovery and capture formats; no robot connection."""

import cv2
from cv2_enumerate_cameras import enumerate_cameras
from PIL import Image

cameras = list(enumerate_cameras())
for camera in cameras:
    print(camera, "index=", camera.index, "backend=", camera.backend,
          "name=", camera.name, "path=", camera.path, flush=True)
matches = [camera for camera in cameras if "405" in camera.name]
if len(matches) != 1:
    raise RuntimeError(f"Expected one D405, got {matches}")
camera = matches[0]
capture = cv2.VideoCapture(camera.index, camera.backend)
try:
    if not capture.isOpened():
        raise RuntimeError("Cannot open D405 through native UVC")
    for width, height in ((640, 480), (1280, 720)):
        print("Request", width, height,
              capture.set(cv2.CAP_PROP_FRAME_WIDTH, width),
              capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height), flush=True)
        print("Reported", capture.get(cv2.CAP_PROP_FRAME_WIDTH),
              capture.get(cv2.CAP_PROP_FRAME_HEIGHT), flush=True)
        for _ in range(30):
            success, bgr = capture.read()
            if not success:
                raise RuntimeError("D405 read failed")
        print("Actual BGR shape", bgr.shape, flush=True)
        Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).save(
            f"agents/.scratchpad/uvc-{width}.png")
finally:
    capture.release()
