"""Command. Record control verification and pending operator test."""
from pathlib import Path
for name in ('agents/manifest.md','agents/todo.md'):
    p=Path(name);s=p.read_text()
    duplicate='\n## Absolute puppet update\nUser requests all six angles plus gripper, bounded catch-up, upright aligned engagement, and Up resets wrist yaw/roll to zero and opens grippers for all four roles. Preserve base heading. Use existing SDK owners and all-joint SDK methods documented in offline vendor teleoperation.py; gripper uses meters. Keep heartbeat, deadlines, factory faults and stop confirmation. No automatic engagement.\n'
    if s.count(duplicate)>1:s=s.replace(duplicate,'',1)
    line='\n- [ ] Absolute seven-joint following, upright alignment gate, normalized/open Up, offline and live verification, phone/audio delivery.\n'
    if s.count(line)>1:s=s.replace(line,'',1)
    p.write_text(s)
with Path('agents/manifest.md').open('a') as f:
    f.write('\nAbsolute update verification: mocked seven-channel catch-up including delayed feedback and all upright/wrist/gripper/base rejection cases passed; fourteen preset tests, API regressions, build and intercepted browser tests passed. Per-tick follower-feedback anchoring prevents queued error from accumulating. Application target-step limits are0.5rad/s arm,0.02m/s gripper, capped by actual factory velocity bounds; remaining controller position/velocity/fault and heartbeat/deadline guards unchanged. Upright and base alignment tolerance0.06rad; open-gripper tolerance0.002m. Up preserves base yaw, sets wrist yaw and roll0, opens to actual factory maximum, and confirms all7idle on completion. Physically ran left leader/follower Up: grippers0.0400299/0.0400131m, wrist axes approximately0, no errors. Hardware hand-driven seven-axis follow trial awaits operator; never claim mock tests as that trial. Evidence agents/.scratchpad/absolute-up-result.json and logs/absolute-up-20261029.log.\n')
with Path('agents/concerns.md').open('a') as f:
    f.write('\nAbsolute puppet revision: repeated non-idempotent scratch script stopped on missing old substring; extracted test adaptation then fixed missing Path import. All resulting source verified by tests. Removed old trial excursion/tracking/velocity stops; bounded feedback-anchored targets and unchanged factory checks now govern lag. No claim of maximum mechanical speed. All7 idle readbacks now mandatory including gripper. Two real left Up moves passed; hand-driven follow validation pending.\n')
print('Recorded verification and remaining physical trial.')
