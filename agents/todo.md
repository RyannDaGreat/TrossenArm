# TODO — current session

- [x] Replace bent poses with model-derived maximum upward reach within unchanged limits; both reached approximately 0.85345 m.
- [x] Complete left staged and right continuous eight-second lift, verify final idle/no error, restore dashboard.
- [x] Identify duck-based cardinal directions: north=wall/top of fixed image; east=right; south=camera/front; west=left.
- [x] Align both bases approximately north using stock camera geometry and north wall; zero both tool rolls. Both continuous turns completed, wrist images level, final idle/no error.
- [x] Integrate illustrated left/right arm-up presets and offline tests.
- [x] Restore updated browser and verify four live feeds at 29.996–30.096 drawn fps. UI motion path is offline-tested, not physically validated.

- [x] Make local vendor documentation and learned hardware-limit facts easy to find offline: manifest now has a near-top source index and verified command-bound/feedback-tolerance distinction.

- [x] Discover and verify all four cameras on the new computer: about 30 fps each, fresh images inspected.
- [x] Restore robot connectivity, start the web UI, verify it, and open the browser. Restarted after stages as the sole hardware owner; following disabled.
- [x] Record small gripper motion after checking the current views: two verified 2 mm cycles, wrist/top MP4s, all joints idle/no error afterward.
- [x] Raise right follower through four visually checked stages; skyward tool at 0.7113 m, final idle/no error.
- [x] Raise left follower at 8/3 seconds per stage (three times faster trajectory timing); all four stages verified, skyward tool at 0.7151 m, final idle/no error. Factory limits unchanged.
- [x] Verify recordings and right-follower pose; send Marvin's Yankee Doodle message via shine_rut (server accepted). Second arm explicitly reported as still idle.

# Previous laptop shutdown checkpoint

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
- [x] Reach all four robots; current Ethernet is AX88179A/en8, 192.168.1.100/24.
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
