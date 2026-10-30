"""Command. Stop all six control channels and verify idle before server shutdown."""
import json, time, urllib.request
base='http://127.0.0.1:28347'
for index,key in enumerate(['left','right','leader_left','follower_left','leader_right','follower_right'],1):
    endpoint='presets' if '_' in key else 'puppet'
    body={'action':'stop','client':'marvin-session-shutdown','sequence':index, 'role' if '_' in key else 'side':key}
    request=urllib.request.Request(base+'/api/'+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(request,timeout=5) as response:
        print(key,response.status)
for attempt in range(30):
    with urllib.request.urlopen(base+'/api/status',timeout=5) as response: status=json.load(response)
    if all(a['modes']==['idle']*7 for a in status['arms'].values()):
        print('All four arms report seven idle modes.');break
    time.sleep(.1)
else: raise RuntimeError('Idle not confirmed')
