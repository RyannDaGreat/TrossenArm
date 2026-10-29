# TODO — laptop shutdown checkpoint

## Shutdown

- [x] Stop the web server, all camera/robot owners, and monitoring jobs; verify port 28347 has no listener.
- [x] Record current state, failures, and remaining work. No delegates remain running.
- [x] Final controller/API/FK offline checks passed; save source, motion experiments, and shutdown documentation as separate commits and verify the working tree.
- [ ] On the next session, reconnect and inspect hardware before explicitly starting the server. Never auto-enable following.

## Next priority: reliable left-pair puppeteering

- [x] Research vendor support and preserve one SDK owner for leader-left `.3` and follower-left `.5`.
- [x] Add themed control modal, workspace acknowledgement, hands-free on/off toggle, heartbeat/session guards, and Stop button.
- [x] Fix stop/rearm races, late-write checks, failed-driver reuse, peer stop ordering, and uncertain-stop reporting; pass mocked regressions and API tests.
- [x] Replace unexplained range faults with per-joint clamping and exact boundary diagnostics; retain factory limits.
- [x] Observe real user-driven follower movement, then a measured-velocity guard stop. Both left arms ended idle.
- [ ] Live-test the final 60 ms interpolated-target change and numeric speed diagnostics. This adjustment is NOT yet physically verified; do not widen the guard just to force completion.
- [ ] Complete a reliable supervised puppeteering trial and report actual outcome. Grippers remain unlinked in the current arm-only implementation.

## Delivered

- [x] Portable Git dump, root pyproject/lock, uv-run-only environment, ignored caches/media/logs/generated builds.
- [x] Reach all four robots; current nested-adapter Ethernet is AX88179A/en11, 192.168.1.100/24.
- [x] Discover all four D405 cameras, inspect views, display montage, and provide a portable camera library.
- [x] Record and visually verify 12 small gripper cycles, reveal replay, speak and notify.
- [x] Record four full gripper cycles for about one minute; verify all telemetry endpoints and idle/no-error finish.
- [x] Raise right follower through four visually checked stages; verify sky-facing gripper and final idle state.
- [x] Build exact `web/run-the-server.sh` + `web/source/` layout, four live feeds near 30 fps each, and real joint/FK geometry for all arms.
- [x] Test dashboard and control UI with Puppeteer; open viewer and send speech plus phone notifications.
- [x] Complete read-only camera performance, scene inventory, kinematics, leader, teleoperation, model-asset, and controller-safety investigations.

## Remaining requested work

- [ ] Final VLM/Finder replay delivery for the separate full-stroke video `gripper-full-stroke-20261028-212658.mp4`.
- [ ] Verified 90°/L-shaped leaders: left reached only ~22.5° before a clearance pause; right has an out-of-configured-bound wrist reading. Do not claim completion or activate right leader blindly.
- [ ] Optional actual robot-model rendering and wireframe/model toggle. Official asset research is complete; rendering is not implemented.
- [ ] Calibrated environment mapping or safe 360° scan. Only a static four-view inventory exists; no blind arm sweep.
- [ ] Long-duration streaming soak and real Windows/Linux camera verification.
