# TODO

## Environment and Git cleanup

- [x] Move `pyproject.toml` and `uv.lock` to the root; verify the `uv run` environment.
- [x] Merge the separate notes into the manifest and remove the redundant file.
- [x] Ignore generated caches/vendor downloads and commit intentional work by objective.

## Camera

- [x] Camera investigator `del_mvssdd85_7gvy` finished: only built-in Mac camera and Desk View available.
- [x] Capture and visually inspect frames: gripper jaws are not visible.
- [ ] Obtain a usable camera view: robot camera USB hub must be connected, or available camera aimed at the gripper.
- [ ] Record actual opening and closing and verify the video through VLM.
- [ ] Reveal the verified video in Finder; only then speak and notify.

## Right gripper test

- [x] Download and read official safety and control documentation and public driver headers.
- [ ] Resolve safe initialization and shutdown: documented destructor changes modes, and runtime faults can close the gripper; core implementation is a binary.
- [x] User reports a visual safety check and authorizes proceeding.
- [ ] Establish safe gripper-only control on right follower `.4`.
- [x] Verify the revised limited-motion script offline: bounded initial offset, invalid bounds, 12 mocked cycles, failed-motion abort, and cleanup. No live motion verified.
- [ ] With usable video capture running, verify gripper opening and closing; original 12 cycles remain pending.
- [ ] Record results and make orthogonal commits.

- [x] Apply near-verbatim transcript rules and clean existing dictation artifacts without changing meaning.

- [x] Initialize this dump as a Git repository and add local instructions.
- [x] Keep the user transcript and project manifest.
- [x] Set up the USB Ethernet link for the robot subnet without changing Wi-Fi or VPN settings.
- [x] Verify connectivity to all four labeled IP addresses without moving the arms.
- [x] Record results and report which arms are reachable.

All four addresses responded: 3/3 pings each, 0% packet loss. Details are in `agents/manifest.md`; raw evidence is in `agents/.scratchpad/logs/connectivity.log`. First driver connection succeeded but aborted before position mode/targets. All joints ended idle. No verified motion or video yet. No speech or completion notifications until VLM verifies the requested video.
