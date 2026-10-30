"""Command. Make Up prepare matching pair base angles and document the change."""
from pathlib import Path
p=Path('agents/manifest.md'); s=p.read_text(); s += '\n## Up base alignment\nUp sets matching encoder headings for each pair: left +91.2 degrees, right -87.6 degrees, using the previously visually aligned follower headings. Leaders use the same encoder target for absolute puppeteering; this does not establish their world compass direction. Up retains tall geometry, resets both wrist axes and opens the gripper. All seven axes use the existing eight-second trajectory and unchanged factory bounds, speed checks, heartbeat, stop and ownership. Tests must prove differing initial base angles converge to the same per-pair target. Deployment requires the requested backend restart approval; no automatic motion on deployment.\n'; p.write_text(s)
p=Path('web/source/backend/presets.py'); s=p.read_text(); a=s.index('\n\nclass Released')
s=s[:a]+'''

# Previously visually aligned follower headings; leaders share encoder angles for copying.
UP_BASE_RADIANS = {"left": math.radians(91.2), "right": math.radians(-87.6)}


def up_target(role, current, bounds):
    """
    Pure function. Prepare a tall pose with the matching pair's standard base angle.

    Args: role: known arm role; current: six radians; bounds: six factory intervals.
    Returns: Six angles, including a common base target for each leader/follower pair.
    Examples:
        >>> bounds = [(-math.pi, math.pi)]*2 + [(0, 2.356194496)] + [(-math.pi, math.pi)]*3
        >>> a = up_target("leader_right", [0]*6, bounds)
        >>> b = up_target("follower_right", [-2, 0, 0, 0, 0, 0], bounds)
        >>> a == b, round(math.degrees(a[0]), 1)
        (True, -87.6)
    """
    if role not in ROLES:
        raise ValueError("Unknown arm role")
    target = tall_target(current, bounds)
    target[0] = UP_BASE_RADIANS[role.rsplit("_", 1)[1]]
    if not bounds[0][0] <= target[0] <= bounds[0][1]:
        raise ValueError("Up base heading does not fit the current factory limits")
    return target
''' + s[a:]
s=s.replace('heading="Keep base yaw; reset wrists and open gripper"','heading="Align pair base angles; reset wrists and open gripper"').replace('self.target = tall_target(reference[:6], bounds[:6])','self.target = up_target(role, reference[:6], bounds[:6])'); p.write_text(s)
p=Path('agents/.scratchpad/presets_offline_test.py');s=p.read_text().replace('(0.2, 0.0))','(presets.UP_BASE_RADIANS["left"], 0.0))');p.write_text(s)
print('Added per-pair Up base targets and documentation.')
