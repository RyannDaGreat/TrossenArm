"""Mock-only preset owner, cancellation, geometry and security regressions."""
import asyncio
import doctest
import math
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'web/source/backend'))
import presets
from presets import Presets, tall_target
from puppet import LeftPair
from geometry import forward
import server
import trossen_arm as arm


class Fake:
    """Memory-only SDK replacement."""
    def __init__(self):
        """Command. Create stationary seven-idle fixture."""
        self.positions = [0.2, 0, 0, 0, 0, 0.3, 0.01]
        self.velocity = [0]*7
        self.modes = [arm.Mode.idle]*7
        self.writes = []
        self.hook = None
        self.stop_failed = False
        self.bounds = [(-math.pi, math.pi)]*2+[(-2.35, 2.356194496154785)]+[(-math.pi, math.pi)]*3+[(0,0.04)]
    def call(self, method, *args):
        """Command. Simulate SDK calls and record writes. Args: method, args: call. Returns: fixture value."""
        if self.hook:
            self.hook(method)
        if method == 'get_all_positions': return self.positions[:]
        if method == 'get_all_velocities': return self.velocity[:]
        if method == 'get_modes': return self.modes[:]
        if method == 'get_error_information': return 'No error'
        if method == 'get_joint_limits': return [SimpleNamespace(position_min=lo, position_max=hi, position_tolerance=0.2, velocity_max=1.0, velocity_tolerance=0.1) for lo, hi in self.bounds]
        self.writes.append((method, args))
        if method == 'set_all_modes':
            if self.stop_failed and args[0] == arm.Mode.idle: raise RuntimeError('stop transport failed')
            self.modes = [args[0]]*7
        elif method == 'set_all_positions': self.positions = list(args[0])
        else: raise AssertionError(method)


class Tests(unittest.TestCase):
    """Controller tests never construct a real driver."""
    def setUp(self):
        """Command. Create connected fake owners and deterministic time."""
        self.clock = 100.0
        self.patch = patch.object(presets.time, 'monotonic', lambda: self.clock)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.p = Presets(threading.Event())
        self.p.pair = LeftPair(self.p.stop, lambda *args: None, self.p)
        self.p.pair.set_state(mode='ready', stop_confirmed=True)
        for role in presets.ROLES: self.p.connected(role)
        self.d = Fake()
        self.seq = 0
    def request(self, action, role='follower_left'):
        """Command. Queue ordered fixture intent. Args: action, role: intent. Returns: None."""
        self.seq += 1
        self.p.request(action, 'test-browser', self.seq, role)
    def tick(self):
        """Command. Run the left owner's simulated tick."""
        self.p.tick('follower_left', self.d.call)
    def test_geometry_and_complete(self):
        """Command. Verify vertical maximum pose and one bounded continuous trajectory."""
        self.request('start'); self.tick()
        target = self.p.target
        self.assertEqual(target[6], 0.04)
        self.assertEqual((target[0], target[5]), (presets.UP_BASE_RADIANS["left"], 0.0))
        _, tool = forward(target[:6])
        self.assertAlmostEqual(tool[2, 3], 0.853447555, places=7)
        self.assertAlmostEqual(tool[2, 0], 1)
        moves = [args for method, args in self.d.writes if method == 'set_all_positions']
        self.assertEqual([args[1] for args in moves], [0.0, 8.0])
        self.clock += 8; self.request('hold'); self.tick()
        self.assertFalse(self.p.busy()); self.assertTrue(self.p.snapshot()['stop_confirmed'])
        self.assertEqual(self.d.modes, [arm.Mode.idle]*7)
    def test_mutual_exclusion_both_orders(self):
        """Command. Check shared lock rejects overlapping preset/puppet reservations."""
        self.request('start')
        with self.assertRaises(ValueError): self.p.pair.request('arm', 'puppet-browser', 1)
        with self.assertRaises(ValueError): self.request('start', 'follower_right')
        self.request('stop'); self.tick()
        self.p.pair.request('arm', 'puppet-browser', 1)
        with self.assertRaises(ValueError): self.request('start')
    def test_heartbeat_expiry_before_start(self):
        """Command. Ensure expired queued motion never enters position mode."""
        self.request('start'); self.clock += 0.6; self.tick()
        self.assertEqual(self.d.writes, [('set_all_modes', (arm.Mode.idle,))])
    def test_stop_during_read(self):
        """Command. Ensure cancellation during SDK reads blocks subsequent motion writes."""
        self.request('start')
        def cancel(method):
            """Command. Inject stop on position read. Args: method: call name. Returns: None."""
            if method == 'get_all_positions': self.request('stop')
        self.d.hook = cancel; self.tick()
        self.assertEqual(self.d.writes, [('set_all_modes', (arm.Mode.idle,))])
    def test_late_read(self):
        """Command. Reject motor writes after a slow SDK read."""
        self.request('start')
        def delay(method):
            """Command. Advance fake time. Args: method: call name. Returns: None."""
            if method == 'get_all_positions': self.clock += 0.2
        self.d.hook = delay; self.tick()
        self.assertIn('deadline', self.p.snapshot()['error'])
        self.d.hook = None
        self.request('start'); self.tick()
        self.d.hook = delay
        self.tick()
        self.assertIn('deadline', self.p.snapshot()['error'])
        self.assertFalse(self.p.busy())
    def test_wrong_owner_and_stale_requests(self):
        """Command. Ensure other owners cannot execute or steal a queued preset."""
        self.request('start'); self.p.tick('follower_right', self.d.call)
        self.assertEqual(self.d.writes, [])
        with self.assertRaises(ValueError): self.p.request('stop', 'other-browser', 2)
        with self.assertRaises(ValueError): self.p.request('hold', 'test-browser', 1)
    def test_bounds_and_speed(self):
        """Command. Out-of-bound starts and excessive measured speeds stop explicitly."""
        self.d.positions[0] = 4
        self.request('start'); self.tick()
        self.assertIn('bounds', self.p.snapshot()['error'])
        self.assertEqual(len(self.d.writes), 1)
        self.d.positions[0] = 0.2
        self.request('start'); self.tick()
        self.d.velocity[1] = 1.1
        self.request('hold'); self.tick()
        self.assertIn('speed guard', self.p.snapshot()['error'])
    def test_uncertain_stop_retains_ownership(self):
        """Command. Failed stops cannot report idle or allow another control mode."""
        self.request('start'); self.tick(); self.request('stop')
        self.d.stop_failed = True
        with self.assertRaises(RuntimeError): self.tick()
        self.p.unavailable('follower_left', 'stop transport failed')
        self.p.unavailable('follower_left', 'Owner stopped')
        self.assertEqual(self.p.snapshot()['error'], 'stop transport failed')
        self.assertEqual(self.p.snapshot()['mode'], 'stop_unconfirmed')
        self.assertTrue(self.p.busy())
        with self.assertRaises(ValueError): self.p.pair.request('arm', 'puppet-browser', 1)
    def test_shutdown_and_completion_error(self):
        """Command. Stop on shutdown and report failure to reach a target."""
        self.request('start'); self.tick(); self.p.stop.set(); self.tick()
        self.assertFalse(self.p.busy())
        self.p.stop.clear(); self.request('start'); self.tick()
        self.d.positions[1] -= .2
        self.clock += 9; self.request('hold'); self.tick()
        self.assertIn('did not reach', self.p.snapshot()['error'])
    def test_right_existing_owner(self):
        """Command. Exercise the actual right owner loop with a fake SDK; API queues only."""
        hub = server.Observatory()
        hub.pair.set_state(mode='ready')
        hub.right_pair.set_state(mode='ready')
        driver = Mock()
        for method in ('get_error_information', 'get_all_positions', 'get_all_velocities',
                       'get_modes', 'get_joint_limits', 'set_all_modes', 'set_all_positions'):
            getattr(driver, method).side_effect = lambda *args, method=method: self.d.call(method, *args)
        def publish(role, owned):
            """Command. Queue intent on first telemetry, end after target write. Args: role, owned: owner. Returns: None."""
            if not hub.presets.busy():
                hub.presets.request('start', 'test-browser', 1, role)
            elif hub.presets.snapshot()['arms'][role]['mode'] == 'moving':
                hub.stop.set()
        hub.publish = publish
        with patch.object(server.arm, 'TrossenArmDriver', return_value=driver) as factory:
            hub.telemetry('follower_right', 'fixture-only')
        factory.assert_called_once()
        self.assertEqual(self.d.modes, [arm.Mode.idle]*7)
        self.assertFalse(hub.presets.busy())
        self.assertTrue(all(s['stop_confirmed'] for s in hub.presets.snapshot()['arms'].values()))
        driver.cleanup.assert_called_once()

    def test_leader_right_existing_owner(self):
        """Command. Exercise the actual right owner loop with a fake SDK; API queues only."""
        hub = server.Observatory()
        hub.pair.set_state(mode='ready')
        hub.right_pair.set_state(mode='ready')
        driver = Mock()
        for method in ('get_error_information', 'get_all_positions', 'get_all_velocities',
                       'get_modes', 'get_joint_limits', 'set_all_modes', 'set_all_positions'):
            getattr(driver, method).side_effect = lambda *args, method=method: self.d.call(method, *args)
        def publish(role, owned):
            """Command. Queue intent on first telemetry, end after target write. Args: role, owned: owner. Returns: None."""
            if not hub.presets.busy():
                hub.presets.request('start', 'test-browser', 1, role)
            elif hub.presets.snapshot()['arms'][role]['mode'] == 'moving':
                hub.stop.set()
        hub.publish = publish
        with patch.object(server.arm, 'TrossenArmDriver', return_value=driver) as factory:
            hub.telemetry('leader_right', 'fixture-only')
        factory.assert_called_once()
        self.assertEqual(self.d.modes, [arm.Mode.idle]*7)
        self.assertFalse(hub.presets.busy())
        self.assertTrue(all(s['stop_confirmed'] for s in hub.presets.snapshot()['arms'].values()))
        driver.cleanup.assert_called_once()

    def test_leader_left_existing_owner(self):
        """Command. Exercise the actual right owner loop with a fake SDK; API queues only."""
        hub = server.Observatory()
        hub.pair.set_state(mode='ready')
        hub.right_pair.set_state(mode='ready')
        driver = Mock()
        for method in ('get_error_information', 'get_all_positions', 'get_all_velocities',
                       'get_modes', 'get_joint_limits', 'set_all_modes', 'set_all_positions'):
            getattr(driver, method).side_effect = lambda *args, method=method: self.d.call(method, *args)
        def publish(role, owned):
            """Command. Queue intent on first telemetry, end after target write. Args: role, owned: owner. Returns: None."""
            if role != 'leader_left': return
            if not hub.presets.busy():
                hub.presets.request('start', 'test-browser', 1, role)
            elif hub.presets.snapshot()['arms'][role]['mode'] == 'moving':
                hub.stop.set()
        def move(target, duration, blocking):
            """Command. Apply fake target and end the owner loop after its main trajectory."""
            self.d.call('set_all_positions', target, duration, blocking)
            if duration == presets.DURATION_SECONDS:
                hub.stop.set()
        driver.set_all_positions.side_effect = move
        hub.pair.publish = publish
        with patch.object(server.arm, 'TrossenArmDriver', return_value=driver) as factory:
            hub.pair.run()
        self.assertEqual(factory.call_count, 2)
        self.assertEqual(self.d.modes, [arm.Mode.idle]*7)
        self.assertFalse(hub.presets.busy())
        self.assertTrue(all(s['stop_confirmed'] for s in hub.presets.snapshot()['arms'].values()))
        self.assertEqual(driver.cleanup.call_count, 2)

    def test_atomic_reservation(self):
        """Command. Race puppet and preset requests; only one can acquire motion."""
        barrier = threading.Barrier(2)
        outcomes = []
        def reserve(kind):
            """Command. Attempt one reservation. Args: kind: control mode. Returns: None."""
            barrier.wait()
            try:
                if kind == 'preset': self.p.request('start', 'preset-browser', 1, 'follower_left')
                else: self.p.pair.request('arm', 'puppet-browser', 1)
                outcomes.append('accepted')
            except ValueError as error:
                outcomes.append(str(error))
        workers = [threading.Thread(target=reserve, args=(kind,)) for kind in ('preset', 'puppet')]
        for worker in workers: worker.start()
        for worker in workers: worker.join()
        self.assertEqual(outcomes.count('accepted'), 1)

    def test_api(self):
        """Command. Validate same-origin guards and named-only input without lifespan startup."""
        async def check():
            """Command. Send in-memory HTTP intents. Returns: None after assertions."""
            transport = httpx.ASGITransport(app=server.app, client=('127.0.0.1', 50000))
            with patch.object(server.hub, 'presets', self.p):
                async with httpx.AsyncClient(transport=transport, base_url='http://127.0.0.1:28347') as client:
                    body = dict(action='start', role='follower_left', client='test-browser', sequence=1)
                    for origin in (None, 'https://evil.example'):
                        response = await client.post('/api/presets', json=body, headers={} if origin is None else {'Origin': origin})
                        self.assertEqual(response.status_code, 403)
                    headers = {'Origin': 'http://127.0.0.1:28347'}
                    response = await client.post('/api/presets', json={**body, 'role': 'unknown_arm'}, headers=headers)
                    self.assertEqual(response.status_code, 422)
                    response = await client.post('/api/presets', json=body, headers=headers)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(self.d.writes, [])
                    response = await client.post('/api/presets', json=body, headers=headers)
                    self.assertEqual(response.status_code, 409)
        asyncio.run(check())


if __name__ == '__main__':
    assert doctest.testmod(presets).failed == 0
    unittest.main(verbosity=2)
