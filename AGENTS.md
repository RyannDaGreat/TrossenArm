# Trossen robot arms

Read `agents/todo.md` and, if present, `agents/manifest.md` and `agents/concerns.md` before planning or changing files.

This is a portable dump. Use paths relative to the Git root. Keep experiments, downloaded tools, and test results in `agents/.scratchpad/`; keep logs in `agents/.scratchpad/logs/`.

Current scope: establish network connectivity only. Do not enable motors, change torque or control modes, or command movement.

Box labels supplied by the user:
- Leader right: `192.168.1.2`
- Follower right: `192.168.1.4`
- Leader left: `192.168.1.3`
- Follower left: `192.168.1.5`
