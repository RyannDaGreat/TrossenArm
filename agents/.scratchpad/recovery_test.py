"""Mock-only recovery regression; no hardware access."""
exec(compile(open('agents/.scratchpad/puppet_offline_test.py').read(),'agents/.scratchpad/puppet_offline_test.py','exec'))
shutdown=threading.Event()
pair=puppet.LeftPair(shutdown,Mock())
old=threading.Thread(target=lambda:None);old.start();old.join();pair.owner_thread=old
leader,follower=fake_driver(),fake_driver()
with patch.object(puppet.arm,'TrossenArmDriver',side_effect=[leader,follower]):
    pair.reconnect()
    try:
        wait_until(lambda:pair.snapshot()['mode']=='ready')
        assert not pair.enabled
        follower.set_all_positions.assert_not_called()
        try:pair.reconnect()
        except ValueError:pass
        else:raise AssertionError('Duplicate owner allowed')
        with patch.object(pair,'activate',side_effect=puppet.ControlDeadline('test missed deadline')):
            pair.request('arm','recovery-test',1);pair.request('hold','recovery-test',2)
            wait_until(lambda:pair.snapshot().get('error')=='test missed deadline')
            assert pair.snapshot()['mode']=='ready' and pair.snapshot()['stop_confirmed']
            assert pair.owner_thread.is_alive() and not pair.enabled
    finally:shutdown.set();pair.owner_thread.join(timeout=2)
assert not pair.owner_thread.is_alive()
print('PASS reconnect disarmed, no duplicate owner, timing stop keeps owner alive and idle.')
