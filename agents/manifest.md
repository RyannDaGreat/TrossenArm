# Goal and verified result

Control the four network-connected Trossen arms from a portable project. The completed task is a right-follower gripper-only test at `192.168.1.4`: **12 small open–close cycles**, recorded on an Intel RealSense D405 and visually verified from decoded video frames. No arm-joint position commands were sent. All seven joints ended idle, with `No error` from the controller.

The test moves the gripper coordinate by **2 mm**, not through its full stroke. The selected arm follows the user's right-follower box label. Its moving gripper is at the upper-left edge of the full camera image, not the stationary foreground jaws.

- Original video: `agents/.scratchpad/gripper-motion-20261028-210146.mp4` — 1280×720, H.264/yuv420p, 30 fps, 2383 frames, 79.433 seconds.
- Replay copy: `agents/.scratchpad/right-gripper-12-cycles-zoom.mp4` — crop of the real upper-left 260×300 pixels, enlarged to 780×900; no synthesized motion. Revealed in Finder and confirmed as its selected file.
- Telemetry: `agents/.scratchpad/logs/gripper-twelve-cycles.log` contains 24 verified endpoints. Closed coordinate ≈12.966 mm; open coordinate ≈14.972–14.975 mm.
- Visual verification: decoded before/open/returned frames from the first and last cycles show the angled jaw moving away and returning. Evidence includes `agents/.scratchpad/motion-upper-left.png` and `agents/.scratchpad/last-{before,open,closed}.png`. Video quality is soft and travel intentionally small; the zoom makes it easier to replay.
- Speech and a separate `rp call ntfy_send` notification were sent only after visual verification and Finder reveal.

Do not repeat movement just because a monitoring check runs. Continue read-only babysitting until stopped. Keep implementation in `agents/.scratchpad/` until the user requests promotion.

# Glossary

- Dump: self-contained, movable Git project without dependencies on its absolute location.
- Leader/follower: operator-input arm / corresponding robot arm, according to the user's labels.
- SDK: vendor software interface for device discovery and control.
- UVC: standard USB camera interface used by the Mac camera backend.
- VLM: vision-language model; here, the assistant visually inspects decoded real video frames.
- Idle: vendor braking/control state, **not electrical power off**.
- Autopilot: make routine decisions without waiting indefinitely for input.
- Bulldog: persist in solving the requested problem without bypassing safety checks.
- Babysitting: remain active and monitor jobs/state until the user stops it, including after task completion.
- Glossary: definitions of project-specific vocabulary.

# User requirements

All human inputs are preserved in `agents/transcript.md`. Transcription removes clear dictation noise, stutters, and accidental repetition without changing meaning. Preserve meaningful qualifiers and contradictions; mark unclear words rather than inventing intent. Keep editorial notes separate.

- This is a portable dump. Everything built for experimentation stays in its scratchpad. Keep `AGENTS.md`, manifest, concerns, TODOs, and transcript current.
- The user made initial commit `9b25ae3` and allows further orthogonal commits: one coherent objective per commit. Never push unless requested.
- Root `pyproject.toml` and `uv.lock` are explicitly allowed. Python execution/dependency management uses **`uv run` only**, never any pip-install command.
- Do not give intermediate chat or speech. Speak only after the requested verified video exists, or at a genuine terminal blocker after attempts to resolve it. Console progress stays visible.
- Speech is one or two English sentences posted to `https://ntfy.sh/stark_comma`. Completion notification is separately `rp call ntfy_send --- 'message'`.
- Active modes: AUTOPILOT, BULLDOG, BABYSITTING, PONYTAIL. Monitor relevant capture/control processes and camera availability without repeating motion. Do not send repeated success audio.
- User visually checked the physical setup and authorized gripper movement. Camera inspection supplements, but does not replace, physical safety checks.
- Camera access must survive changed USB ports and computers, with macOS working now and Windows/Linux accommodated explicitly rather than claiming untested hardware support.

# Network and controllers

| User's arm label | Address | MAC address | Initial mean ping latency |
| --- | --- | --- | --- |
| Leader right | 192.168.1.2 | 04:e9:e5:1a:5f:78 | 1.858 ms |
| Follower right | 192.168.1.4 | 04:e9:e5:1a:5e:5f | 0.862 ms |
| Leader left | 192.168.1.3 | 04:e9:e5:18:11:da | 1.023 ms |
| Follower left | 192.168.1.5 | 04:e9:e5:1a:5e:8b | 1.187 ms |

All four initially returned 3/3 pings with 0% loss through USB Ethernet `en9`, at 1000baseT full duplex. Vendor discovery reports `wxai_v0`, firmware `1.8.4`, no errors. The Mac uses `192.168.1.100/24` with no router on `USB 10/100/1000 LAN`. Wi-Fi and VPN settings were not changed. These names describe this machine; rediscover interfaces on a new computer.

```sh
# Configure this Mac's robot network:
networksetup -setmanual 'USB 10/100/1000 LAN' 192.168.1.100 255.255.255.0
# Restore its previous DHCP setting when no longer needed:
networksetup -setdhcp 'USB 10/100/1000 LAN'
```

Evidence: `agents/.scratchpad/logs/connectivity.log`. Reachability does not establish physical identity or safe control readiness.

# Camera library

`agents/.scratchpad/robot_camera.py` provides `discover`, `select_camera`, `open_camera`, `read_rgb`, and `record_video`.

- Device: Intel RealSense D405, USB VID/PID `8086:0b5b`. Its USB connection is separate from the arms' Ethernet connection.
- macOS: enumerate current UVC devices with `cv2-enumerate-cameras`, match VID/PID, then use OpenCV with the discovered index. Never store a hardcoded camera index or port path. Actual 1280×720 RGB frames at 30 fps are verified.
- Windows/Linux: use the official RealSense SDK, identify the D405 by model, then enable its discovered serial. Adapter behavior is mock-tested; **real Windows/Linux hardware is untested**.
- Exactly one matching camera is required. Multiple matches raise an explicit ambiguity error. Persistent serial-to-role mapping for multiple cameras is not implemented. Never silently select a laptop camera.
- SDK failure is not hidden by runtime fallback. The Mac explicitly uses UVC because its SDK probe failed; details remain in concerns.
- Frames are `(H, W, C)` uint8 RGB, e.g. `(720, 1280, 3)` where C means red, green, blue. NumPy represents frames; Pillow saves images. `imageio-ffmpeg` supplies a portable H.264 encoder.
- `record_gripper.py` records concurrently. Camera-ready gating precedes robot configuration. Capture/encoder failures are surfaced; action checkpoints stop further commands after recording failure. A command already in progress may finish before the next checkpoint.

# Gripper control contract

`agents/.scratchpad/gripper_test.py` is offline by default and uses the matching `trossen-arm==1.8.8` driver. The successful final run did not clear errors.

1. Configure only `.4` with `wxai_v0_follower`. Require seven idle modes, finite telemetry, and `No error`. Abort rather than take over existing control.
2. Preserve arm-joint limits exactly. Gripper command effort is capped at **20 N**; its velocity bound is the original manufacturer **0.25 m/s**, with original feedback tolerances. These values are **not a certified contact-force or activation-speed guarantee**. The 20 N demo cited during development uses leader external-effort mode, not a follower safety rating.
3. Choose a 2 mm target interval within factory position bounds, approximately `[0, 0.04]` m. Feedback may start outside nominal bounds only within both actual factory tolerance and 1 mm. Do not change calibration offsets or widen factory position limits.
4. Enable only gripper position mode and verify six arm modes remain idle. Verify position mode immediately before the first target and during feedback checks.
5. Move with 3-second rest-to-rest trajectories. Ideal quintic peak speed for 2 mm is 1.25 mm/s, but activation/tracking transients can be faster. Do not confuse trajectory speed with the velocity bound.
6. Require each endpoint within 1 mm of target and each cycle half to move at least 1 mm in the requested direction. Check arm feedback drift against 0.005 rad; stop on controller errors, invalid feedback, unexpected modes, or insufficient travel. Never auto-increase force.
7. Finally return the gripper to idle and clean up the driver. Reduced effort remains 20 N; original velocity bound remains 0.25 m/s. Manufacturer limits persist across reconnects but reset on reboot. Re-read and verify before future activation.

Faults can themselves brake arm joints and close the gripper. Driver cleanup/destruction changes modes; idle is not electrical power-off. Never catch a driver daemon failure and continue using cached feedback. Known development faults and the explicit one-cycle recovery are in concerns. Do not reuse the recovery environment flag for an unidentified fault.

# Files and reproducibility

- `AGENTS.md`: scoped instructions and safety boundary.
- `agents/todo.md`: current checklist; `agents/transcript.md`: human inputs.
- `agents/manifest.md`: current design/results; `agents/concerns.md`: append-only history, failed attempts, and lessons.
- `pyproject.toml`, `uv.lock`: Python 3.12 and pinned dependencies. Robot driver is an optional `robot` extra so camera-only Windows use is not blocked by absent robot-driver wheels.
- `.gitignore`: environments, runtime/cache downloads, vendor checkout, bytecode, logs, and generated camera media.
- `agents/.scratchpad/scratchpad.py`: offline driver API check.
- `agents/.scratchpad/robot_camera.py`, `camera_check.py`, `camera_offline_test.py`: library, actual Mac frame check, and platform-adapter mock tests.
- `agents/.scratchpad/gripper_test.py`, `record_gripper.py`: guarded motion and concurrent recording.
- `agents/.scratchpad/gripper_readback.py`: controller configuration/telemetry diagnostics; it configures and cleans up the driver, so it is not a side-effect-free network query.
- `agents/.scratchpad/uvc_probe.py`: camera profile experiment.
- `agents/.scratchpad/inspect_motion.py`, `motion_difference.py`: actual-frame crops and diagnostic image differences, not synthetic motion.

Run from the Git root. Keep generated environments inside the dump and recreate them after moving it.

```sh
export UV_CACHE_DIR=agents/.scratchpad/uv-cache
export UV_PYTHON_INSTALL_DIR=agents/.scratchpad/uv-python
uv run --locked agents/.scratchpad/camera_offline_test.py
uv run --locked agents/.scratchpad/camera_check.py
uv run --extra robot --locked agents/.scratchpad/scratchpad.py
uv run --extra robot --locked agents/.scratchpad/gripper_test.py
# Capture-only encoder check, no robot commands:
uv run --locked agents/.scratchpad/record_gripper.py
```

A deliberate `TROSSEN_GRIPPER_LIVE=1` runs actual recorded motion through `record_gripper.py`; do not set it for routine monitoring or offline tests. Recheck physical clearance before any later live test.

# Official documentation

Repository: https://github.com/TrossenRobotics/trossen_arm . Local ignored checkout `agents/.scratchpad/trossen_arm`, tag `v1.8.8`, revision `084ef0a74d3e6b71d640ac9907e4b48e04efcdcf`. Recreate if absent:

```sh
git clone --depth 1 --branch v1.8.8 https://github.com/TrossenRobotics/trossen_arm.git agents/.scratchpad/trossen_arm
```

- Versioned docs: https://docs.trossenrobotics.com/trossen_arm/v1.8/
- Camera configuration: https://docs.trossenrobotics.com/trossen_arm/v1.9/tutorials/lerobot_plugin/configuration.html
- In the checkout: `docs/getting_started/configuration.rst` explains command clipping, feedback limits, and persistent settings; `docs/troubleshooting.rst` explains faults and recovery; `include/libtrossen_arm/trossen_arm.hpp` defines API contracts and daemon failure behavior.
- Driver and controller must share minor version. Core driver implementation is a precompiled binary; do not claim its internals were verified. Never upgrade firmware just to match a newer Python package.

# Verification and limits

Offline tests cover target bounds, bounded initial offset, 12-cycle flow, rejected idle-mode activation, gripper-only limit restoration, failed-motion abort, and preservation of motion plus cleanup errors. Camera tests cover unambiguous selection and mocked Windows/Linux SDK lifecycle. Hardware verification covers this Mac, one D405, and the labeled right follower only. Neither the other three grippers nor full-stroke motion has been tested.

Use concise, documented functions, visible failures, and no silent fallback. Document tensor/image shapes. All stored project paths must be relative to the Git root. Do not create separate project-notes files; current knowledge belongs here and historical reasoning belongs in concerns.

# Semantic Bindings

None.
