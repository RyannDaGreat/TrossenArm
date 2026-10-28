# Trossen robot arms

Read `agents/todo.md` and, if present, `agents/manifest.md` and `agents/concerns.md` before planning or changing files.

This is a portable dump. Use paths relative to the Git root. Keep experiments, downloaded tools, and test results in `agents/.scratchpad/`; keep logs in `agents/.scratchpad/logs/`.

Current scope: read official documentation and prepare a safe right-follower gripper-only test (12 open–close cycles). Verify safety before enabling the gripper. Do not move arm joints or change their torque/control modes. Do not run vendor motion demos blindly. Follow the manifest's safety and speech requirements.

Python: use `uv run` only. Never use `pip install`, `uv pip install`, or another pip installation command. Declare dependencies in environment files or PEP 723 script metadata. Keep generated environments and caches inside this dump, ignored by Git and reproducible.

Box labels supplied by the user:
- Leader right: `192.168.1.2`
- Follower right: `192.168.1.4`
- Leader left: `192.168.1.3`
- Follower left: `192.168.1.5`
