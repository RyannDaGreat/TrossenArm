# TODO

## Environment and Git cleanup

- [x] Move `pyproject.toml` and `uv.lock` to the root; verify the `uv run` environment.
- [x] Merge the separate notes into the manifest and remove the redundant file.
- [x] Ignore generated caches/vendor downloads and commit intentional work by objective.

## Right gripper test

- [x] Download and read official safety and control documentation and public driver headers.
- [ ] Resolve safe initialization and shutdown: documented destructor changes modes, and runtime faults can close the gripper; core implementation is a binary.
- [ ] Await physical confirmation: right follower `.4`, stock gripper, arm mounted securely, gripper empty/clear, operator able to stop power. Then establish safe gripper-only control.
- [ ] Implement and test a limited-motion script offline before hardware use.
- [ ] With safety checks satisfied, warn before physical actions and verify 12 open–close cycles.
- [ ] Record results and make orthogonal commits.

- [x] Apply near-verbatim transcript rules and clean existing dictation artifacts without changing meaning.

- [x] Initialize this dump as a Git repository and add local instructions.
- [x] Keep the user transcript and project manifest.
- [x] Set up the USB Ethernet link for the robot subnet without changing Wi-Fi or VPN settings.
- [x] Verify connectivity to all four labeled IP addresses without moving the arms.
- [x] Record results and report which arms are reachable.

All four addresses responded: 3/3 pings each, 0% packet loss. Details are in `agents/manifest.md`; raw evidence is in `agents/.scratchpad/logs/connectivity.log`. Robot control is not tested. No intermediate progress chatter; speech warnings are required before physical actions.
