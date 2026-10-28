# TODO

## Environment and Git cleanup

- [ ] Replace the pip-installed scratch environment with `uv run` and declared dependencies.
- [ ] Ignore generated caches/vendor downloads and commit intentional work by objective.

## Right gripper test

- [x] Download and read official safety and control documentation and public driver headers.
- [ ] Verify initialization and shutdown behavior; core driver implementation is distributed as a binary.
- [ ] Establish the exact target, safe gripper-only control, and required physical safety checks.
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
