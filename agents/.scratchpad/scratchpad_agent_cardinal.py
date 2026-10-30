"""Offline stock camera rotation and wall-line bearing study; no hardware access."""
import json
import math
import sys
from pathlib import Path
import cv2
import einx
import numpy as np
sys.path.insert(0, str(Path('web/source/backend').resolve()))
from geometry import forward

pitch = math.radians(20)
mount = np.array([[math.cos(pitch), 0, math.sin(pitch)], [0, 1, 0],
                  [-math.sin(pitch), 0, math.cos(pitch)]])
optical = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]])
relative = einx.dot('I J, J K -> I K', mount, optical)
print('Optical axes expressed in tool coordinates:', relative.tolist())
results = {}
for role in ['left', 'right']:
    state = json.loads(Path(f'agents/.scratchpad/follower_{role}-tall-motion/upright-status.json').read_text())
    _, transform = forward(state['joints'])
    camera = einx.dot('I J, J K -> I K', transform[:3, :3], relative)
    # Verify that the DH tool orientation equals stock URDF link_6 orientation.
    yaw, shoulder, elbow, wrist, wrist_yaw, roll = state['joints']
    urdf_rotation = np.eye(3)
    for axis, angle in [('z', yaw), ('y', shoulder-elbow-wrist), ('z', -wrist_yaw), ('x', roll)]:
        cosine, sine = math.cos(angle), math.sin(angle)
        axis_rotation = {
            'x': np.array([[1,0,0],[0,cosine,-sine],[0,sine,cosine]]),
            'y': np.array([[cosine,0,sine],[0,1,0],[-sine,0,cosine]]),
            'z': np.array([[cosine,-sine,0],[sine,cosine,0],[0,0,1]]),
        }[axis]
        urdf_rotation = einx.dot('I J, J K -> I K', urdf_rotation, axis_rotation)
    assert np.allclose(urdf_rotation, transform[:3, :3])
    image = cv2.imread(f'agents/.scratchpad/north-current-{role}.jpg')
    assert image.shape == (480, 640, 3)
    lines = cv2.HoughLinesP(cv2.Canny(image, 40, 100), 1, math.pi/1800, 80,
                            minLineLength=180, maxLineGap=30)
    print(role, 'joints', state['joints'], 'camera_R', camera.tolist())
    records = []
    for wrapped in lines:
        x1, y1, x2, y2 = map(float, wrapped.ravel())
        if x2 == x1:
            continue
        slope = (y2-y1)/(x2-x1)
        if role == 'left' and not 0.7 < slope < 1.2:
            continue
        if role == 'right' and not -0.9 < slope < -0.45:
            continue
        # The north wall occupies lower-left/left or lower-right/right of these lines.
        line = np.array([y1-y2, x2-x1, x1*y2-x2*y1])
        if line[1] < 0:
            line = -line
        bearings = {}
        for focal in [280, 350, 420, 500, 600]:
            principal_x, principal_y = 320, 240
            ray_plane = np.array([focal*line[0], focal*line[1],
                                  principal_x*line[0]+principal_y*line[1]+line[2]])
            normal = einx.dot('I J, J -> I', camera, ray_plane)
            bearings[focal] = math.degrees(math.atan2(normal[1], normal[0]))
        record = {'pixels': [x1,y1,x2,y2], 'slope': slope, 'north_degrees_by_focal': bearings}
        print(record)
        records.append(record)
    results[role] = {'joints': state['joints'], 'camera_R': camera.tolist(), 'lines': records}
Path('agents/.scratchpad/cardinal-assets/wall-line-analysis.json').write_text(json.dumps(results, indent=2)+'\n')
