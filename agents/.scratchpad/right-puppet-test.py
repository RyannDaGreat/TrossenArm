"""Mock regression. Run identical owner lifecycle tests using right-role routing."""
from pathlib import Path
source=Path('agents/.scratchpad/puppet_offline_test.py').read_text()
source=source.replace('puppet.LeftPair(', 'partial(puppet.LeftPair, side="right")(').replace('leader_left','leader_right').replace('follower_left','follower_right')
exec(compile(source,'right-puppet-regression','exec'))
assert leader.configure.call_args.args[2]=='192.168.1.2'
assert follower.configure.call_args.args[2]=='192.168.1.4'
print('PASS: right pair uses .2/.4, same seven-joint copying, stop ordering and cancellation guards.')
from presets import Presets
shared=Presets(threading.Event())
left=puppet.LeftPair(shared.stop,Mock(),shared)
right=puppet.LeftPair(shared.stop,Mock(),shared,side='right')
shared.pairs={'left':left,'right':right};shared.pair=left
for p in (left,right):p.set_state(mode='ready')
right.request('arm','right-test',1)
try:left.request('arm','left-test',1)
except ValueError:pass
else:raise AssertionError('Both pairs reserved motion')
print('PASS: shared reservation excludes overlapping left/right engagements.')
