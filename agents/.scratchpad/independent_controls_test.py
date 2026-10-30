"""Offline concurrency and cancellation checks; no real SDK construction."""
import threading
from unittest.mock import Mock, patch
import presets_offline_test as fixtures
from presets import PresetGroup, ROLES
from puppet import LeftPair
import presets
import trossen_arm as arm

clock = [100.0]
group = PresetGroup(threading.Event())
left = LeftPair(group.stop, Mock(), group)
right = LeftPair(group.stop, Mock(), group, side='right')
group.pair = left
group.pairs = {'left': left, 'right': right}
for pair in group.pairs.values(): pair.set_state(mode='ready', active=False)
for role in ROLES: group.connected(role)
drivers = {role: fixtures.Fake() for role in ROLES}
with patch.object(presets.time, 'monotonic', lambda: clock[0]):
    left.request('arm','left-client',1)
    right.request('arm','right-client',1)
    left.request('hold','left-client',2)
    right.request('hold','right-client',2)
    assert left.enabled and right.enabled
    for role in ROLES:
        try: group.request('start',role,1,role)
        except ValueError: pass
        else: raise AssertionError('Overlapping puppet and Up accepted')
    # Stop left intent without altering right heartbeat or generation.
    generation = right.generation
    left.request('stop','left-client',3)
    assert right.enabled and right.generation == generation
    for pair in (left,right):
        pair.enabled = False
        pair.stop_pending = False
        pair.client = None
    for role in ROLES: group.request('start',role,1,role)
    assert len([state for state in group.snapshot()['arms'].values() if state['role']]) == 4
    for pair in (left,right):
        try: pair.request('arm',pair.side+'-again',1)
        except ValueError: pass
        else: raise AssertionError('Puppet overlapped active Up')
    for role in ROLES: group.tick(role,drivers[role].call)
    group.request('stop','follower_left',2,'follower_left')
    group.tick('follower_left',drivers['follower_left'].call)
    assert drivers['follower_left'].modes == [arm.Mode.idle]*7
    assert all(drivers[role].modes == [arm.Mode.position]*7 for role in ROLES if role != 'follower_left')
    # Expiry on one arm must not stop the three other channels.
    clock[0] += .6
    for role in ('leader_left','leader_right'): group.request('hold',role,2,role)
    for role in ROLES: group.tick(role,drivers[role].call)
    assert drivers['follower_right'].modes == [arm.Mode.idle]*7
    assert drivers['leader_left'].modes == drivers['leader_right'].modes == [arm.Mode.position]*7
    # Finish the remaining pair-independent trajectories.
    clock[0] += 8
    for role in ('leader_left','leader_right'):
        group.request('hold',role,3,role)
        group.tick(role,drivers[role].call)
    assert not group.busy()
    # A left preset may coexist with right puppeteering.
    group.request('start','follower_left',3,'follower_left')
    right.request('arm','new-right-client',1)
    assert right.enabled and group.busy('left') and not group.busy('right')
    # Cancellation inside an SDK read never reaches position-mode writes.
    def cancel(method):
        if method == 'get_all_positions': group.request('stop','follower_left',4,'follower_left')
    drivers['follower_left'].writes.clear()
    drivers['follower_left'].hook = cancel
    group.tick('follower_left',drivers['follower_left'].call)
    assert drivers['follower_left'].writes == [('set_all_modes',(arm.Mode.idle,))]
print('PASS: simultaneous pairs, four Up reservations, overlap rejection, individual stop/expiry, and cancellation during reads.')

# Exercise both real owner loops against four isolated fake drivers.
import time
from presets import tall_target
fresh = PresetGroup(threading.Event())
workers = {side: LeftPair(fresh.stop, Mock(), fresh, side=side) for side in ('left','right')}
fresh.pairs, fresh.pair = workers, workers['left']
by_ip = {}
def make_driver():
    """Command. Create one independent fake SDK; configure records its role address."""
    fake = fixtures.Fake()
    fake.positions = tall_target(fake.positions[:6],fake.bounds[:6])+[.04]
    driver = Mock()
    driver.configure.side_effect = lambda model, effector, ip, debug, timeout: by_ip.update({ip:fake})
    for method in ('get_error_information','get_all_positions','get_all_velocities','get_modes','get_joint_limits','set_all_modes','set_all_positions'):
        getattr(driver,method).side_effect = lambda *args, method=method: fake.call(method,*args)
    return driver

def wait_for(condition):
    """Command. Bound asynchronous mock checks to two seconds."""
    deadline = time.monotonic()+2
    while not condition():
        assert time.monotonic()<deadline, 'Concurrent owner condition timed out'
        time.sleep(.005)

with patch('puppet.arm.TrossenArmDriver',side_effect=make_driver):
    threads = [threading.Thread(target=pair.run) for pair in workers.values()]
    for thread in threads: thread.start()
    try:
        wait_for(lambda: all(pair.snapshot()['mode']=='ready' for pair in workers.values()))
        for side,pair in workers.items():
            pair.request('arm',side+'-live-mock',1)
            pair.request('hold',side+'-live-mock',2)
        wait_for(lambda: all(pair.snapshot()['active'] for pair in workers.values()))
        by_ip['192.168.1.3'].positions[0]+=.02
        by_ip['192.168.1.2'].positions[0]-=.02
        wait_for(lambda: abs(by_ip['192.168.1.5'].positions[0]-.22)<.001 and abs(by_ip['192.168.1.4'].positions[0]-.18)<.001)
        workers['left'].request('stop','left-live-mock',3)
        wait_for(lambda: workers['left'].snapshot()['stop_confirmed'])
        assert workers['right'].snapshot()['active']
        assert by_ip['192.168.1.4'].modes == [arm.Mode.position]*7
    finally:
        fresh.stop.set()
        for thread in threads:
            thread.join(2)
            assert not thread.is_alive()
assert all(fake.modes == [arm.Mode.idle]*7 for fake in by_ip.values())
print('PASS: two actual owner loops copy concurrently through four mocked SDKs; one stop leaves its peer active; shutdown idles all.')
