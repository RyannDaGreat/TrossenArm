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
