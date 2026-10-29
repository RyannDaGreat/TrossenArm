"""Save one fresh frame per discovered hardware serial; no robot commands."""
from PIL import Image
import robot_camera

cameras = robot_camera.discover()
print(cameras, flush=True)
assert len({camera["serial"] for camera in cameras}) == len(cameras)
for camera in cameras:
    serial = camera["serial"]
    with robot_camera.open_camera(serial, uid=camera["uid"] if serial is None else None) as capture:
        path = f"agents/.scratchpad/camera-{serial or 'unidentified'}.png"
        Image.fromarray(robot_camera.read_rgb(capture)).save(path)
        print(f"Saved {path}", flush=True)
