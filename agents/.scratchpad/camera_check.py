"""Check stable camera selection, then capture one real RGB preview without robot commands."""

import doctest
from pathlib import Path

from PIL import Image

import robot_camera

assert doctest.testmod(robot_camera).failed == 0
for devices in ([], [{"name": "D405", "serial": "1"}, {"name": "D405", "serial": "2"}]):
    try:
        robot_camera.select_camera(devices)
    except RuntimeError as error:
        print(f"Expected selection rejection: {error}")
    else:
        raise AssertionError("Ambiguous/missing cameras must not be selected")
print(robot_camera.discover(), flush=True)
with robot_camera.open_camera() as camera:
    image = robot_camera.read_rgb(camera)
    output = Path(__file__).with_name("realsense-rgb.png")
    Image.fromarray(image).save(output)
    print(f"Saved {output.name}: {image.shape} RGB", flush=True)
