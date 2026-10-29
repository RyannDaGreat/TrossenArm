<script>
  import { onMount } from 'svelte';
  let { state: pairState, follower } = $props();
  let dialog;
  let confirmed = $state(false);
  let following = $state(false);
  let pending = $state(false);
  let error = $state('');
  let timer, sequence = 0, sending = false;
  const client = crypto.randomUUID();
  const jointNames = ['Base', 'Shoulder', 'Elbow', 'Wrist pitch', 'Wrist yaw', 'Tool roll'];

  /** Pure function. Convert radians to a degree label. @param {number} value Radians. @returns {string} @example degrees(Math.PI/2) // '90.0°' */
  function degrees(value) { return `${(value*180/Math.PI).toFixed(1)}°`; }

  /** Command. Send ordered browser intent. @param {string} action arm/hold/stop. @returns {Promise<object>} Pair state. @example send('stop') // queues a latched stop */
  async function send(action) {
    const response = await fetch('/api/puppet', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(1500), body: JSON.stringify({ action, client, sequence: ++sequence }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `Control HTTP ${response.status}`);
    return result;
  }

  /** Command. Report failure and cancel automatic heartbeat. @param {Error} failure Failure. @returns {void} */
  function fail(failure) { error = String(failure); console.error(failure); following = false; clearInterval(timer); }

  /** Command. Disable the pair; release both hands from the computer. @returns {Promise<void>} */
  async function stop() {
    const needed = following || pairState?.enabled;
    following = false; clearInterval(timer);
    if (needed) { try { await send('stop'); } catch (failure) { fail(failure); } }
  }

  /** Command. Keep a switched-on session alive; never queue overlapping heartbeats. @returns {Promise<void>} */
  async function heartbeat() {
    if (!following || sending) return;
    sending = true;
    try { await send('hold'); } catch (failure) { fail(failure); }
    finally { sending = false; }
  }

  /** Command. Start/stop latched following after operator acknowledgement. @returns {Promise<void>} */
  async function toggle() {
    pending = true; error = '';
    try {
      if (following || pairState?.enabled) await stop();
      else {
        await send('arm'); following = true;
        await heartbeat();
        if (following) timer = setInterval(heartbeat, 100);
      }
    } catch (failure) { fail(failure); }
    finally { pending = false; }
  }

  /** Command. Open controls with a fresh workspace acknowledgement. @returns {void} */
  function open() { confirmed = false; error = ''; dialog.showModal(); }
  /** Command. Stop before dismissing the modal. @returns {Promise<void>} */
  async function close() { await stop(); dialog.close(); }

  onMount(() => {
    /** Command. Request stop during page exit; heartbeat expiry remains independent. @returns {void} */
    function leaving() {
      if (following || pairState?.enabled) {
        const sent = navigator.sendBeacon('/api/puppet', new Blob([
          JSON.stringify({ action: 'stop', client, sequence: ++sequence })
        ], { type: 'application/json' }));
        if (!sent) console.error('Exit stop could not be queued; heartbeat timeout remains active');
      }
      following = false; clearInterval(timer);
    }
    window.addEventListener('pagehide', leaving);
    window.addEventListener('blur', stop);
    return () => { leaving(); window.removeEventListener('pagehide', leaving); window.removeEventListener('blur', stop); };
  });
</script>

<button class="control-launch" onclick={open}>Robot controls <span>↗</span></button>
<dialog bind:this={dialog} class="control-modal" oncancel={(event) => { event.preventDefault(); close(); }}>
  <header><div><p class="eyebrow">LEFT PAIR / OPERATOR CONTROL</p><h2>Puppet mode</h2></div><button class="icon-button" onclick={close} aria-label="Close robot controls">×</button></header>
  <p class="control-route">Leader left <strong>192.168.1.3</strong> → Follower left <strong>192.168.1.5</strong></p>
  <div class="control-state" class:active={pairState?.active}><span>{pairState?.mode ?? 'connecting'}</span><span>{pairState?.active ? `${Math.ceil(pairState.remaining_s ?? 0)} seconds left` : pairState?.mode === 'stop_unconfirmed' ? 'USE PHYSICAL STOP' : 'No automatic movement'}</span></div>
  <p class="notice">Hands-free toggle. Arm-only trial; grippers stay idle. Relative joint motion is capped at ±14° from engagement and 14°/s. These are software trial limits, not obstacle detection. Tiny factory-bound corrections up to 0.12° may occur at activation.</p>
  <div class="switch-row"><div><strong>Workspace clear</strong><small>I am at the leader, the follower path is clear, and a physical power stop is reachable.</small></div>
    <button class="switch" role="switch" aria-checked={confirmed} aria-label="Confirm operator and workspace clearance" onclick={() => { confirmed = !confirmed; if (!confirmed) stop(); }}><span></span></button></div>
  <div class="switch-row"><div><strong>Enable puppet mode</strong><small>Switch on, then use both hands on the leader. Switch off or press Stop to end.</small></div>
    <button class="switch" role="switch" aria-checked={following || !!pairState?.enabled} aria-label="Enable puppet mode" disabled={!confirmed || pending || !pairState || (!pairState.enabled && pairState.mode !== 'ready')} onclick={toggle}><span></span></button></div>
  <button class="stop-control" onclick={stop}>STOP LEFT PAIR</button>
  {#if pairState?.limited?.length}
    <div class="limit-notice" role="status">{#each pairState.limited as limit}<p>{jointNames[limit.joint]}: requested {degrees(limit.requested)}, held at {degrees(limit.bounded)} ({limit.kind}). Other joints can still follow.</p>{/each}</div>
  {/if}
  {#if error || pairState?.error}<p class="error-banner" role="alert">{error || pairState.error}</p>{/if}
  <details class="limit-details"><summary>Controller joint limits — not a collision map</summary>
    {#each follower?.limits ?? [] as limit, index}<div class="limit-row"><span>{jointNames[index]}</span><span>{degrees(follower.joints[index])}</span><span>{degrees(limit.min)} to {degrees(limit.max)}</span></div>{/each}
  </details>
  <p class="notice">Stops on toggle off, modal close, browser focus loss, heartbeat loss, or 60-second timeout. This is not a certified emergency stop: a blocked process or SDK call can delay stopping. No force reflection or automatic home/reset.</p>
</dialog>
