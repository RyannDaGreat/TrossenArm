# Cardinal directions — read-only image findings

## Checklist

- [x] Inspect current duck in fixed-camera images.
- [x] Define the camera-view cardinal directions.
- [x] Check whether encoder yaw is already registered to room north.
- [x] Derive stock-camera registration and estimate north from wrist-camera wall lines.
- [ ] Validate the registration assumptions with contemporaneous joints, source image geometry, and observed motion; image estimates are not exact calibration.

## Verified direction reference

User definition: the rubber duck's beak defines north. East is to the right when facing north; west is left; south is behind. Vertical up is separate from north.

Evidence: `agents/.scratchpad/follower_left-tall-motion/upright-stage-0-top.png` and `upright-stage-0-bottom.png`, captured 2026-10-29 around 21:02. In the top image the duck's orange beak is at its top, toward the wall and rear horizontal rail; its tail is at the bottom. The bottom image shows the duck's back, consistent with the beak pointing away from this camera.

| Direction | Top camera image | Physical description |
| --- | --- | --- |
| North | Toward image top | Toward the wall / rear crossbar |
| East | Toward image right | Toward the right follower side |
| South | Toward image bottom | Toward the fixed camera / front table edge |
| West | Toward image left | Toward the left follower side |
| Up | Not a tabletop compass direction | Vertically away from the tabletop |

These are qualitative scene directions, not calibrated metric coordinates. Perspective means an exact tabletop angle cannot be read as an equal pixel angle. The duck is slightly off the image centerline, so the mapping means the table's broad north/south axis, not a fabricated exact pixel-unit north vector.

## Arm headings: what is and is not established

The two arms' visible bent configurations are not simply north-parallel: they have opposing inward lateral components in the fixed-camera images. An exact NE/NW label is not verified because vertical height also projects toward image top; image-tip minus image-base direction mixes height and tabletop heading.

The saved left tall plan preserves base yaw 0.7974746227 rad. Earlier right feedback gives about -0.4163805544 rad. These are encoder angles in independent base frames. Neither the manifest nor geometry module supplies each base's mounting transform into the room. Equal q0 values do not establish parallel room headings, and q0=0 must not be assumed to mean north.

For a precise command, the remaining information is each robot base's positive-X orientation relative to duck north (and the encoder-positive rotation direction in the room). This can come from a verified physical mounting/reference axis or measured camera/base registration. No blind scan or base rotation was performed by this delegate.

At the tallest target, wrist yaw is zero and the tool is only about 0.020 m radially from the base. The shoulder-to-elbow bend extends approximately 0.0495 m on the opposite side. Therefore tool-tip horizontal location becomes a weak visual heading cue. A clear convention is: 'facing north' means the arm's positive radial direction is north, with the elbow on the south side at the tall pose. This convention needs confirmation in the task record before claiming that north alignment is achieved.

## Sources and limits

- `web/source/backend/geometry.py`: q0 is the first local DH rotation; output is local-base XYZ, not registered room XYZ.
- `agents/manifest.md`: states separate base frames and absent world registration.
- No SDK connection, direct camera access, or motor command was used. The later wrist-camera study fetched the official stock URDF and license because the exact camera transform was missing locally; both are saved offline below.
- One read-only `rg` command failed because an unmatched zsh `*.md` glob expanded before execution. It did not modify state; subsequent findings use explicit source paths.

## Follow-up: qualitative headings and possible mounting convention

Re-inspected original bent poses in `follower_right-motion/upright-stage-4-top.png`, `follower_left-motion/upright-stage-4-top.png`, and the folded `current-top.jpg`. Left has an inward/east component and right an inward/west component. Northeast for the left and northwest for the right are plausible qualitative interpretations, but remain unverified because arm height projects upward and outward in this perspective camera. Do not present these as measured compass bearings.

A mirrored mounting convention (left local +X=east, right local +X=west) is consistent with those apparent inward directions and the recorded yaw values. It is only a hypothesis. Under that hypothesis north would correspond to opposite signed quarter-turn yaw values, not zero; these are not established command targets. There is no evidence that q0=0 means north on both robots.

Concrete next step: obtain a fixed-camera view containing the duck, complete arm links, and bases. Root has asked the user to tilt the camera for this view because the tall tips are outside the existing frame. Identify the physical base reference or validate heading with a single small, deliberate, observed yaw adjustment, preserving the tall joint pose and checking cable/fixture clearance. Only root may command that adjustment. Do not substitute a wide scanning sweep for registration. A small adjustment establishes rotation sense, but does not alone prove the full absolute north angle; use the visible pose/reference as well.

## Wrist-camera registration study — stronger evidence

The upward-looking wrist images provide a second physical reference: the north wall / ceiling junction. The wall plane is assumed perpendicular to duck north. Images: `agents/.scratchpad/north-current-left.jpg` and `north-current-right.jpg`, each 640 × 480. In the left image the wall occupies the lower-left side of the diagonal; in the right image it occupies the lower-right side.

Official stock source, pinned to commit `1f36d47d104ad9370eb9a30ac255f682c42449c5`:
`https://raw.githubusercontent.com/TrossenRobotics/trossen_arm_description/1f36d47d104ad9370eb9a30ac255f682c42449c5/urdf/generated/wxai/wxai_follower.urdf`

Offline assets:

- `agents/.scratchpad/cardinal-assets/wxai_follower.urdf`
- `agents/.scratchpad/cardinal-assets/LICENSE` (BSD 3-Clause, downloaded from the same commit)
- `agents/.scratchpad/cardinal-assets/wall-line-analysis.json` (numeric results)
- `agents/.scratchpad/scratchpad_agent_cardinal.py` (reproduction command: `uv run agents/.scratchpad/scratchpad_agent_cardinal.py`; no hardware imports)

The URDF camera chain is link_6 → mount (translation 0.012 m on X) → camera screw frame (translation [0.02927207801, 0, 0.03824951197] m and +20° rotation about Y) → camera_link (translation [0.01085, 0.009, 0.021] m) → color frame (identity) → color optical frame (roll −90°, pitch 0°, yaw −90°). The gripper/tool fixed frame has identity rotation relative to link_6. Thus, using active rotations with column vectors:

`R_tool_optical = Ry(20°) Rz(−90°) Rx(−90°)`.

Optical axes expressed in tool coordinates are:

- pixel-right optical X: `[0, −1, 0]`
- pixel-down optical Y: `[−sin(20°), 0, −cos(20°)]`
- forward optical Z: `[cos(20°), 0, −sin(20°)]`

The stock URDF link_6 orientation is `Rz(q0) Ry(q1−q2−q3) Rz(−q4) Rx(q5)`. The analysis script independently composes this chain and asserts equality with `geometry.forward` for both saved poses. This passed. The right wrist roll of approximately −30° must be included; line tilt is not simply base yaw.

For a measured image line `L = [a,b,c]` with `a*u + b*v + c = 0`, and camera intrinsics K, the plane normal containing the camera center and the observed straight wall junction is:

`m_base = R_base_tool R_tool_optical Kᵀ L`.

The wall junction is horizontal and parallel to east–west. Therefore the horizontal projection `[m_x,m_y,0]` is parallel to the wall normal. Select its sign toward the visible wall, which is `b>0` for these images. North bearing in the robot's base frame is `atan2(m_y,m_x)`. Translation is irrelevant to the bearing calculation. This uses a horizontal physical line; an arbitrary diagonal object edge cannot replace it.

Using tall-stage endpoint joint feedback, four long wall-line segments per camera, principal point (320,240), square pixels, and assumed focal lengths 280–600 pixels:

| Arm | Estimated local-base north bearing | Current base yaw | Approximate required yaw change |
| --- | --- | --- | --- |
| Left follower | +91.0° to +91.5° | +45.69° | +45.5° |
| Right follower | −87.8° to −87.4° | −23.88° | −63.8° |

These estimates strongly support mirrored base mounting. They do not establish a high-precision command target. The values use endpoint joints rather than proven photo-synchronous feedback, and require stock camera orientation, no mirrored/rotated image, aspect-preserving image formation, approximately square native pixels, vertical bases, and a wall perpendicular to duck north. Unknown distortion and actual mount tolerances remain. Focal sensitivity is under half a degree for these measured segments; that does not bound all systematic errors.

If those assumptions are confirmed, the positive radial arm direction currently points approximately northeast on the left (45.5° east of north) and northwest on the right (63.8° west of north). This refers to the arm's radial bending plane, not the near-vertical gripper axis. At the tall pose its elbow is on the opposite side from the small positive radial tool offset.

Proposed verification for the hardware owner: confirm image source dimensions/aspect ratio and current joint feedback; then make one small observed yaw adjustment in the intended direction while holding other joints fixed, capture the same wall, and recompute. The inferred local-base north bearing should remain approximately constant while the apparent line rotates by the predicted camera rotation. This tests mounting/sign assumptions without scanning. Continue only with root's camera/clearance checks; this delegate has issued no motion command. If a numerical fit disagrees between before/after, stop treating the nominal quarter-turn mounting convention as calibrated.

Offline script correction: OpenCV returned Hough segments shaped `(N,4)` in this environment, not `(N,1,4)` as initially assumed. Flattening each segment fixed the explicit TypeError; the rerun completed and wrote the JSON. No exception was hidden.
