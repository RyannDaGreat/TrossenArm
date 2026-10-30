"""Command. Exercise authorized Up through the exclusive web owner; record feedback."""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
BASE='http://127.0.0.1:28347'
seq=0

def status():
    """Query. Fetch current owner and encoder state."""
    with urllib.request.urlopen(BASE+'/api/status') as response:
        return json.load(response)

def post(action, role=None):
    """Command. Queue an ordered preset action on the existing hardware owner."""
    global seq
    seq+=1
    data=dict(action=action,client='marvin-base-up-20261029-2250',sequence=seq)
    if role: data['role']=role
    request=urllib.request.Request(BASE+'/api/presets',data=json.dumps(data).encode(),headers={'Origin':BASE,'Content-Type':'application/json'})
    with urllib.request.urlopen(request) as response:
        return json.load(response)

for role in ('leader_left','follower_left','leader_right','follower_right'):
    before=status()
    assert not before['puppet']['enabled'] and before['puppet']['active'] is False
    assert not before['puppet_right']['enabled'] and before['puppet_right']['active'] is False
    print('START',role,before['arms'][role]['joints'],before['arms'][role]['gripper'],flush=True)
    post('start',role)
    try:
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            time.sleep(.1)
            state=status()
            preset=state['presets']['arms'][role]
            if preset['role'] is None:
                assert not preset['error'],preset
                break
            try:
                post('hold',role)
            except urllib.error.HTTPError as error:
                detail = json.load(error).get('detail')
                state = status()
                if error.code != 409 or detail != 'No running preset' or state['presets']['arms'][role]['role'] is not None or state['presets']['arms'][role]['error']:
                    raise
                break
        else:
            raise RuntimeError('Preset timeout')
    finally:
        if status()['presets']['arms'][role]['role'] is not None: post('stop',role)
    print('DONE',role,state['arms'][role],flush=True)
Path('agents/.scratchpad/all-up-result.json').write_text(json.dumps(status(),indent=2))
