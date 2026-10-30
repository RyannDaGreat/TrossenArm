"""Command. Reflect the running controller's Up behavior in the UI."""
from pathlib import Path
p=Path('web/source/frontend/src/Controls.svelte');s=p.read_text().replace('Tall pose · keeps current heading', "Tall pose · {stateFor(choice.role)?.heading?.startsWith('Align') ? 'aligns pair bases' : 'keeps current heading'}")
s=s.replace('Up preserves base heading, resets the wrists, and opens the gripper.', "Up resets the wrists and opens the gripper. {presets?.arms?.follower_right?.heading?.startsWith('Align') ? 'It also sets matching base angles for each pair.' : 'The running controller still preserves base heading; Up cannot correct a base mismatch until the controller update is loaded.'}")
p.write_text(s)
p=Path('web/source/backend/puppet.py');s=p.read_text().replace('Align the {self.side} base headings before enabling puppet mode', 'Use Up on BOTH {self.side} arms to match base angles before enabling puppet mode');p.write_text(s)
print('UI describes actual running Up behavior; updated start rejection names both Up buttons.')
