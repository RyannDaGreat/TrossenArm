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
- [x] Complete real user-driven seven-joint copying; see absolute-observation.json and current manifest results.

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
- [x] Leader L-pose request superseded by completed tall follower-pose copies on both leaders.
- [ ] Optional actual robot-model rendering and wireframe/model toggle. Official asset research is complete; rendering is not implemented.
- [ ] Calibrated environment mapping or safe 360° scan. Only a static four-view inventory exists; no blind arm sweep.
- [ ] Long-duration streaming soak and real Windows/Linux camera verification.

## Current request — leader pose copies
- [x] Read current leader/follower joints and validate follower targets against leader nominal limits.
- [x] User explicitly confirmed leader movement paths clear and instructed motion; existing cameras do not show leaders.
- [x] Verify actual leader feedback tolerances, copy each follower pose with single control owner, and verify final idle/no error.
- [x] Save four operator reference photographs and standing leader-clearance assumption in the manifest.
- [x] Restore dashboard and report completion.
- [x] Restore/open dashboard after leader copies; verify four live cameras and four idle arms.

## Four-arm preset controls
- [x] Add leader-up controls using existing SDK owners.
- [x] Put all position presets in a collapsed accordion; verify browser and owner routing offline.

- [x] Absolute seven-joint following, upright alignment gate, normalized/open Up, offline and live verification.
- [x] Optional stopwatch unlimited mode and recoverable moving-start rejection; dashboard restarted ready.
- [x] Send final phone/audio completion.

- [x] Implement right-pair puppeteering, side selector, shared seven-joint/timer behavior; verify mocked owner/API/browser and real connections.
- [ ] Operator-driven right-pair copying trial (software and connections verified; no automatic following).

- [x] Replace puppet dropdown with two visible illustrated cards; verified both routes, stopwatch, stopping and mobile layout.
- [x] State chevrons on both sections; puppet initially expanded.
- [ ] Show actual right-pair engagement rejection instead of the secondary heartbeat error; verify via intercepted browser requests.
- [x] Vite43179 serves frontend and proxies cameras/API to backend28347.
- [x] Independent puppet pairs and per-arm Up controllers; concurrent mocked owner tests passed.
- [x] Independent UI sessions and per-arm progress; isolated browser validation passed; source staged outside live Vite tree.
- [x] User authorized one restart after upright reset; all four reset/verified, updated controller and canonical UI deployed.

- [ ] Restart server after operator power-cycled right arms; verify fresh connections without motion.
- [ ] Establish vendor and intended resting poses before implementing illustrated Rest controls; background investigation active.
- [x] Power-cycle recovery restart complete: PID62919, all four arms fresh/idle/noerror, four cameras fresh. Rest-pose definition remains under investigation.
- [x] Fix Up targets to align each pair's base encoder angles; fourteen preset tests and concurrent owner regressions passed.
- [ ] Deploy base-aligned Up after backend restart authorization; verify fresh ready state without automatic motion.

- [x] Execute updated Up on all four arms; verify idle/noerror and record operator confirmation that all four face north.
