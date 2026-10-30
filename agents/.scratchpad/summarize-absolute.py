"""Query. Summarize observed physical copying across all seven axes."""
import json
from pathlib import Path
s=json.loads(Path('agents/.scratchpad/absolute-observation.json').read_text())
a=[v for v in s if v['puppet']['active']]
for j in range(7):
    lead=[v['leader'][j] for v in a];follow=[v['follower'][j] for v in a]
    print(j,'leader excursion',max(lead)-min(lead),'follower excursion',max(follow)-min(follow))
best=min(a,key=lambda v:max(abs(x-y)/(0.002 if j==6 else .03) for j,(x,y) in enumerate(zip(v['leader'],v['follower']))))
print('Best simultaneously matched sample:',best)
print('errors:',[v['puppet']['error'] for v in s if v['puppet']['error']])
