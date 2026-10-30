"""Command. Add explicit owner recovery and truthful UI error handling."""
from pathlib import Path
p=Path('web/source/backend/puppet.py');s=p.read_text()
s=s.replace('class StartNotReady(Exception):','class ControlDeadline(RuntimeError):\n    """A missed software deadline requiring a confirmed stop, not driver retirement."""\n\n\nclass StartNotReady(Exception):')
s=s.replace('        self.side = side','        self.owner_thread = None\n        self.side = side',1)
pos=s.index('    def snapshot(self):')
s=s[:pos]+'''    def reconnect(self):
        """Command. Replace an exited owner with fresh disarmed connections; never clear faults."""
        with self.lock:
            if self.stop.is_set() or self.owner_thread is None or self.owner_thread.is_alive():
                raise ValueError("Owner still running or stopping; reconnect waits for cleanup")
            if self.enabled or (self.presets and self.presets.busy(self.side)):
                raise ValueError("Stop this pair's movements before reconnecting")
            self.drivers, self.dead, self.fault = {}, set(), None
            self.client, self.deadline, self.stop_pending = None, 0.0, False
            self.generation += 1
            self.set_state(mode="connecting", active=False, error=None, limited=[], stop_confirmed=False)
            self.owner_thread = threading.Thread(target=self.run, daemon=True)
            self.owner_thread.start()

'''+s[pos:]
s=s.replace('"unlimited": self.unlimited}', '"unlimited": self.unlimited, "can_reconnect": self.owner_thread is not None and not self.owner_thread.is_alive()}')
s=s.replace('raise RuntimeError("Current SDK reads exceeded the control deadline")','raise ControlDeadline("Current SDK reads exceeded the control deadline")')
s=s.replace('raise RuntimeError(f"Missed control interval: {dt:.3f}s")','raise ControlDeadline(f"Missed control interval: {dt:.3f}s")')
s=s.replace('        active = False\n        try:', '        self.owner_thread = threading.current_thread()\n        active = False\n        try:',1)
s=s.replace('            self.set_state(mode="ready")','''            for role in self.stop_order:
                if self.sdk(role, "get_error_information") != "No error":
                    raise RuntimeError(f"{role}: controller reports an error; reconnect does not clear it")
                if list(self.sdk(role, "get_modes")) != [arm.Mode.idle]*7:
                    raise RuntimeError(f"{role}: expected idle on connection")
            self.set_state(mode="ready", stop_confirmed=True)''',1)
s=s.replace('                except StartNotReady as reason:\n                    self.halt()', '                except (StartNotReady, ControlDeadline) as reason:\n                    if not self.halt():\n                        raise RuntimeError("Stopping failed; use the physical stop")')
s=s.replace('error=detail, remaining_s=0)', 'error=detail, remaining_s=0, limited=[])')
p.write_text(s)
p=Path('web/source/backend/server.py');s=p.read_text().replace('"disarm", "unlimited"]','"disarm", "unlimited", "reconnect"]')
s=s.replace('        pair.request(body.action, body.client, body.sequence)','        if body.action == "reconnect":\n            pair.reconnect()\n        else:\n            pair.request(body.action, body.client, body.sequence)')
p.write_text(s)
p=Path('web/source/frontend/src/Controls.svelte');s=p.read_text()
pos=s.index('  /** Command. Require a fresh acknowledgement')
s=s[:pos]+'''  /** Command. Reconnect an exited owner; this never enables following. */
  async function reconnect(key) {
    release(key); sessions[key].error = ''; sessions[key].pending = true;
    try { await send(key, 'reconnect'); }
    catch (failure) { sessions[key].error = failure.message; }
    finally { sessions[key].pending = false; }
  }
'''+s[pos:]
s=s.replace('{#if state?.limited?.length}', '{#if running && state?.limited?.length}')
s=s.replace(".toFixed(1)}{limit.joint", ".toFixed(limit.joint === 6 ? 3 : 1)}{limit.joint")
s=s.replace('{sessions[choice].error || state?.error}', '{state?.error || sessions[choice].error}')
s=s.replace('        </article>', '''          {#if state?.can_reconnect}<button class="arm-stop" disabled={sessions[choice].pending} onclick={() => reconnect(choice)}>Reconnect {choice} arms</button>{/if}
          {#if sessions[choice].error && state?.mode === 'ready' && !state?.stop_pending}<button class="arm-stop" onclick={() => { sessions[choice].error = ''; }}>Dismiss message</button>{/if}
        </article>''')
s=s.replace('Base yaw stays as it is; wrist yaw and tool roll reset to zero and the gripper opens. North is not calibrated in these presets.', 'Up sets the verified north base heading, resets wrist yaw and tool roll, and opens the gripper.')
p.write_text(s)
print('Recovery and current-error display implemented.')
