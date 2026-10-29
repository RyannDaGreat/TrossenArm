"""Offline driver check. Imports the package without connecting to any robot."""

from importlib.metadata import version

import trossen_arm

EXPECTED_DRIVER_VERSION = "1.8.8"
REQUIRED_METHODS = (
    "configure",
    "cleanup",
    "get_modes",
    "get_joint_limits",
    "set_joint_limits",
    "get_gripper_position",
    "set_gripper_mode",
    "set_gripper_position",
)

assert version("trossen-arm") == EXPECTED_DRIVER_VERSION
assert hasattr(trossen_arm.StandardEndEffector, "wxai_v0_follower")
for method in REQUIRED_METHODS:
    assert hasattr(trossen_arm.TrossenArmDriver, method), method
print(f"PASS: trossen-arm {EXPECTED_DRIVER_VERSION}; follower gripper API available.")
print("No driver instance created; no network or motion commands sent.")
