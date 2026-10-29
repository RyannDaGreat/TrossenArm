"""WXAI classic-DH geometry from official v1.8 specifications; meters and radians."""
import math

import einx
import numpy as np

FOLLOWER_TOOL_M = 0.156062
LEADER_TOOL_M = 0.156062  # Replaced by controller end-effector transform in live telemetry.


def dh(d, theta, a, alpha):
    """
    Pure function. Classic DH transform Rz(theta) Tz(d) Tx(a) Rx(alpha).

    Args:
        d, a (float): Distances in meters.
        theta, alpha (float): Angles in radians.
    Returns:
        ndarray: (4, 4) homogeneous transform, e.g. identity rotation with XYZ translation.
    Examples:
        >>> dh(1, 0, 2, 0)[:3, 3].tolist()
        [2.0, 0.0, 1.0]
    """
    c, s = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return np.array([[c, -s*ca, s*sa, a*c], [s, c*ca, -c*sa, a*s],
                     [0, sa, ca, d], [0, 0, 0, 1]], dtype=float)


def forward(joints, tool_m=FOLLOWER_TOOL_M):
    """
    Pure function. Compute WXAI joint-frame points and tool transform in its base frame.

    Args:
        joints: Six angles, shape (6,), in radians.
        tool_m (float): Flange-to-tool +X distance in meters.
    Returns:
        tuple: (9, 3) XYZ points and (4, 4) tool transform. These are frame origins, not collision meshes.
    Examples:
        >>> points, tool = forward([0, 0, 0, 0, 0, 0])
        >>> points.shape, np.allclose(tool[:3, 0], [1, 0, 0])
        ((9, 3), True)
        >>> _, tool = forward([0, math.pi/2, 2.2, math.pi-2.2, 0, 0])
        >>> np.allclose(tool[:3, 0], [0, 0, 1])
        True
    """
    if len(joints) != 6 or not all(math.isfinite(q) for q in joints):
        raise ValueError("Expected six finite joint angles")
    q0, q1, q2, q3, q4, q5 = joints
    table = [(0.1035, q0, 0.02, -math.pi/2),
             (0, q1+math.pi, 0.264, math.pi),
             (0, q2-math.pi/2-math.atan2(0.245, 0.06), math.hypot(0.245, 0.06), 0),
             (0, q3-math.atan2(0.06, 0.245), 0.06775, math.pi/2),
             (0, q4+math.pi/2, 0, math.pi/2), (0.02895, q5, 0, math.pi/2),
             (0, math.pi/2, 0, 0), (0, 0, tool_m, 0)]
    transform = np.eye(4)
    points = [transform[:3, 3].copy()]
    for row in table:
        transform = einx.dot("I J, J K -> I K", transform, dh(*row))
        points.append(transform[:3, 3].copy())
    return np.array(points), transform
