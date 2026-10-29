"""Read gripper configuration and telemetry without enabling a control mode or moving."""

import trossen_arm as arm

robot = arm.TrossenArmDriver()
try:
    robot.configure(arm.Model.wxai_v0, arm.StandardEndEffector.wxai_v0_follower,
                    "192.168.1.4", False, 5.0)
    print("Modes:", robot.get_modes(), flush=True)
    print("Errors:", robot.get_error_information(), flush=True)
    print("Position:", robot.get_gripper_position(), "effort:", robot.get_gripper_effort(),
          "compensation:", robot.get_gripper_compensation_effort(), flush=True)
    print("Friction coulomb:", robot.get_friction_coulomb_coefs(), flush=True)
    print("Friction viscous:", robot.get_friction_viscous_coefs(), flush=True)
    print("Position offsets:", robot.get_position_offsets(), flush=True)
    for mode, parameters in robot.get_motor_parameters()[-1].items():
        for loop in ("position", "velocity"):
            pid = getattr(parameters, loop)
            print(mode, loop, {key: getattr(pid, key) for key in ("kp", "ki", "kd", "imax")}, flush=True)
    limit = robot.get_joint_limits()[-1]
    print("Limits:", {key: getattr(limit, key) for key in
          ("position_min", "position_max", "position_tolerance", "velocity_max",
           "velocity_tolerance", "effort_max", "effort_tolerance")}, flush=True)
finally:
    robot.cleanup()
