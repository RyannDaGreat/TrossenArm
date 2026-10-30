"""Mock regression for all-axis catch-up, lag and engagement rejection."""
exec(compile(open('agents/.scratchpad/puppet_offline_test.py').read(), 'agents/.scratchpad/puppet_offline_test.py', 'exec'))
for index in range(7):
    target = START[:]
    target[index] -= 0.3 if index < 6 else 0.015
    target[index] = max(BOUNDS[index][0], target[index])
    current = START[:]
    for _ in range(400):
        nxt, _ = puppet.limited_target(current, target, BOUNDS, [.5]*6+[.02], .02)
        assert all(abs(a-b) <= speed*.02+1e-10 for a,b,speed in zip(nxt,current,[.5]*6+[.02]))
        current = [a+(b-a)*.5 for a,b in zip(current,nxt)]  # Delayed hardware response.
    assert max(abs(a-b) for a,b in zip(current,target)) < 1e-6
for index, delta in ((1,-.2),(4,.2),(5,.2),(6,-.01),(0,.2)):
    pair = puppet.LeftPair(threading.Event(), Mock())
    pair.drivers = {role:fake_driver() for role in puppet.STOP_ORDER}
    pair.set_state(mode='ready')
    pair.request('arm','gate',1); pair.request('hold','gate',2)
    pair.drivers['leader_left'].get_all_positions.return_value[index] += delta
    try:
        pair.activate(pair.generation, time.monotonic())
    except puppet.StartNotReady:
        pass
    else:
        raise AssertionError('Bad start accepted')
    for driver in pair.drivers.values():
        driver.set_all_modes.assert_not_called()
print('PASS: all seven axes converge after delayed feedback; bad posture/wrist/gripper/base rejected before writes.')
pair = puppet.LeftPair(threading.Event(), Mock())
pair.set_state(mode='ready')
pair.request('arm','timer',1); pair.request('hold','timer',2)
try:
    pair.require_intent(pair.generation,time.monotonic(),time.monotonic()-61)
except puppet.IntentStopped:
    pass
else:
    raise AssertionError('Default session did not expire')
pair.request('unlimited','timer',3)
pair.require_intent(pair.generation,time.monotonic(),time.monotonic()-600)
pair.deadline=time.monotonic()-1
try:
    pair.require_intent(pair.generation,time.monotonic(),time.monotonic()-600)
except puppet.IntentStopped:
    pass
else:
    raise AssertionError('Unlimited mode bypassed heartbeat')
leader,follower=fake_driver(),fake_driver()
leader.get_all_velocities.return_value=[.1]*7
shutdown=threading.Event()
pair=puppet.LeftPair(shutdown,Mock())
with patch.object(puppet.arm,'TrossenArmDriver',side_effect=[leader,follower]):
    worker=threading.Thread(target=pair.run);worker.start()
    try:
        wait_until(lambda: pair.snapshot()['mode']=='ready')
        pair.request('arm','moving',1);pair.request('hold','moving',2)
        wait_until(lambda: pair.snapshot()['stop_confirmed'])
        assert pair.snapshot()['mode']=='ready' and not pair.snapshot()['enabled'],pair.snapshot()
        follower.set_all_positions.assert_not_called()
        pair.request('arm','moving',3)
        assert not pair.snapshot()['unlimited']
    finally:
        shutdown.set();worker.join(timeout=2)
print('PASS: optional unlimited duration retains heartbeat; moving-start rejection returns ready and allows reuse.')
