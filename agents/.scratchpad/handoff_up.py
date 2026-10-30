"""Command. Authorized sequential Up, only after the web SDK owners have exited."""
import json
import sys
import threading
import time
from pathlib import Path
sys.path.insert(0,str(Path('web/source/backend').resolve()))
import trossen_arm as arm
from presets import Presets
from geometry import forward

class Ready:
    """Query-only readiness for this exclusive standalone owner."""
    def snapshot(self):
        return dict(mode='ready',enabled=False,stop_pending=False,active=False)

results={}
for role, ip in [('leader_left','192.168.1.3'),('follower_left','192.168.1.5'),('leader_right','192.168.1.2'),('follower_right','192.168.1.4')]:
    driver=arm.TrossenArmDriver()
    configured=False
    try:
        driver.configure(arm.Model.wxai_v0, getattr(arm.StandardEndEffector,'wxai_v0_'+role.split('_')[0]), ip, False, 5.0)
        configured=True
        preset=Presets(threading.Event());preset.pair=Ready();preset.connected(role)
        seq=1
        preset.request('start','marvin-authorized-handoff',seq,role)
        print('START',role,flush=True)
        deadline=time.monotonic()+12
        while preset.busy():
            if time.monotonic()>deadline: raise TimeoutError('Up did not complete')
            seq+=1
            preset.request('hold','marvin-authorized-handoff',seq,role)
            preset.tick(role,lambda method,*args:getattr(driver,method)(*args))
            time.sleep(.02)
        assert not preset.snapshot()['error'],preset.snapshot()
        q=list(driver.get_arm_positions());_,tool=forward(q)
        assert tool[2,0]>.995 and tool[2,3]>.84
        assert list(driver.get_modes())==[arm.Mode.idle]*7
        assert driver.get_error_information()=='No error'
        results[role]=dict(joints=q,up=float(tool[2,0]),height=float(tool[2,3]),gripper=driver.get_all_positions()[6])
        print('VERIFIED',role,results[role],flush=True)
    finally:
        if configured:
            driver.set_all_modes(arm.Mode.idle)
            assert list(driver.get_modes())==[arm.Mode.idle]*7
        driver.cleanup()
Path('agents/.scratchpad/handoff-up-result.json').write_text(json.dumps(results,indent=2))
