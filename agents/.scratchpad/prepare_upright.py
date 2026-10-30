"""Read-only robot geometry check and offline path plan; no mode or position commands."""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import trossen_arm as arm

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "web/source/backend"))
from geometry import forward

role = os.environ.get("TROSSEN_MOTION_ROLE", "follower_right")
ip = {"follower_right": "192.168.1.4", "follower_left": "192.168.1.5",
      "leader_right": "192.168.1.2", "leader_left": "192.168.1.3"}[role]
preset = "wxai_v0_leader" if role.startswith("leader") else "wxai_v0_follower"
pose = os.environ.get("TROSSEN_MOTION_POSE", "upright")
if pose not in {"upright", "tall", "north"}:
    raise ValueError(f"Unknown pose: {pose}")
folder = Path("agents/.scratchpad") / (f"{role}-{pose}-motion" if pose != "upright" else f"{role}-motion")
folder.mkdir(exist_ok=True)
robot = arm.TrossenArmDriver()
try:
    robot.configure(arm.Model.wxai_v0, getattr(arm.StandardEndEffector, preset), ip, False, 5.0)
    start = list(robot.get_arm_positions())
    modes = list(robot.get_modes())
    limits = robot.get_joint_limits()[:6]
    assert modes == [arm.Mode.idle] * 7, modes
    assert robot.get_error_information() == "No error"
    cartesian = list(robot.get_cartesian_positions())
    _, current = forward(start)
    print("Current joints:", start, "controller Cartesian:", cartesian, flush=True)
    print("Offline FK XYZ:", current[:3, 3], "direction:", current[:3, 0], flush=True)
    assert np.allclose(current[:3, 3], cartesian[:3], atol=0.005), "Controller/model mismatch"
    target = ([start[0], math.pi/2, math.pi/2, 0, 0, start[5]] if role.startswith("leader")
              else [start[0], math.pi/2, 1.7, math.pi-1.7, 0, start[5]])
    if pose == "tall":
        assert role.startswith("follower"), "Tall target is verified for follower geometry only"
        upper_length, forearm_length = 0.264, math.hypot(0.245, 0.06)
        elbow = limits[2].position_max
        included_angle = elbow + math.atan2(0.06, 0.245)
        shoulder = math.atan2(upper_length - forearm_length * math.cos(included_angle),
                              forearm_length * math.sin(included_angle))
        target = [start[0], shoulder, elbow, shoulder + math.pi/2 - elbow, 0, start[5]]
    if pose == "north":
        north_degrees = {"follower_left": 91.2, "follower_right": -87.6}
        target = [math.radians(north_degrees[role]), *start[1:5], 0.0]
    bounds = [(limit.position_min, limit.position_max) for limit in limits]
    print("Factory joint bounds:", bounds, flush=True)
    print("Factory position tolerances:", [limit.position_tolerance for limit in limits], flush=True)
    print("Factory velocity limits:", [limit.velocity_max for limit in limits], flush=True)
    for index, (value, limit) in enumerate(zip(start, limits)):
        if not limit.position_min-limit.position_tolerance <= value <= limit.position_max+limit.position_tolerance:
            raise RuntimeError(f"Joint {index} outside factory feedback bounds: {value}")
    for q, (lo, hi) in zip(target, bounds):
        assert lo <= q <= hi, (q, lo, hi)
    stages = []
    for fraction in np.linspace(0, 1, 101):
        joints = [a + float(fraction)*(b-a) for a, b in zip(start, target)]
        points, transform = forward(joints)
        # Geometry checks are not collision certification; report the whole sampled envelope.
        stages.append(points)
        if fraction in (0, 0.25, 0.5, 0.75, 1):
            print("Stage", fraction, "tool XYZ", transform[:3, 3], "direction", transform[:3, 0], flush=True)
    points = np.concatenate(stages)
    print("All sampled frame-origin bounds:", points.min(axis=0), points.max(axis=0), flush=True)
    plan = {"ip": ip, "role": role, "pose": pose, "preset": preset, "start": start, "target": target, "limits": bounds,
            "position_tolerances": [limit.position_tolerance for limit in limits],
            "controller_xyz": cartesian[:3],
            "fractions": [1.0] if os.environ.get("TROSSEN_CONTINUOUS") == "1" else [0.25, 0.5, 0.75, 1.0]}
    (folder / "upright-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print("Saved plan:", folder, flush=True)
finally:
    robot.cleanup()
