"""Offline camera selection and Windows/Linux SDK adapter tests. No real device access."""

import doctest
import sys
from unittest.mock import Mock, patch

import numpy as np

import robot_camera

assert doctest.testmod(robot_camera).failed == 0
cameras = [{"serial": "left", "index": 1201}, {"serial": "right", "index": 1200}]
assert robot_camera.select_camera(cameras, "right")["index"] == 1200
cameras.reverse()
assert robot_camera.select_camera(cameras, "right")["index"] == 1200
from record_gripper import sing_after_motion
with patch("record_gripper.subprocess.run") as post:
    sing_after_motion()
    post.assert_called_once()
    assert "Yankee Doodle" in post.call_args.args[0][-2]
print("PASS: explicit serial independent of enumeration order; speech request mocked.")
for platform in ("linux", "win32"):
    sdk = Mock()
    device = Mock()
    device.get_info.side_effect = ["Intel RealSense D405", "Intel RealSense D405", "stable-serial"]
    sdk.context.return_value.query_devices.return_value = [device]
    camera = sdk.pipeline.return_value
    frame = camera.wait_for_frames.return_value.get_color_frame.return_value
    frame.get_data.return_value = np.zeros((robot_camera.HEIGHT, robot_camera.WIDTH, 3), dtype=np.uint8)
    with patch.object(sys, "platform", platform), patch.dict(sys.modules, {"pyrealsense2": sdk}):
        with robot_camera.open_camera() as active:
            assert robot_camera.read_rgb(active).shape == (720, 1280, 3)
        sdk.config.return_value.enable_device.assert_called_once_with("stable-serial")
        camera.start.assert_called_once()
        camera.stop.assert_called_once()
    print(f"PASS: {platform} SDK adapter mocked; stable serial selection and cleanup")
print("Platform adapters tested offline; only macOS has real camera validation.")
