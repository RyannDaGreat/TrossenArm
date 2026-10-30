# Goal and current state

North turn execution: stock wrist-camera geometry and north-wall junction estimates place local north at approximately +91.2° left and −87.6° right. Use these approximate bearings for one continuous eight-second base turn per follower, preserve current shoulder/elbow/pitch, and bring tool roll to zero so both wrists share the same orientation. This is visual compass alignment, not precision calibration. Inspect fresh pre/post camera images and encoder/error readbacks; unchanged factory bounds and single hardware owner apply. Evidence and assumptions: `agents/.scratchpad/cardinal-findings.md`, pinned stock URDF and wall-line analysis in `agents/.scratchpad/cardinal-assets/`.

Control and observe four Trossen WXAI arms from this portable Git project. Keep robot identity, hardware ownership, current geometry, and measured camera performance explicit. Never infer collision clearance or metric room coordinates from uncalibrated camera images.

**Current result:** both followers reached the locally derived maximum-height pose within existing nominal joint limits, about 0.85345 m above their own bases. Left used four observed 8/3-second stages; right completed one continuous eight-second move. Both ended idle/no error. Post-idle heights were left0.85278 m and right0.85302 m. Earlier bent poses did not meet the user's intended height and are historical evidence only. Both bases now face approximate duck north (+91.2° left, −87.6° right); both tool rolls are zero. Post-turn wrist images show the north wall level. This is visual alignment, not precision calibration. The two-view recorder is `agents/.scratchpad/record_two_views.py`; `scratchpad.py` is the disposable offline height study.

Do not auto-enable following. The viewer owns four cameras and all robot telemetry drivers; stop it before standalone motor scripts and confirm the previous owner has exited. Never issue competing driver commands. AX88179A/en8 is configured and verified at 192.168.1.100/24.

**Verified:** four live camera feeds, live encoder-driven geometry for all four arms, right-follower small/full gripper cycles, and a staged sky-facing right-follower pose. The dashboard was tested with Puppeteer, visually inspected, opened in the browser, and announced through both channels. A 20-second browser test measured approximately 30 drawn frames/second for each camera; exact results are in `agents/.scratchpad/web-verification.json`. This is not a long-duration soak or exposure-to-screen latency certification.

**Pending:** left-pair puppeteering is implemented and the user's physical trial moved the follower, but it stopped on the software measured-velocity guard; this is not yet a reliable completed trial. The final 60 ms target-interpolation adjustment and detailed speed diagnostics are offline-tested only, not live-tested. Do not restart it automatically. Both leaders copied the raised follower joint poses on 2026-10-29, with verified feedback and final idle/no error. A static four-view environment inventory exists; no 360-degree arm sweep or calibrated room map exists. Full-stroke video replay still needs its own final VLM/Finder delivery check.

# Glossary

- Dump: self-contained, movable Git project, with no dependency on its absolute location.
- Leader: finger-handle arm used as operator input. Follower: corresponding output arm.
- SDK: vendor device-control interface. UVC: standard USB camera interface.
- Nominal bounds: minimum/maximum positions accepted as motor targets. Feedback tolerance: additional measured-position allowance around those bounds before the controller reports a fault; it does not extend the permitted targets.
- VLM: the assistant's visual inspection of real captured images/video frames.
- Idle: vendor braking state, not electrical power off or guaranteed exact position hold.
- FK: forward kinematics; joint angles transformed into link/tool geometry.
- DH: Denavit–Hartenberg convention used by the manufacturer's geometry table.
- Base frame: one robot's local coordinate system. World registration: calibrated placement of different bases/cameras in one coordinate system; not implemented.
- Relative teleoperation: preserve the starting follower pose and mirror changes in leader joints rather than immediately copying unmatched absolute angles.
- Deadman: a control that must stay actively held/refreshed; releasing it or losing heartbeat stops powered following.
- Autopilot: make routine decisions without unnecessary blocking. Bulldog: persist without bypassing safety. Babysitting: monitor ongoing work until stopped. Ponytail: smallest complete, checked implementation.
- Glossary: definitions of project-specific terms.

# Offline reference — start here

Read this index and search the listed local source before using the internet. Keep newly learned behavior, source version, and local evidence in this manifest; keep mistakes and superseded interpretations in `agents/concerns.md`. Use the internet for facts missing from the local material or for a deliberate version check. Paths below are relative to the Git root. The vendor checkout is `agents/.scratchpad/trossen_arm/`, verified tag `v1.8.8`, revision `084ef0a74d3e6b71d640ac9907e4b48e04efcdcf`; its recreation command is in Reproducibility and verification.

| Question | Local source and entry point |
| --- | --- |
| What is a command bound versus a feedback tolerance? | `agents/.scratchpad/trossen_arm/docs/getting_started/configuration.rst`, Joint Limits, lines 418–427; `agents/.scratchpad/trossen_arm/include/libtrossen_arm/trossen_arm_type.hpp`, `JointLimit`, lines 136–152 |
| What units, duration, and modes does the SDK accept? | `agents/.scratchpad/trossen_arm/include/libtrossen_arm/trossen_arm.hpp`, `set_arm_positions` around line 129, `set_joint_modes` around line 601, `set_arm_modes` around line 637 |
| What are this connected arm's actual limits and pose? | `agents/.scratchpad/prepare_upright.py`; recorded left-follower check: `agents/.scratchpad/logs/left-preflight-20261029.log`. Requires exclusive SDK ownership; never run alongside the viewer. |
| How are changed USB ports and camera identities handled? | `web/source/backend/robot_camera.py`: `mac_usb_serials`, `discover`, `select_camera`; `web/source/backend/server.py`: `SERIAL_ROLES`, `assign_roles`; `agents/.scratchpad/usb_identity_probe.py` for raw local USB identity records |
| How do I inspect cameras or record without rediscovering the approach? | Running viewer: `/api/status` and `/api/camera/{role}/snapshot.jpg`. Standalone scripts: `agents/.scratchpad/preview_cameras.py`, `camera_montage.py`, and `scratchpad.py` (two-view 640×480 recording; live gripper opt-in). The preview script's 1280×720 default failed on this Mac; use the verified 640×480 profile. |
| How are staged poses executed and checked? | `agents/.scratchpad/raise_arm.py`, `upright_offline_test.py`; per-arm plans, approvals, snapshots, and measured status under `agents/.scratchpad/<role>-motion/` |
| Where are geometry and fault behavior documented? | `agents/.scratchpad/trossen_arm/docs/specifications.rst`, `docs/troubleshooting.rst`; implementation: `web/source/backend/geometry.py` |
| How do I verify the existing UI without touching motors? | `agents/.scratchpad/verify_web.mjs`; saved `web-verification.json` and `web-viewer.png`. `verify_controls.mjs` mocks all control POSTs. |

## Joint-limit facts needed for the current lift

The local v1.8.8 configuration document distinguishes **command clipping** from **feedback fault checks**. Position commands are clipped to `min(max(command, position_min), position_max)`. Measured position is checked against `position_min - position_tolerance` and `position_max + position_tolerance`. Header units are radians for arm position/tolerance and radians per second for arm velocity. A feedback reading outside nominal bounds alone is insufficient to diagnose a limit fault; inspect the configured tolerance and controller error. Tolerance is not permission to send targets outside nominal bounds or proof of collision clearance.

Actual left-follower readback at 2026-10-29 20:56:42 (`left-preflight-20261029.log`):

| Quantity | Measured/configured value |
| --- | --- |
| Wrist yaw / nominal maximum | 1.6397726536 / 1.5707963705 rad; excess 0.0689762831 rad, about 3.95° |
| Position tolerance, joints 0–2 | 0.200000003 rad |
| Position tolerance, wrist joints 3–5 | 0.400000006 rad |
| Velocity maximum, joints 0–2 | 6.283185482 rad/s |
| Velocity maximum, wrist joints 3–5 | 9.424777985 rad/s |

This wrist reading is inside the existing feedback allowance. The authorized lift uses a two-second initial target explicitly clamped to nominal bounds, then four quarter-waypoints toward `[starting yaw, π/2, 1.7, π−1.7, 0, starting roll]`. `TROSSEN_STAGE_SECONDS` selects the stage duration, bounded to 8/3 through 8 seconds; gripper stays idle, each stage is observed, and errors trigger cleanup. No factory limit or tolerance is widened. These recorded numbers are evidence for this readback, not defaults to assume for another arm or after reconfiguration. They also do not alter the separate, stricter puppeteering trial guards.

# Requirements and workflow

All actual human inputs belong in `agents/transcript.md`, near-verbatim with obvious dictation artifacts/stutters removed, no semantic reinterpretation, and unclear words marked. Keep editorial notes outside quotations. The transcript is the record of user ideas; this manifest also includes explicitly identified implementation decisions.

- Portable dump. One scoped instruction file, `AGENTS.md`; current work in `agents/todo.md`; current design here; append-only mistakes/results in `agents/concerns.md`. No redundant notes file.
- Experiments and evidence stay under `agents/.scratchpad/`. The user explicitly requested promotion of the web app into `web/`.
- Root `pyproject.toml` and `uv.lock`; **Python and dependencies through `uv run` only. Never any pip-install command.** Keep generated environments/caches inside the dump, ignored and recreated after moving it.
- Orthogonal commits using `[P]` prefix; no push unless requested. User made initial commit `9b25ae3`.
- This session requests a timely finite hardware demonstration. Historical session modes do not auto-enable following or repeated motion.
- No unnecessary intermediate speech. Answer direct status questions. Report verified outcomes and genuine terminal blockers, not setup milestones as completed tasks.
- Current speech instruction: chat first, then speak one or two English sentences through `https://ntfy.sh/shine_rut` only after completing the task. Say Yankee Doodle after verified raised arms. No intermediate speech or old-topic delivery.
- Concise functions, explicit CQS classification and examples, documented image/tensor shapes, meaningful error reports. No silent runtime fallback. Use einx for applicable tensor operations. All CSS component sizes/colors use root custom properties.
- No absolute project paths stored in code. Derive the Git/project root at runtime. Windows/Linux camera adapters are mock-tested; only this Mac has real hardware verification.

# Network and identity

| User label | IP | MAC |
| --- | --- | --- |
| Leader right | 192.168.1.2 | 04:e9:e5:1a:5f:78 |
| Follower right | 192.168.1.4 | 04:e9:e5:1a:5e:5f |
| Leader left | 192.168.1.3 | 04:e9:e5:18:11:da |
| Follower left | 192.168.1.5 | 04:e9:e5:1a:5e:8b |

Controllers report `wxai_v0`, firmware `1.8.4`; use driver `trossen-arm==1.8.8` (matching minor version), Python 3.12. The vendor core is a precompiled binary, not audited implementation source. Do not upgrade firmware merely to match a newer package.

Current setup: AX88179A network service on `en8`, manual `192.168.1.100/24`, no router. Wi-Fi and VPN remain unchanged. Discover service/interface identity before configuring a new host. The current right-follower route/ping check succeeded after `networksetup -setmanual AX88179A 192.168.1.100 255.255.255.0`.

Reachability and a label do not alone certify physical identity, mounting, or clearance. The user reports a visual safety check and has separately authorized gripper, upright follower, leader, and left-pair puppeteering work. Scope those permissions to the requested tasks, not arbitrary scans.

# Camera library and roles

Canonical library: `web/source/backend/robot_camera.py`; scratchpad import shim preserves earlier experiments.

| Role | Stable serial |
| --- | --- |
| Left wrist | 418643070450 |
| Right wrist | 418643070460 |
| Top | 418643070452 |
| Bottom | Not reported on this Mac's USB2 path |

All four are Intel RealSense D405, VID/PID `8086:0b5b`. Camera USB and robot Ethernet are separate connections.

- macOS: enumerate native UVC devices with `cv2-enumerate-cameras`. Join current AVFoundation UID location to current USB-registry location and serial; never save an OS camera index. Missing serial is explicit `None`. Ignore child service records lacking physical-device identity rather than confusing them with USB devices.
- Windows/Linux: explicit RealSense SDK path, select model/serial. No hidden fallback from SDK failure. Mac uses UVC by design because its SDK device-access probe failed.
- Match the three known serials to roles. The unique remaining fourth D405 is bottom. Missing/extra/ambiguous cameras fail loudly. On this Mac its observed UID was `0x11100080860b5b`; that is session-only, rediscovered at startup, never a portable key.
- `open_camera(serial=None, uid=None, width=1280, height=720, fps=30)` owns capture lifetime. A serial and UID must not both be supplied. `read_bgr(camera, width, height)` returns `(H,W,3)` uint8 BGR; `read_rgb(camera)` returns default `(720,1280,3)` uint8 RGB. The web backend uses 640×480 to accommodate USB2 bandwidth and four simultaneous feeds.
- Four-view montage: `agents/.scratchpad/four-camera-montage.png`, displayed and visually inspected. Images establish views, not a calibrated 360° map.

# Web observatory

The only visible entries directly under `web/` are `run-the-server.sh` and `source/`. The script resolves the repo root, builds the frontend with the lockfile, then starts the single Python backend on loopback port 28347. Change port with `TROSSEN_WEB_PORT` when required; choose a port far from existing listeners.

- `web/source/backend/server.py`: FastAPI lifecycle, camera capture/encoding, read-only arm telemetry, status JSON, JPEG snapshots, bounded WebSocket streams.
- `web/source/backend/geometry.py`: official classic-DH FK, output `(9,3)` XYZ frame origins and `(4,4)` tool transform. Uses einx matrix products. Tool forward is +X; stock leader/follower tool offset is 0.156062 m along flange +X.
- `web/source/frontend/`: Svelte/Vite, Three.js geometry, Futura system font with explicit sans-serif fallback, Swiss-style grid/typography/colors.
- Each camera has one capture thread, one encoder thread, one replaceable raw slot, and one replaceable JPEG slot. No accumulating frame FIFO. Encode once per frame, not per viewer.
- `/ws/camera/{role}` sends network-order uint64 sequence + float64 server read-return time + JPEG bytes. Browser acknowledges only after bitmap decode and canvas draw. One unacknowledged frame per viewer; timeout disconnects stalled viewers. JPEG WebSocket compression is disabled.
- `/api/status` exposes measured capture FPS, frame age, encoding time, post-read-to-draw ACK age, and arm state. `/api/camera/{role}/snapshot.jpg` returns the newest actual JPEG or explicit unavailability. No prerecorded substitution.
- Arm owners configure the correct leader/follower preset, never clear errors, and publish joints/modes/tool geometry at 20 Hz. FK XYZ must agree with controller XYZ within 5 mm. Geometry layout is **schematic in four separate base frames**, not a measured room arrangement. Idle/braked status is visible. A same-origin, loopback-only `/api/puppet` endpoint queues intent to the single left-pair owner; HTTP handlers never call the SDK. Right-arm owners publish telemetry and execute explicitly requested named presets.
- Browser tests: `agents/.scratchpad/verify_web.mjs`; results `agents/.scratchpad/web-verification.json`; screenshot `agents/.scratchpad/web-viewer.png`. Four feeds measured about 30 fps each over 20 seconds, five canvases rendered, all four FK checks passed, and no JS errors remained. Exact 30.000 fps minimum and exposure-to-screen latency are not certified. The ACK figure includes round trip after read return, not sensor exposure delay.

# Verified robot experiments

## Right-follower gripper

Small mode completed 12 open–close cycles. Original video `agents/.scratchpad/gripper-motion-20261028-210146.mp4` (2383 frames, 79.433 s); zoom replay `agents/.scratchpad/right-gripper-12-cycles-zoom.mp4` was VLM-checked, revealed in Finder, and announced. Telemetry log: `agents/.scratchpad/logs/gripper-twelve-cycles.log`.

Full mode completed four full cycles using factory targets near 0 and 0.04 m, eight seconds per half-cycle (64 seconds cycling). All eight telemetry endpoints passed; seven modes ended idle with no error. Recording: `agents/.scratchpad/gripper-full-stroke-20261028-212658.mp4` (2137 frames, 1280×720 H.264/yuv420p). Public-domain Yankee Doodle was posted only after measured movement. Final VLM/Finder replay delivery for this separate full-stroke file remains a TODO.

Control invariants in `gripper_test.py`/`record_gripper.py`: explicit live opt-in; camera-ready gate; correct `.4` follower preset; initial seven idle modes/no errors; preserve all six arm limits; 20 N gripper command cap, original 0.25 m/s velocity bound and feedback tolerances; never auto-increase force or widen position bounds. Neither cap is a certified human-contact safety rating. Initial out-of-bound feedback is accepted only within both factory tolerance and 1 mm. Endpoint tolerance is 1 mm; small mode requires ≥1 mm directional travel per 2 mm command; full mode requires ≥90% expected directional travel. Six arm joints remain idle and drift ≤0.005 rad. Always return idle/cleanup, surfacing cleanup failures too. Do not reuse the known-fault recovery flag for unknown faults.

## Right follower upright

Four staged waypoints completed under one persistent driver, with fresh top/bottom images inspected between stages. Plan preserves base yaw/tool roll, targets shoulder π/2, elbow 1.7 rad, wrist pitch π−1.7, wrist yaw 0. This is a verified derived pose, not a generic safe vendor recipe.

Final measured joints: `[-0.1302738935,1.5707255602,1.6996643543,1.4417868853,-0.0001907378,-0.6258106232]`; tool XYZ `[0.2530921779,-0.0331235099,0.7112664751]` m; forward `[0.0000948267,0.0001799440,0.9999999793]`. Final modes idle/no error. VLM confirmed sky-facing gripper, and an original success verse was spoken. Subsequent idle drift is observable; idle is not an exact position hold.

Scripts: `prepare_upright.py` (configuration/readback + offline model checks), `raise_arm.py` (single-owner staged motion), `upright_offline_test.py`. Runtime plans/approval/status and stage images stay ignored in the scratchpad. Stop requests and approval timeouts brake/clean up. Generalized runtime plan selects correct role/preset; never use a follower preset on a leader.

## Leaders

Both `.2` and `.3` return joint readings. Manufacturer-supported position mode and gravity-compensated external-effort mode are documented. Reference home/L candidate is `[0,π/2,π/2,0,0,0]`; preserve base yaw/tool roll when deliberately reducing unnecessary rotation. This is not proof of swept-volume safety.

Both leaders completed follower-pose copies on 2026-10-29. Right leader initial wrist yaw −1.8816 rad was inside the factory feedback allowance (nominal minimum −π/2, tolerance0.4 rad); all commanded targets stayed inside nominal bounds. Both completed one eight-second main trajectory and returned seven idle modes with No error. Human hands must leave handles before powered motion.

# Left-pair teleoperation — implemented; live trial incomplete

User wants leader-left `.3` to control follower-left `.5`. Vendor `demos/python/teleoperation.py` supports this but its example IPs differ, it automatically moves both arms home/sleep, and it copies absolute joints with force feedback. **Do not run that example unchanged.** Current poses are unmatched; direct copying can cause a large follower jump.

Implementation plan: preserve sole SDK ownership inside the web backend, use a dedicated left-pair owner rather than competing processes, start from latched relative joint references, rate/position-limit output, and avoid force-feedback amplification. Require an explicit held control and heartbeat to keep following active; loss of heartbeat/browser closure returns idle without an automatic home/sleep move. A bounded session and visible status must distinguish ready, active, limited, stopped, and faulted. The user explicitly requests robot controls in a themed modal, with toggle switches rather than checkboxes, and basic puppet enable/disable. The user rejected hold-to-follow because it occupies a hand needed on the leader. Use a latched on/off puppet toggle with a 0.5-second browser heartbeat timeout, 60-second session cap, 50 Hz pair loop, 0.25 rad/s command-rate limit, and ±0.25 rad initial-reference excursion cap. These are conservative assistant-selected trial bounds, not manufacturer-certified safety limits. Keep both grippers idle for the first arm-only trial; show this prominently. Initial follower corrections up to 0.002 rad at factory bounds must be disclosed and confirmed in the modal; larger mismatches block activation. Require an operator-clearance acknowledgement each time the modal is opened. Check tracking error, measured velocity, modes, controller faults, and timing; never auto-resume a faulted driver. Any browser motor endpoint must be loopback/same-origin guarded. A software heartbeat cannot guarantee stopping if the process or SDK blocks; require a reachable physical stop and explain this limitation. No automatic home/sleep/reset button until a calibrated safe path exists. At a software/factory position boundary, clamp only the affected joint inside unchanged bounds and display saturation; do not classify tiny encoder jitter at a boundary as an SDK fault. Continue enforcing command-rate, excursion, tracking, velocity, deadline, and mode guards. Toggle off, closing the modal, browser focus loss, heartbeat expiry, or session expiry stops and disables following. An acknowledgement is required before enabling. Research confirms the vendor supports this host-side loop; live human puppeteering remains unverified until tested.

The user also requests optional real robot models with a wireframe/model toggle, retaining the UI theme. Research found https://github.com/TrossenRobotics/trossen_arm_description at revision `1f36d47d104ad9370eb9a30ac255f682c42449c5`. Expanded URDFs: `urdf/generated/wxai/wxai_follower.urdf`, `wxai_leader_left.urdf`, and `wxai_leader_right.urdf` in that directory. Meshes are STL under `meshes/wxai/`; arm meshes use meters with identity visual origins, while `meshes/peripherals/d405.stl` needs the URDF's 0.001 scale and visual transform. Root license is BSD-3-Clause (Trossen 2025); camera description also carries Intel 2023/Apache-2.0 notices. Preserve notices. Use URDF link transforms, not DH-origin points alone, for mesh orientation. The researcher numerically compared the URDF and existing DH geometry over 100 synthetic poses. No model assets or model toggle have been installed yet, and none are registered to this room.

`puppet.py` now latches stop requests until the owner confirms idle, preserves per-client intent sequence numbers, checks cancellation/deadlines before each write, retires SDK instances that raise, stops the healthy follower before leader teardown, and reports `active=None`/`stop_unconfirmed` when braking cannot be established. Faults require deliberate restart; there is no automatic resume. The modal toggle frees both hands while sending heartbeats; closing/blur/off stops it. Boundary saturation clamps the affected joint and displays its requested/limited angle and whether the bound is from the controller or the ±0.25 rad trial window. Hardware limits are not widened. Measured follower speed remains guarded at 0.75 rad/s; final code reports joint and actual speed and interpolates targets over 0.06 seconds instead of instantaneous steps. The latter was added after the last physical speed-guard stop and has not been live-validated.

Offline controller tests cover mapping/boundary jitter, stop/rearm races, cancellation during activation, delayed reads, peer stopping order, failure status, heartbeat expiry, and cleanup. API tests reject foreign/missing Origin and invalid commands. Puppeteer tests intercept every control POST, so they validate the modal/toggle/heartbeat/stop UI without moving hardware. Latest stream measurements remained about 30 fps per camera. Human trial evidence is in `agents/.scratchpad/logs/puppet-trial-monitor.log`; do not describe the guard-stopped trial as fully successful.

# Environment inventory and safety limits

Stored four-camera images show a crowded tabletop, two follower assemblies, rails/uprights, loose cables, tools/small parts, equipment, nearby wall/chair/fabric panel, and people in some side views. Blind regions include behind housings, outside frame edges, under the table, and behind foreground jaws. No full 360° coverage, metric depth, collision meshes, extrinsics, or verified leader-base placement exists. Do not use an unverified sweeping arm to discover obstacles. A future scan needs current physical clearance, calibrated geometry, cable management, bounded joints, and one motion owner.

Driver faults may brake arms and close grippers; cleanup/destruction changes modes. Never continue using cached feedback after a driver daemon failure. Keep error clearing off unless an independently understood fault has an explicit recovery plan. Manufacturer limits are not contact-safe ratings. Do not disable safeguards because a task is slow.

# Reproducibility and verification

Root `pyproject.toml`/`uv.lock` define Python 3.12, camera/web/math dependencies, and optional `robot` extra (`trossen-arm==1.8.8`). Frontend package/lock files remain inside `web/source/frontend/`. No system installs were required. Ignore vendor checkout, environments, caches, node_modules, built dist, logs, runtime state, and camera media; track intentional code, locks, and documentation.

Run from repo root:

```sh
export UV_CACHE_DIR=agents/.scratchpad/uv-cache
export UV_PYTHON_INSTALL_DIR=agents/.scratchpad/uv-python
uv run --extra robot --locked agents/.scratchpad/gripper_test.py
uv run --extra robot --locked agents/.scratchpad/camera_offline_test.py
uv run --extra robot --locked -m doctest -v web/source/backend/geometry.py
./web/run-the-server.sh
```

Offline tests never imply Windows/Linux hardware validation or physical collision checking. Live tests must not run concurrently with the server owner. Puppeteer tests use a scratchpad script and an explicitly supplied local Chrome executable; do not hardcode its machine path into the portable project.

Official repository: https://github.com/TrossenRobotics/trossen_arm ; ignored local checkout tag `v1.8.8`, revision `084ef0a74d3e6b71d640ac9907e4b48e04efcdcf`. Recreate with `git clone --depth 1 --branch v1.8.8 https://github.com/TrossenRobotics/trossen_arm.git agents/.scratchpad/trossen_arm`. Versioned docs: https://docs.trossenrobotics.com/trossen_arm/v1.8/ . Key sources: `docs/specifications.rst` (DH), `docs/getting_started/configuration.rst` (limits/compensation), `docs/troubleshooting.rst` (faults), headers (API), and teleoperation/gravity-compensation demos. Historical failed approaches and corrections belong in concerns, not stale instructions here.

# Semantic Bindings

None.

# Current-session demonstration details

The current left-follower request and verified limit interpretation are defined near the top in Goal and current state and Offline reference. Do not widen limits, clear faults, or activate beyond factory feedback tolerance. Keep one driver owner and inspect stage images.

Use explicit 640x480 capture for recordings and staged snapshots on this Mac. Reuse the existing guarded gripper exercise when gripper motion is requested; no intermediate speech and no unknown-fault clearing. Motion scope follows the current user request; both follower lifts and subsequent leader copies are complete. Prefix every user-facing message and eventual speech with Marvin.

## Verified outcome on 2026-10-29

All four cameras delivered live 640x480 video at approximately 30 fps on the new Mac. Browser test passed; four robots reported ready/idle. Two right-follower gripper cycles were measured and visually checked, saved in agents/.scratchpad/gripper-right-20261029-205125.mp4 and gripper-top-20261029-205125.mp4 (574 frames each). Four observed right-follower lift stages completed: final tool XYZ [0.233651,-0.103001,0.711266] m, forward [0.000645,0.000341,0.9999997], final seven idle modes and no error. Stage images and status are in agents/.scratchpad/follower_right-motion/.

The left follower then completed all four 2.6666667-second stages with unchanged limits. Final measured joints were [0.7932783961,1.5543221235,1.7000458241,1.4417868853,-0.00171663996,0.00133516442]; tool XYZ [0.1717265173,0.1749072955,0.7151307443] m and forward [-0.0129481,-0.0107067,0.9998588468]. All seven joints finished idle with No error. The top image visually confirmed both followers raised. Evidence: agents/.scratchpad/follower_left-motion/upright-status.json, upright-stage-{0..4}-{top,bottom}.png, and agents/.scratchpad/logs/upright-left-20261029.log. Restore the web viewer as the single hardware owner after standalone motion exits. No automatic following.

After braking, measured idle drift reduced left tool height to 0.67395046 m (forward Z 0.9904169) and right height to 0.6919077 m (forward Z 0.997793). Both remained raised, idle, and error-free; stage endpoint coordinates are not an exact held pose. The viewer was restarted with all four feeds near 30 fps and opened at a fresh browser URL.

## Tallest upward follower target

Local DH geometry gives z = 0.1035 + a sin(s) + b sin(A-s) + 0.06775 + 0.02895 + 0.156062 when the final links/tool are vertical, where a=0.264 m, b=hypot(0.245,0.06) m, A=e+atan2(0.06,0.245), s=shoulder and e=elbow. For fixed e, maximize with s=atan2(a-b cos(A), b sin(A)). Over the configured elbow range [0, 3π/4], maximum height increases with e, so use the unchanged nominal elbow maximum; wrist pitch is s+π/2-e and wrist yaw is zero. Preserve base yaw/tool roll. Expected target is shoulder1.3045514, elbow2.3561945, wrist pitch0.5191532 rad; tool height0.8534476 m and horizontal radius0.020 m. This is the kinematic height maximum for this model and configuration, not permission to bypass clearance checks or change limits. Use distinct <role>-tall-motion runtime folders to preserve earlier pose evidence. Verify actual feedback and final views; idle may drift.

The user objects to repeated pauses and confirms the workspace is empty. For the already model-checked tall-pose transition, allow one continuous eight-second joint-space move, with initial/final camera inspection and the existing 20 Hz controller/error/stop checks. This avoids artificial stops at quarter-waypoints without widening limits or increasing motor limits. `TROSSEN_CONTINUOUS=1` in preparation selects fractions=[1.0]; runtime duration remains explicitly bounded. Unknown base-yaw registration is a separate issue and must not delay completing height changes at unchanged yaw.

## Duck-defined cardinal directions

North is the duck's beak direction, toward the wall/rear crossbar and top of the fixed-camera image. East is image-right/right-follower side; south is toward the fixed cameras/front table edge; west is image-left/left-follower side. Vertical up is separate. Verified from left-tall stage0 top/bottom images: orange beak at image top and duck's back facing bottom camera. Qualitative image directions are not a metric room calibration. Earlier arms had opposing inward lateral components; exact NE/NW labels are not verified because height affects projection. Separate local q0 frames have no verified compass offset; do not assume q0=0 means north. At tall pose, tool radial offset is only20 mm, and elbow lies on the opposite side; proposed facing convention is positive radial direction toward north. Wider fixed-camera coverage was requested because tall arms are now partly outside both fixed views. No base rotation has been performed for north alignment. Details/evidence: agents/.scratchpad/cardinal-findings.md.

## Arm-up preset controls

The operator wants a Swiss-style Robot controls panel with illustrated Left arm up and Right arm up actions alongside puppet mode. Use a clear grid, restrained colors, strong type hierarchy, concise labels and simple SVG arm diagrams. Record later design preferences here as they emerge. The presets raise a follower toward the validated tall pose in one eight-second interpolation, keeping its current base yaw and tool roll: encoder zero is not a verified north heading. Wrist yaw becomes zero for a vertical tool. A preset and puppet mode cannot own motion concurrently. Browser intent is ordered, expires after 0.5 seconds without heartbeat, and stops on blur, close or Stop. Only the existing SDK-owner thread writes motors. Limits stay unchanged; faults never auto-clear; uncertain stops remain explicit. Hardware behavior still requires a supervised live validation after offline tests.

Implementation: `web/source/backend/presets.py` owns ordered preset intent; `LeftPair` and right-arm telemetry call it on their existing motor-owner threads. A shared reentrant lock makes puppet/preset reservations atomic. The pure tall-target function uses the actual elbow maximum and local WXAI DH dimensions; tests reproduce 0.853447555 m tool height. The modal has illustrated leader and follower cards in a collapsible section, a separate puppet row and a sticky Stop button. Offline checks: `agents/.scratchpad/presets_offline_test.py` (14 mocked tests plus geometry doctest) and `agents/.scratchpad/verify_presets.mjs` (isolated static fixture; every control POST intercepted). Build with the existing frontend npm script. No added dependencies.

## Leader copies of tall followers

Both leaders copied their matching follower six-joint poses on 2026-10-29; grippers stayed idle. Maximum endpoint joint error was below0.001rad. Tool heights were0.852276m left and0.852356m right, relative to each base. Both final states: seven idle modes, No error. Joint-coordinate copying does not establish world compass alignment when mount registration differs. Evidence: `agents/.scratchpad/leader_left-copy-motion/`, `agents/.scratchpad/leader_right-copy-motion/`, and `agents/.scratchpad/logs/leader-left-copy-20261029.log` / `leader-right-copy-20261029.log`.

## Standing leader-clearance assumption and reference photographs

The user states that the leader movement paths will basically always be clear: the leaders project outward into open room space. For the current installation, treat ordinary requested leader motions as cleared by the operator; do not repeatedly ask for clearance or require fixed-camera re-aiming merely because leaders are outside those camera views. Reassess if the installation changes or current evidence shows a person or obstacle entering the intended path. Retain factory joint limits, fault checks and exclusive motor ownership.

User-supplied photos were reviewed and copied without alteration:
- [Oblique rig view](reference-images/rig-oblique-leaders-outside-frame.jpeg): leaders project outside the front frame; raised followers are behind them.
- [Front clearance view](reference-images/rig-front-leader-clearance.jpeg): shows both leader mounts and surrounding open space.
- [Opposite oblique view](reference-images/rig-opposite-oblique.jpeg): confirms the rig arrangement from the other side.
- [Controller labels](reference-images/controller-role-ip-labels.jpeg): leader right192.168.1.2, follower right192.168.1.4, leader left192.168.1.3, follower left192.168.1.5.

Source filenames: IMG_2088.jpeg through IMG_2091.jpeg in that order. These photos document the installation before the leader copies, not the completed leader pose. Nearby frame members and cables remain part of the installation; the images are not a calibrated collision model.

## Four-arm preset accordion

Position presets live in a native collapsible details/summary section, initially collapsed, with explicit left/right follower and left/right leader up buttons. All four use the same tall-target computation, preserving base yaw/tool roll. Leader buttons raise the selected leader, rather than copying a possibly lowered follower. Existing per-arm SDK owners execute each request; the left pair routes the selected role through its guarded SDK method. Shared reservation excludes puppet and other presets, with unchanged heartbeat, cancellation, fault and idle confirmation rules. Validate role routing and shutdown with mocked drivers and intercept all browser control requests during UI tests; no physical motion is needed to implement this change.

## Absolute puppet update
User requests all six angles plus gripper, bounded catch-up, upright aligned engagement, and Up resets wrist yaw/roll to zero and opens grippers for all four roles. Preserve base heading. Use existing SDK owners and all-joint SDK methods documented in offline vendor teleoperation.py; gripper uses meters. Keep heartbeat, deadlines, factory faults and stop confirmation. No automatic engagement.

Absolute update verification: mocked seven-channel catch-up including delayed feedback and all upright/wrist/gripper/base rejection cases passed; fourteen preset tests, API regressions, build and intercepted browser tests passed. Per-tick follower-feedback anchoring prevents queued error from accumulating. Application target-step limits are0.5rad/s arm,0.02m/s gripper, capped by actual factory velocity bounds; remaining controller position/velocity/fault and heartbeat/deadline guards unchanged. Upright and base alignment tolerance0.06rad; open-gripper tolerance0.002m. Up preserves base yaw, sets wrist yaw and roll0, opens to actual factory maximum, and confirms all7idle on completion. Physically ran left leader/follower Up: grippers0.0400299/0.0400131m, wrist axes approximately0, no errors. Hardware hand-driven seven-axis follow trial awaits operator; never claim mock tests as that trial. Evidence agents/.scratchpad/absolute-up-result.json and logs/absolute-up-20261029.log.

User requests optional unlimited puppet sessions via animated monochrome stopwatch next to toggle. Keep heartbeat/Stop; expiry opt-out per engagement, resets next arm. User dislikes button lockouts: stationary precondition must be recoverable, never latch hardware fault or block Up. Observed live seven-axis copy passed: each axis moved, gripper excursion39.96mm leader/39.26mm follower; one settled sample max arm error0.000382rad, gripper0.0000133m.

Completed real operator-driven absolute copying observation: all six arm joints and gripper moved; no errors in30second sample. At1793324820.577269, all six errors≤0.000382rad (0.022deg), gripper error0.0000133m (0.0133mm). This is one settled sample, not continuous precision guarantee. Evidence agents/.scratchpad/absolute-observation.json. User subsequently hit moving-start error that incorrectly latched fault and disabled Up. Changed it to recoverable StartNotReady; mocked owner verifies ready/idle and rearm afterwards. No hardware fault bypass. Stopwatch widget web/source/frontend/src/widgets/Stopwatch/Stopwatch.svelte shows countdown and optional∞ via ordered unlimited action, resets each engagement, preserves heartbeat/Stop. Tests cover session expiry opt-out, heartbeat expiry, moving-start recovery, intercepted browser click and all14preset regressions. Restarted dashboard ready/noerror. User preference: avoid unnecessary button lockouts; prefer compact monochrome SVG controls.

Completion notification sent to phone topic rp and spoken shine_rut after chat, with human-readable-notification skill clarity review. Product/test commit e59c0b6. Server remains open; no automatic following enabled by assistant.

Right puppet requested: reuse identical seven-axis controller per side, one paired SDK owner each; remove separate right telemetry ownership. Side selection routes UI/API; shared preset lock excludes concurrent modes. Existing left endpoint defaults preserved.

Right puppet delivered: dashboard Arm pair selector routes left/right requests; right pair owns .2/.4 and publishes both telemetry streams, replacing independent right telemetry threads. Both sides share the seven-joint controller and stopwatch. Mock right-owner lifecycle, correct IPs, pair exclusion, API right dispatch, browser right selector/unlimited/Stop, left regressions and14preset tests passed. Both live pairs ready/noerror after restart. Right hand-driven copying has not been physically tested; left seven-axis trial remains valid.

Latest requested left Up: both completed through existing web preset owner, one eight-second trajectory each, wrist yaw/roll reset and grippers open (~0.04003/0.04001m). Heights0.853338/0.853364m; all7idle/noerror. Base headings preserved at approximately−0.2882/−0.2939rad. Fresh fixed-camera view checked before motion; standing leader clearance applies. Evidence agents/.scratchpad/logs/left-up-request-20261029.log. Spoken completion sent via shine_rut.

Robot control design: show separate illustrated Left and Right puppet cards at the same time, each with its own labelled switch and active stopwatch. Do not hide either behind a dropdown. Keep the four illustrated Up presets in the requested collapsible section. Only one mode may own movement; stop and heartbeat remain bound to the pair selected at start.

Both Position presets and Puppet mode use native collapsible sections with state chevrons; puppet starts expanded. Frontend edits use Vite development/HMR with API and camera WebSocket proxy to the existing hardware server; never restart hardware just for UI edits. When an activation is rejected, display the owner reason from current pair status instead of masking it with a subsequent heartbeat "not armed" error.

User requested all four arms upright again and completion speech "Yankee Doodle". Use existing HTTP preset owner sequentially, no server restart. Both puppet owners currently inactive with confirmed idle; fresh fixed view inspected and standing operator clearance applies to leaders.

Current request: allow simultaneous left/right puppet mode, and independent Up trajectories on all four arms with per-card progress. Retain one SDK owner per arm; reserve only overlapping arms (a puppet pair excludes Up on either member). Global Stop covers all locally owned channels, individual stops affect only their channel. Independent heartbeat, ordering, cancellation, and session timers. Keep all existing speed/fault guards. Stage frontend outside the running Vite source to avoid hot-reload interrupting operator motion; do not restart the hardware backend. Deployment requires a later idle handoff authorized by the user.

## Independent controls — staged, not deployed
Backend PresetGroup allocates one existing Presets state machine per arm under the shared lock. LeftPair reserves only its own side. Up on nonoverlapping arms and left/right puppet sessions can coexist; Up and puppet remain mutually exclusive for the same physical arm. All factory limits, speed checks, heartbeat deadlines, cancellation, and idle verification retained.

The new UI is staged at `agents/.scratchpad/independent-ui/frontend/src/Controls.svelte` and `agents/.scratchpad/independent-ui/frontend/src/style.css`. Do not copy these into the live Vite source during operator motion: HMR can dispose controls and trigger stop. Six immutable channel identities each have independent client token, sequence, cancellation generation, heartbeat and error state. Individual switches/Stop buttons cancel only their channel; global Stop/blur/close/pagehide stop all channels concurrently. Per-arm eight-second progress is elapsed trajectory time, not measured distance; the controller still verifies target arrival before releasing the arm. API snapshots expose `presets.arms[role]`.

Verified isolated frontend build and browser tests (all motor POSTs intercepted), four independent Up reservations, two concurrent actual owner loops with four mocked SDKs, independent stop/expiry, overlapping-arm rejection and cancellation during reads. Existing14 preset regressions, right lifecycle regressions and API guards pass. Actual simultaneous hardware motion has NOT been tested.

Deployment pending explicit idle handoff: user prohibited server restart. Backend process63401 still running since2026-10-29 21:57:26; observed left puppet active during final check. No controller restart or motor requests issued for this implementation. After user authorizes handoff, stop/verify all channels idle, stop/wait existing backend, copy both staged UI source files into web/source/frontend/src/, build, and start the sole backend owner; do not automatically enable motion. Vite remains127.0.0.1:43179 and backend28347. Check four live feeds and independent UI status after deployment.

Authorized handoff: user permits one restart after resetting all arms upright. Initial status found left owner already faulted on Missed control interval:0.115s, confirmed idle; left telemetry stale and presets unavailable. Right owner ready/idle. Stop old process and wait exit before standalone sequential Up using unchanged Presets state machine (speed/fault/heartbeat guards intact); verify upright before starting updated backend once. No concurrent SDK ownership or automatic fault clearing.

## Authorized deployment completed 2026-10-29 22:32
User authorized one restart after upright reset. Old backend63401 stopped and fully exited. Standalone handoff_up.py reused unchanged Presets speed/fault/heartbeat guards sequentially; all four reached tool-forward Z>0.99998 and height0.85336–0.85340m, wrists near zero, grippers about0.040m; every final mode idle/no controller error. No guard bypass. Evidence agents/.scratchpad/handoff-up-result.json and logs/handoff-up.log. Only then started updated backend44403 (22:32:28), one restart. Independent UI files copied into canonical frontend source and built. Browser uses Vite43179, proxying existing backend28347; no second restart. No automatic puppet activation.
