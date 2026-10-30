"""Query. Observe owner state and matching encoders without controlling hardware."""
import json,time,urllib.request
from pathlib import Path
samples=[]
for _ in range(60):
    with urllib.request.urlopen('http://127.0.0.1:28347/api/status') as response: s=json.load(response)
    a,b=(s['arms'][role] for role in ('leader_left','follower_left'))
    entry=dict(at=time.time(),puppet=s['puppet'],leader=a['joints']+[a['gripper']],follower=b['joints']+[b['gripper']])
    samples.append(entry)
    if len(samples)==1 or entry['puppet']!=samples[-2]['puppet']:
        print(entry,flush=True)
    time.sleep(.5)
Path('agents/.scratchpad/absolute-observation.json').write_text(json.dumps(samples,indent=2))
