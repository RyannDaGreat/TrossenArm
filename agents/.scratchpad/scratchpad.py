"""Command. Record operator-verified north registration and preserve replaced history."""
from pathlib import Path
p=Path('agents/manifest.md')
s=p.read_text()
replacements={
'Separate local q0 frames have no verified compass offset; do not assume q0=0 means north.':'Verified Up base headings are +91.2° for both left arms and −87.6° for both right arms; q0=0 is not north.',
'No base rotation has been performed for north alignment.':'All four arms completed the updated base-aligned Up move; the operator visually confirmed all four face north.',
'The presets raise a follower toward the validated tall pose in one eight-second interpolation, keeping its current base yaw and tool roll: encoder zero is not a verified north heading.':'The presets raise any selected arm toward the validated tall pose in one eight-second interpolation, set its side’s verified north base angle, reset both wrist axes, and open the gripper.',
'A preset and puppet mode cannot own motion concurrently.':'A preset and puppet mode cannot own the same arm concurrently; disjoint arms may move independently.',
'Joint-coordinate copying does not establish world compass alignment when mount registration differs.':'The operator confirmed this installation mounts each leader/follower pair consistently: the shared side-specific Up base angle faces north on both.',
'Preserve base heading.':'Set the side-specific north base heading.',
}
old=[]
for a,b in replacements.items():
    if a in s:
        old.append(a)
        s=s.replace(a,b)
record='''## Verified installation: all four Up poses face north

The operator visually confirmed all four arms face north after the updated Up moves. The arms are mounted consistently for this mapping; do not treat leader mount registration as unknown in this installation. Both left arms use base +91.2°, both right arms use −87.6°. Up must set these angles, reset wrist yaw and tool roll to zero, open the gripper, and raise the arm. North remains the duck’s beak direction toward the rear wall. This is operator-confirmed visual alignment, not a precision survey. Reassess only if the mounting arrangement changes.

All four completed their eight-second trajectories and subsequently reported seven idle modes, no errors. Post-move wrist images agree with the previously registered north wall: `agents/.scratchpad/base-up-left-after.jpg`, `agents/.scratchpad/base-up-right-after.jpg`. Motion record: `agents/.scratchpad/logs/base-up-all.log`.

'''
s=s.replace('# ', '# ',1)
p.write_text(record+s)
with Path('agents/concerns.md').open('a') as f:
    f.write('\n## Operator confirms all four face north\nAll four updated Up moves completed, then fresh telemetry confirmed idle/noerror. User visually confirmed matching installation mounts make these side-specific encoder headings north for leaders and followers alike. Earlier assumption that leader registration remained unknown is superseded. Removed obsolete instructions from manifest, retained here:\n'+ '\n'.join('- '+x for x in old)+'\n')
with Path('agents/transcript.md').open('a') as f:
    f.write('\nUser: “Oh, actually no, they’re all good. They’re all mounted the same way. You can write that down. They’re mounted such that when you do this, they do all need to face north. Don’t forget that. The manifest can record it.”\n')
with Path('agents/todo.md').open('a') as f:
    f.write('\n- [x] Execute updated Up on all four arms; verify idle/noerror and record operator confirmation that all four face north.\n')
print('Recorded verified mounting and north headings; removed conflicting instructions.')
