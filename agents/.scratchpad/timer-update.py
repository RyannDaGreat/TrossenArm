"""Command. Add optional unlimited sessions and recoverable engagement rejection."""
from pathlib import Path
with Path('agents/manifest.md').open('a') as f:
    f.write('\nUser requests optional unlimited puppet sessions via animated monochrome stopwatch next to toggle. Keep heartbeat/Stop; expiry opt-out per engagement, resets next arm. User dislikes button lockouts: stationary precondition must be recoverable, never latch hardware fault or block Up. Observed live seven-axis copy passed: each axis moved, gripper excursion39.96mm leader/39.26mm follower; one settled sample max arm error0.000382rad, gripper0.0000133m.\n')
p=Path('web/source/backend/puppet.py');s=p.read_text().replace('self.enabled = False','self.enabled = False\n        self.unlimited = False',1).replace('"stop_pending": self.stop_pending}','"stop_pending": self.stop_pending, "unlimited": self.unlimited}')
s=s.replace('self.client, self.enabled = client, True','self.client, self.enabled = client, True\n                self.unlimited = False')
s=s.replace('            elif action == "hold":','            elif action == "unlimited":\n                if not self.enabled:\n                    raise ValueError("Enable puppet mode first")\n                self.unlimited = True\n                self.deadline = time.monotonic()+HEARTBEAT_SECONDS\n            elif action == "hold":')
s=s.replace('(engaged is not None and now-engaged >= SESSION_SECONDS)','(engaged is not None and not self.unlimited and now-engaged >= SESSION_SECONDS)').replace('(not held or now-engaged >= SESSION_SECONDS)','(not held or (not self.unlimited and now-engaged >= SESSION_SECONDS))').replace('remaining_s=max(0, SESSION_SECONDS-(time.monotonic()-engaged))','remaining_s=None if self.unlimited else max(0, SESSION_SECONDS-(time.monotonic()-engaged))')
s=s.replace('raise RuntimeError("Hold the leader still before engagement")','raise StartNotReady("Puppet start cancelled because an arm was moving. Up is available; try puppet mode once both arms have stopped.")')
p.write_text(s)
p=Path('web/source/backend/server.py');p.write_text(p.read_text().replace('Literal["arm", "hold", "stop", "disarm"]','Literal["arm", "hold", "stop", "disarm", "unlimited"]'))
p=Path('web/source/frontend/src/widgets/Stopwatch/Stopwatch.svelte');p.parent.mkdir(parents=True,exist_ok=True);p.write_text('''<script>
  let { remaining = 60, unlimited = false, onclick } = $props();
  let seconds = $derived(Math.max(0, Math.ceil(remaining ?? 60)));
  let angle = $derived((60 - (remaining ?? 60)) * 6);
</script>

<button class="stopwatch" class:unlimited onclick={onclick}
  aria-label={unlimited ? 'Puppet timer off — no time limit' : 'Turn off puppet time limit'}
  aria-pressed={unlimited} title={unlimited ? 'No time limit · Stop still works' : 'Click to keep puppet mode on without a time limit'}>
  <svg viewBox="0 0 40 44" aria-hidden="true">
    <path d="M16 3h8M20 3v5M31 9l3 3M32 10l-3 3" />
    <circle cx="20" cy="25" r="15" />
    <path class="ticks" d="M20 12v2M33 25h-2M20 38v-2M7 25h2" />
    {#if unlimited}<path d="M20 25c-8-10-15 6-6 4 4-1 8-9 12-8 9 2 2 15-6 4" />
    {:else}<g class="hand" style:transform={`rotate(${angle}deg)`}><path d="M20 25V16" /><circle cx="20" cy="25" r="1" /></g>{/if}
  </svg>
  <span>{unlimited ? '∞' : `${seconds}s`}</span>
</button>

<style>
  .stopwatch { display: inline-flex; align-items: center; gap: 5px; padding: 3px 7px; background: transparent; color: inherit; border: 0; cursor: pointer; font: inherit; font-variant-numeric: tabular-nums; }
  svg { width: 30px; height: 34px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
  .hand { transform-origin: 20px 25px; transition: transform .15s linear; }
  span { min-width: 27px; font-size: 12px; }
  .stopwatch:hover { background: #00000009; }
  .stopwatch:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) { .hand { transition: none; } }
</style>
''')
p=Path('web/source/frontend/src/Controls.svelte');s=p.read_text().replace("import { onMount } from 'svelte';","import { onMount } from 'svelte';\n  import Stopwatch from './widgets/Stopwatch/Stopwatch.svelte';\n  let unlimitedRequested = $state(false);")
s=s.replace("try { await send(kind, 'hold'); } catch (failure)","try {\n      await send(kind, kind === 'puppet' && unlimitedRequested ? 'unlimited' : 'hold');\n      unlimitedRequested = false;\n    } catch (failure)")
s=s.replace("pending = true; error = ''; control = kind;","pending = true; error = ''; control = kind; unlimitedRequested = false;")
s=s.replace('`${Math.ceil(visibleState.remaining_s ?? 0)} seconds left`',"visibleState.unlimited ? 'No time limit' : `${Math.ceil(visibleState.remaining_s ?? 0)} seconds left`")
needle='      <button class="switch" role="switch" aria-checked={control'
s=s.replace(needle,'      {#if control === \'puppet\' || pairState?.enabled}<Stopwatch remaining={pairState?.remaining_s ?? 60} unlimited={!!pairState?.unlimited} onclick={() => { unlimitedRequested = true; }} />{/if}\n'+needle)
s=s.replace('Puppet mode ends after 60 seconds and catches up','Click the stopwatch to remove the 60-second session limit. Puppet mode catches up')
s=s.replace('{degrees(limit.requested)} requested, {degrees(limit.bounded)} held','{limit.joint === 6 ? `${(limit.requested*1000).toFixed(1)} mm` : degrees(limit.requested)} requested, {limit.joint === 6 ? `${(limit.bounded*1000).toFixed(1)} mm` : degrees(limit.bounded)} held')
p.write_text(s)
print('Added stopwatch and recoverable moving-start rejection.')
