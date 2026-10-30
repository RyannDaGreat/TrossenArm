"""Query and record right-pair readiness without motor writes."""
import json,urllib.request
from pathlib import Path
with urllib.request.urlopen('http://127.0.0.1:28347/api/status') as r:s=json.load(r)
for key in ('puppet','puppet_right'):
    print(key,s[key])
    assert s[key]['mode']=='ready' and not s[key]['error']
for role in ('leader_right','follower_right'):
    assert s['arms'][role]['ready']
    print(role,s['arms'][role]['modes'])
with Path('agents/manifest.md').open('a') as f:f.write('\nRight puppet delivered: dashboard Arm pair selector routes left/right requests; right pair owns .2/.4 and publishes both telemetry streams, replacing independent right telemetry threads. Both sides share the seven-joint controller and stopwatch. Mock right-owner lifecycle, correct IPs, pair exclusion, API right dispatch, browser right selector/unlimited/Stop, left regressions and14preset tests passed. Both live pairs ready/noerror after restart. Right hand-driven copying has not been physically tested; left seven-axis trial remains valid.\n')
with Path('agents/todo.md').open('a') as f:f.write('\n- [x] Implement right-pair puppeteering, side selector, shared seven-joint/timer behavior; verify mocked owner/API/browser and real connections.\n- [ ] Operator-driven right-pair copying trial (software and connections verified; no automatic following).\n')
with Path('agents/concerns.md').open('a') as f:f.write('\nRight-pair ownership migration: old telemetry fixture tests initially passed without movement because new right pair readiness remained connecting; fixed fixtures to mark right ready and added actual right paired-owner regression plus correct .2/.4 assertions and cross-pair exclusion. No competing right SDK owners started by current server.\n')
