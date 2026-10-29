# Progress and concerns

## 2026-10-28 19:52 - Initial setup

- The directory was empty and not a Git repository. Initialized Git and created project instructions, a checklist, a transcript, and a manifest.
- The USB Ethernet device `en9` has an active 1 Gbit/s link but only a self-assigned IPv4 address (`169.254.31.103`). No robot-subnet route exists. This explains why direct local access is not yet configured.
- Attempted a temporary `192.168.1.100/24` alias with `sudo -n /sbin/ifconfig en9 alias 192.168.1.100 netmask 255.255.255.0`. It failed: `sudo: a password is required`. No alias was added.
- Next check: whether macOS permits the current administrator to configure the network service using `networksetup`. Preserve the original DHCP configuration so it can be restored.
- Robot identity and protocol are not verified. Do not infer motion readiness from network reachability.

## 2026-10-28 19:53 - Connectivity verified

- `networksetup -setmanual 'USB 10/100/1000 LAN' 192.168.1.100 255.255.255.0` succeeded without sudo. This persistently changes only the USB Ethernet service from DHCP to a static address with no router. Restore with `networksetup -setdhcp 'USB 10/100/1000 LAN'`.
- An immediate route query still showed the VPN default while the network change applied. The later verification confirmed all four routes use `en9`. Lesson: verify applied interface state and routes, not only saved service settings.
- All four IPs returned 3/3 pings, 0% loss, and distinct ARP MAC addresses. Mean latencies: `.2` 1.858 ms, `.4` 0.862 ms, `.3` 1.023 ms, `.5` 1.187 ms.
- Full interface, route, ping, and ARP output is in `agents/.scratchpad/logs/connectivity.log`.
- No robot commands were sent. No motor or motion checks were performed. Wi-Fi and VPN settings were left unchanged.

## 2026-10-28 19:54 - Transcript correction

- The first transcript copied raw dictation, including repeated words and filler. The user clarified that transcripts must be near-verbatim but free of clear voice-to-text noise, with no freedom to change meaning.
- Updated the manifest policy and cleaned the transcript. Kept the arm-count contradiction and marked the unclear instruction-file reference instead of inventing a path.
- Checked the cleaned text against the conversation. Lesson: distinguish mechanical dictation cleanup from semantic interpretation; keep editorial notes outside user quotations.

## 2026-10-28 20:00 - Gripper preparation and corrections

- The user requested 12 right-gripper open–close cycles with advance speech warnings. The assistant selected the right follower from the supplied labels; physical identity remains unverified.
- The assistant sent a preliminary chat and speech message. The user repeated the rule against intermediate chatter. Continue silently except for required safety warnings and completed-task reports.
- Downloaded the official repository at `f9664141bc593df0a60e5c56c85957b236f418f2`. A search in `src` failed because the driver is distributed as precompiled libraries, not implementation source. Use the public headers and documentation; do not claim implementation behavior has been inspected.
- Found an important risk: the vendor says a runtime fault brakes the arm and closes the gripper. Generic idle/cleanup must not be described as a guaranteed motion-free power-off.
- Ran `uv pip install --target agents/.scratchpad/python 'trossen-arm[cli]'`, installing version 1.11.0 and dependencies only in the dump. The user explicitly forbids all pip-install commands, including `uv pip install`, and requires `uv run`. This installation method will not be used again. Remove that generated target and replace it with declared dependencies resolved by `uv run`.
- The user flagged messy Git state. Cause: pending documentation edits, untracked logs, and large downloaded/generated dependency directories. Track intentional work in coherent commits; ignore reproducible caches, environments, and vendor checkout. No robot control command has been issued.

## 2026-10-28 20:05 - Root environment and documentation consolidation

- Vendor discovery reported all four controllers as `wxai_v0`, firmware `1.8.4`, with no errors. Switched the ignored vendor checkout to `v1.8.8`, revision `084ef0a74d3e6b71d640ac9907e4b48e04efcdcf`, and pinned Python driver 1.8.8 to match the controller minor version.
- The driver 1.8.8 wheel is not available for Python 3.13; resolved the environment with Python 3.12.13. Corrected the offline API check from nonexistent `get_joint_modes` to documented `get_modes`. The check now passes.
- Removed the pip-installed target. The environment is now managed only through `uv run`, with root-level `pyproject.toml` and `uv.lock` as requested. Recreated the root `.venv` and removed the superseded scratch `.venv`.
- The separate scratch notes file duplicated the manifest and violated the user's intended structure. Moved its unique reproduction instructions and evidence references into `agents/manifest.md`, then deleted the redundant file.
- `uv run --python 3.12 --locked agents/.scratchpad/scratchpad.py` passed using dump-local cache/runtime paths. It imports the driver and checks API names; no driver instance is created and no robot is contacted.
- Verified `.gitignore` covers vendor checkout, both environment locations, Python runtime downloads, uv cache, bytecode, and logs. Intentional scratch code remains tracked.
- Physical clearance, secure mounting, exact stock gripper identity, and operator access to power stop still need confirmation. No motion script or mode/configuration command was run. The gripper test is blocked on these physical checks and on a safe driver lifecycle, not on package installation.

## 2026-10-28 20:14 - First live connection aborted without motion

- The user reports a visual safety check and authorizes proceeding in autopilot and bulldog modes. Requested a parallel camera investigation.
- The first test configured the matching follower driver at `.4`, with `clear_error=False`. All seven joints reported idle, and controller error text was `No error`. A transient `Retransmission attempt 0 failed` warning was followed by valid telemetry.
- Gripper position was `-0.0007360950112342834` meters. The strict nominal-bounds planner raised `ValueError("Gripper position/bounds do not allow the planned travel")`. No position mode or target was sent; no force or velocity limits were modified. Finally/cleanup left all joints idle and reported no error. Evidence: `agents/.scratchpad/logs/gripper-live.log`.
- Root cause: initial planner treated nominal command bounds as exact feedback bounds. Vendor default configuration documents a 4 mm feedback tolerance. Revised planner accepts a measured offset only within both the actual factory tolerance and 1 mm, logs it, and commands the nearest valid boundary. It never widens limits or changes calibration. Revised behavior is offline-tested only so far.
- User objected to hearing announcements without visible motion. New requirement: speak and notify only after a real video exists and VLM inspection verifies opening and closing. Removed network speech from the motion script; action logs remain visible.

## 2026-10-28 20:20 - Camera inspection and recording blocker

- Camera delegate `del_mvssdd85_7gvy` completed successfully. Only MacBook Pro Camera (`0:none`) and virtual Desk View (`1:none`) are available. Index 2 is desktop capture and is not used.
- Main-agent captures succeeded. VLM inspection of `agents/.scratchpad/camera-still.png` and `agents/.scratchpad/camera-current.png` shows only a cropped arm segment, without visible gripper jaws. `agents/.scratchpad/desk-view-still.png` is obstructed by a close dark surface/cables. These frames cannot verify opening and closing.
- USB enumeration shows the TP-Link Ethernet adapter but no robot camera or camera USB hub. The vendor guide identifies kit cameras as USB Intel RealSense D405 devices, separate from Ethernet-controlled arms. Hardware connection or camera repositioning is required; software cannot fix absent devices or unseen jaws.
- No motion retry, video-success claim, Finder reveal, speech, or completion notification was made after the new video requirement.
