# Goal and current state

Control and observe four Trossen WXAI arms from this portable Git project. Keep robot identity, hardware ownership, current geometry, and measured camera performance explicit. Never infer collision clearance or metric room coordinates from uncalibrated camera images.

**Shutdown checkpoint:** the user is turning off the laptop. The server and all camera/robot jobs have been stopped; do not automatically resume motion or following next session. Start the viewer explicitly with `web/run-the-server.sh` at http://127.0.0.1:28347 after reconnecting and checking current hardware. It owns four cameras, two right-arm read-only drivers, and one left-pair telemetry/control owner. Never issue competing driver commands.

**Verified:** four live camera feeds, live encoder-driven geometry for all four arms, right-follower small/full gripper cycles, and a staged sky-facing right-follower pose. The dashboard was tested with Puppeteer, visually inspected, opened in the browser, and announced through both channels. A 20-second browser test measured approximately 30 drawn frames/second for each camera; exact results are in `agents/.scratchpad/web-verification.json`. This is not a long-duration soak or exposure-to-screen latency certification.

**Pending:** left-pair puppeteering is implemented and the user's physical trial moved the follower, but it stopped on the software measured-velocity guard; this is not yet a reliable completed trial. The final 60 ms target-interpolation adjustment and detailed speed diagnostics are offline-tested only, not live-tested. Do not restart it automatically. Powered leaders reaching a verified 90-degree/L pose remain incomplete. A static four-view environment inventory exists; no 360-degree arm sweep or calibrated room map exists. Full-stroke video replay still needs its own final VLM/Finder delivery check.

# Glossary

- Dump: self-contained, movable Git project, with no dependency on its absolute location.
- Leader: finger-handle arm used as operator input. Follower: corresponding output arm.
- SDK: vendor device-control interface. UVC: standard USB camera interface.
- VLM: the assistant's visual inspection of real captured images/video frames.
- Idle: vendor braking state, not electrical power off or guaranteed exact position hold.
- FK: forward kinematics; joint angles transformed into link/tool geometry.
- DH: Denavit–Hartenberg convention used by the manufacturer's geometry table.
- Base frame: one robot's local coordinate system. World registration: calibrated placement of different bases/cameras in one coordinate system; not implemented.
- Relative teleoperation: preserve the starting follower pose and mirror changes in leader joints rather than immediately copying unmatched absolute angles.
- Deadman: a control that must stay actively held/refreshed; releasing it or losing heartbeat stops powered following.
- Autopilot: make routine decisions without unnecessary blocking. Bulldog: persist without bypassing safety. Babysitting: monitor ongoing work until stopped. Ponytail: smallest complete, checked implementation.
- Glossary: definitions of project-specific terms.

# Requirements and workflow

All actual human inputs belong in `agents/transcript.md`, near-verbatim with obvious dictation artifacts/stutters removed, no semantic reinterpretation, and unclear words marked. Keep editorial notes outside quotations. The transcript is the record of user ideas; this manifest also includes explicitly identified implementation decisions.

- Portable dump. One scoped instruction file, `AGENTS.md`; current work in `agents/todo.md`; current design here; append-only mistakes/results in `agents/concerns.md`. No redundant notes file.
- Experiments and evidence stay under `agents/.scratchpad/`. The user explicitly requested promotion of the web app into `web/`.
- Root `pyproject.toml` and `uv.lock`; **Python and dependencies through `uv run` only. Never any pip-install command.** Keep generated environments/caches inside the dump, ignored and recreated after moving it.
- Orthogonal commits using `[P]` prefix; no push unless requested. User made initial commit `9b25ae3`.
- Active modes: AUTOPILOT, BULLDOG, BABYSITTING, PONYTAIL. Do not repeat physical actions merely because a monitoring timer fires.
- No unnecessary intermediate speech. Answer direct status questions. Report verified outcomes and genuine terminal blockers, not setup milestones as completed tasks.
- Speak in brief English through `https://ntfy.sh/stark_comma`; every spoken message also gets the same phone update through `rp call ntfy_send --- 'message'`. Use `uv run --extra robot --with rp --with requests rp call ...` so RP cannot prompt for pip installation. Keep command output visible. Song requests use public-domain or original material, not unprovided copyrighted song lyrics.
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

Current nested-adapter setup: AX88179A network service on `en11`, manual `192.168.1.100/24`, no router. Wi-Fi and VPN remain unchanged. The earlier TP-Link `en9` connection is historical evidence in `agents/.scratchpad/logs/connectivity.log`; do not reuse its service name blindly. Discover service/interface identity before configuring a new host. The current right-follower route/ping check succeeded after `networksetup -setmanual AX88179A 192.168.1.100 255.255.255.0`.

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
- Arm owners configure the correct leader/follower preset, never clear errors, and publish joints/modes/tool geometry at 20 Hz. FK XYZ must agree with controller XYZ within 5 mm. Geometry layout is **schematic in four separate base frames**, not a measured room arrangement. Idle/braked status is visible. A same-origin, loopback-only `/api/puppet` endpoint queues intent to the single left-pair owner; HTTP handlers never call the SDK. Right-arm telemetry remains read-only.
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

Right leader `.2` wrist yaw read approximately −1.8553 rad, outside its reported −π/2 bound. **Do not activate it or widen bounds.** Left leader `.3` completed one observed quarter-stage, shoulder/elbow about 22.5°; returned idle/no error. Stopped before completing the 90° goal because current camera views did not establish clearance of the leader-handle trajectory. The central white tabletop gripper assemblies must not be assumed to be leader arm bases. No 90° success notification was sent. Human hands must leave handles before powered position moves; gravity-compensated teaching is different and must be explicitly enabled under operator control.

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
