"""Offline paired-owner tests. Every SDK constructor is mocked; no hardware access."""
import doctest
from functools import partial
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "web/source/backend"))
import puppet

assert doctest.testmod(puppet).failed == 0
command, limited = puppet.limited_target([0, 0.1], [-0.001, 0.12], [0, 0.1], [0, 0.1], [(0,1), (0,1)], 0.02)
assert command[0] == 0 and command[1] > 0.1
assert limited == [{'joint': 0, 'requested': -0.001, 'bounded': 0, 'kind': 'controller bound'}]
print('PASS: boundary jitter clamps only its joint; other joints still follow with explicit diagnostics.')
for invalid_dt in (0, -1, 0.11):
    try:
        puppet.limited_target([0], [0], [0], [0], [(-1,1)], invalid_dt)
    except ValueError:
        pass  # Expected guard rejection.
    else:
        raise AssertionError("Invalid interval accepted")


def set_modes(driver, mode):
    """
    Command. Change only mock arm modes, leaving mock gripper idle.

    Args: driver: mock; mode: SDK Mode.
    Returns: None; set_modes(mock, position) gives six position modes plus idle.
    """
    driver.get_modes.return_value = [mode]*6+[puppet.arm.Mode.idle]


def set_positions(driver, positions, *unused):
    """
    Command. Instantly update mock encoder feedback.

    Args: driver: mock; positions: six angles; unused: timing arguments.
    Returns: None; set_positions(mock, [0]*6) stores six zeros.
    """
    driver.get_arm_positions.return_value = list(positions)


def fake_driver():
    """
    Command. Create an isolated SDK test double with idle modes and valid limits.

    Returns: Mock; fake_driver().get_arm_positions() returns [0.1]*6.
    """
    driver = Mock()
    driver.get_arm_positions.return_value = [0.1]*6
    driver.get_arm_velocities.return_value = [0.0]*6
    driver.get_modes.return_value = [puppet.arm.Mode.idle]*7
    driver.get_error_information.return_value = "No error"
    driver.get_joint_limits.return_value = [SimpleNamespace(position_min=-1, position_max=1, position_tolerance=0.01) for _ in range(7)]
    driver.set_arm_modes.side_effect = partial(set_modes, driver)
    driver.set_arm_positions.side_effect = partial(set_positions, driver)
    return driver


def wait_until(predicate):
    """
    Command. Wait at most two seconds for a mock-worker condition, raising on timeout.

    Args: predicate: zero-argument query.
    Returns: None once predicate is true; wait_until(Event.is_set) waits for that event.
    """
    deadline = time.monotonic()+2
    while not predicate():
        assert time.monotonic() < deadline, "Mock worker condition timed out"
        time.sleep(0.005)


leader, follower = fake_driver(), fake_driver()
stop = threading.Event()
owner = puppet.LeftPair(stop, Mock())
with patch.object(puppet.arm, "TrossenArmDriver", side_effect=[leader, follower]):
    thread = threading.Thread(target=owner.run)
    thread.start()
    try:
        wait_until(lambda: owner.snapshot()["mode"] == "ready")
        owner.request("arm", "offline-client", 1)
        owner.request("hold", "offline-client", 2)
        wait_until(lambda: owner.snapshot()["active"])
        assert follower.set_arm_positions.call_args_list[0].args[0] == [0.1]*6
        leader.get_arm_positions.return_value = [0.12]+[0.1]*5
        wait_until(lambda: abs(follower.get_arm_positions()[0]-0.12) < 1e-6)
        owner.request("stop", "offline-client", 3)
        for action, sequence in (("hold", 2), ("arm", 1)):
            try:
                owner.request(action, "offline-client", sequence)
            except ValueError as error:
                print("Expected stale request rejection:", error)
            else:
                raise AssertionError("Late request resumed control")
        wait_until(lambda: owner.snapshot()["stop_confirmed"] and not owner.snapshot()["active"])
        assert leader.get_modes() == follower.get_modes() == [puppet.arm.Mode.idle]*7
        owner.request("arm", "offline-client", 4)
        owner.request("hold", "offline-client", 5)
        wait_until(lambda: owner.snapshot()["active"])
        wait_until(lambda: owner.snapshot()["stop_confirmed"] and not owner.snapshot()["active"])  # Heartbeat expires.
        assert not owner.snapshot()["enabled"]
        print("PASS: relative engagement, bounded following, ordered stop, stale-arm rejection, and heartbeat expiry.")
    finally:
        stop.set()
        thread.join(timeout=2)
        assert not thread.is_alive()
for driver in (leader, follower):
    driver.set_gripper_mode.assert_not_called()
    driver.set_all_positions.assert_not_called()
    driver.cleanup.assert_called_once()
print("PASS: both exclusive mock drivers released; no gripper copying or automatic home.")

# Stop must remain latched even when stop/arm/hold arrive between worker ticks.
owner = puppet.LeftPair(threading.Event(), Mock())
owner.drivers = {"leader_left": fake_driver(), "follower_left": fake_driver()}
owner.set_state(mode="ready")
owner.request("arm", "client-A", 1)
owner.request("hold", "client-A", 2)
owner.request("stop", "client-A", 3)
for client, sequence in (("client-A", 4), ("client-B", 1)):
    try:
        owner.request("arm", client, sequence)
    except ValueError as error:
        assert "Stop pending" in str(error)
    else:
        raise AssertionError("Rearm bypassed pending stop")
assert owner.halt()
owner.request("arm", "client-A", 4)
owner.request("hold", "client-A", 5)
generation = owner.generation


def cancel_during_activation(mode):
    """
    Command. Inject a stop after the first mock mode write.

    Args: mode: requested mock mode.
    Returns: None; cancellation must prevent the remaining activation writes.
    """
    set_modes(owner.drivers["follower_left"], mode)
    if mode == puppet.arm.Mode.position:
        owner.request("stop", "client-A", 6)


owner.drivers["follower_left"].set_arm_modes.side_effect = cancel_during_activation
try:
    owner.activate(generation, time.monotonic())
except puppet.IntentStopped:
    pass  # Expected cancellation, not a hidden hardware failure.
else:
    raise AssertionError("Activation ignored stop")
owner.drivers["follower_left"].set_arm_positions.assert_not_called()
assert owner.halt()
owner.request("arm", "client-A", 7)
owner.request("hold", "client-A", 8)
try:
    owner.require_intent(owner.generation, time.monotonic()-0.2)
except RuntimeError as error:
    assert "Current SDK reads" in str(error)
else:
    raise AssertionError("Slow current read accepted")
assert owner.halt()
print("PASS: stop/rearm race, competing client, cancellation during activation, and slow-current-read guard.")

# A failed leader must not delay a healthy follower's stop behind leader cleanup.
leader, follower = fake_driver(), fake_driver()
leader.get_arm_positions.side_effect = RuntimeError("simulated leader read fault")
owner = puppet.LeftPair(threading.Event(), Mock())
order = Mock()
order.attach_mock(follower.set_arm_modes, "follower_idle")
order.attach_mock(follower.cleanup, "follower_cleanup")
order.attach_mock(leader.cleanup, "leader_cleanup")
with patch.object(puppet.arm, "TrossenArmDriver", side_effect=[leader, follower]):
    thread = threading.Thread(target=owner.run)
    thread.start()
    wait_until(lambda: owner.snapshot()["mode"] == "ready")
    owner.request("arm", "fault-client", 1)
    owner.request("hold", "fault-client", 2)
    thread.join(timeout=2)
    assert not thread.is_alive()
assert owner.snapshot()["mode"] == "stop_unconfirmed"
assert owner.snapshot()["active"] is None
names = [call[0] for call in order.mock_calls]
assert names.index("follower_idle") < names.index("follower_cleanup") < names.index("leader_cleanup")
leader.set_arm_modes.assert_not_called()
assert "simulated leader read fault" in owner.snapshot()["error"]
print("PASS: failed driver retired; healthy follower stopped first; uncertainty and original fault retained.")
