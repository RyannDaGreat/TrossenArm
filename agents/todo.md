# TODO

## Active monitoring

- [ ] Continue read-only babysitting until the user stops it. No capture/control job remains running after the successful test. Do not repeat motion or success notifications.

## Environment and Git cleanup

- [x] Move `pyproject.toml` and `uv.lock` to the root; verify the `uv run` environment.
- [x] Merge the separate notes into the manifest and remove the redundant file.
- [x] Ignore generated caches/vendor downloads and commit intentional work by objective.

## Camera

- [x] Identify and connect the Intel RealSense D405 after the USB hub was plugged in.
- [x] Implement model/USB-identity discovery on Mac and serial discovery on Windows/Linux; no saved port or OS index. Multiple matches fail explicitly.
- [x] Verify Mac RGB capture and recording; Windows/Linux adapter tests pass with mocks, real hardware remains untested.
- [x] Record 12 actual open–close cycles; verify the moving upper-left gripper through VLM inspection of decoded frames.
- [x] Reveal `agents/.scratchpad/right-gripper-12-cycles-zoom.mp4` in Finder and confirm selection; speak and notify after verification.

## Right gripper test

- [x] Download and read official safety and control documentation and public driver headers.
- [x] Verify the test starts and ends with all joints idle. Document that faults can close the gripper and idle is not electrical power-off; binary internals remain unverified.
- [x] User reports a visual safety check and authorizes proceeding.
- [x] Test gripper-only position control on `.4` with 2 mm travel, 3-second moves, 20 N effort cap, and original manufacturer velocity bound.
- [x] Pass offline tests: bounds/offsets, cycles, mode guards, gripper-only limit restoration, abort, and combined cleanup failures.
- [x] Verify all 12 recorded cycles through 24 telemetry endpoints; final controller state is idle with no errors.
- [ ] Record results and make orthogonal commits.

- [x] Apply near-verbatim transcript rules and clean existing dictation artifacts without changing meaning.

- [x] Initialize this dump as a Git repository and add local instructions.
- [x] Keep the user transcript and project manifest.
- [x] Set up the USB Ethernet link for the robot subnet without changing Wi-Fi or VPN settings.
- [x] Verify connectivity to all four labeled IP addresses without moving the arms.
- [x] Record results and report which arms are reachable.

All four addresses responded: 3/3 pings each, 0% packet loss. Details are in `agents/manifest.md`; raw evidence is in `agents/.scratchpad/logs/connectivity.log`. The final 12-cycle video is verified and delivered. Earlier failed attempts remain recorded in `agents/concerns.md`. No further movement is scheduled.
