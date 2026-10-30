<script>
  import { onMount } from 'svelte';
  let { state: pairState, presets, arms } = $props();
  let dialog;
  let confirmed = $state(false);
  let control = $state(null);
  let pending = $state(false);
  let error = $state('');
  let timer, sequence = 0, sending = false, generation = 0;
  const client = crypto.randomUUID();
  const heartbeatMs = 100, requestTimeoutMs = 1500;
  const jointNames = ['Base yaw', 'Shoulder', 'Elbow', 'Wrist pitch', 'Wrist yaw', 'Tool roll'];
  const choices = [{ role: 'follower_left', title: 'Left arm up', number: '01' }, { role: 'follower_right', title: 'Right arm up', number: '02' }];
  let occupied = $derived(!!control || pending || !!pairState?.enabled || !!presets?.role);
  let visibleState = $derived(presets?.role ? presets : pairState);

  /** Pure function. Convert radians to a degree label. @param {number} value Radians. @returns {string} @example degrees(Math.PI/2) // '90.0°' */
  function degrees(value) { return `${(value*180/Math.PI).toFixed(1)}°`; }

  /** Command. Queue ordered intent. @param {string} kind API control. @param {string} action Intent. @param {string} [role] Follower. @returns {Promise<object>} State. */
  async function send(kind, action, role) {
    const response = await fetch(`/api/${kind}`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(requestTimeoutMs), body: JSON.stringify({ action, role, client, sequence: ++sequence }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `Control HTTP ${response.status}`);
    return result;
  }

  /** Command. Report failure and expire local intent. @param {Error} failure Failure. @returns {void} */
  function fail(failure) { error = String(failure); console.error(failure); control = null; clearInterval(timer); }

  /** Command. Latch cancellation even while a start request is in flight. @returns {Promise<void>} */
  async function stop() {
    generation++;
    const kind = control || (presets?.role ? 'presets' : pairState?.enabled ? 'puppet' : null);
    control = null; clearInterval(timer);
    if (kind) { try { await send(kind, 'stop'); } catch (failure) { fail(failure); } }
  }

  /** Command. Renew intent without overlapping requests. @returns {Promise<void>} */
  async function heartbeat() {
    if (!control || sending) return;
    sending = true;
    const kind = control;
    try { await send(kind, 'hold'); } catch (failure) {
      // Finishing a preset releases ownership before the next browser poll.
      if (kind === 'presets' && String(failure).includes('No running preset')) { control = null; clearInterval(timer); }
      else fail(failure);
    } finally { sending = false; }
  }

  /** Command. Start one selected mode; cancellation cannot revive a delayed response. @param {string} kind Control API. @param {string} [role] Follower. @returns {Promise<void>} */
  async function start(kind, role) {
    if (occupied || !confirmed) return;
    pending = true; error = ''; control = kind;
    const token = ++generation;
    try {
      await send(kind, kind === 'presets' ? 'start' : 'arm', role);
      if (generation !== token) { await send(kind, 'stop'); return; }
      await heartbeat();
      if (control && generation === token) timer = setInterval(heartbeat, heartbeatMs);
    } catch (failure) { fail(failure); }
    finally { pending = false; }
  }

  /** Command. Open controls with a fresh operator acknowledgement. @returns {void} */
  function open() { confirmed = false; error = ''; dialog.showModal(); }
  /** Command. Stop before closing controls. @returns {Promise<void>} */
  async function close() { await stop(); dialog.close(); }

  onMount(() => {
    /** Command. Queue stop on page exit; server heartbeat remains independent. @returns {void} */
    function leaving() {
      generation++;
      const kind = control || (presets?.role ? 'presets' : pairState?.enabled ? 'puppet' : null);
      if (kind && !navigator.sendBeacon(`/api/${kind}`, new Blob([
        JSON.stringify({ action: 'stop', client, sequence: ++sequence })
      ], { type: 'application/json' }))) console.error('Exit stop was not queued; heartbeat timeout remains active');
      control = null; clearInterval(timer);
    }
    window.addEventListener('pagehide', leaving);
    window.addEventListener('blur', stop);
    return () => { leaving(); window.removeEventListener('pagehide', leaving); window.removeEventListener('blur', stop); };
  });
</script>

<button class="control-launch" onclick={open}>Robot controls <span>↗</span></button>
<dialog bind:this={dialog} class="control-modal" oncancel={(event) => { event.preventDefault(); close(); }}>
  <header><div><p class="eyebrow">TROSSEN / OPERATOR CONTROL</p><h2>Choose a movement.</h2></div><button class="icon-button" onclick={close} aria-label="Close robot controls">×</button></header>
  <div class="control-state" class:active={visibleState?.active} role="status"><span>{presets?.role?.replaceAll('_', ' ') || 'Left puppet pair'} / {visibleState?.mode ?? 'connecting'}</span><span>{visibleState?.mode === 'stop_unconfirmed' ? 'USE PHYSICAL STOP' : visibleState?.active ? `${Math.ceil(visibleState.remaining_s ?? 0)} seconds left` : visibleState?.stop_confirmed ? 'Idle confirmed' : 'Awaiting owner'}</span></div>
  <button class="stop-control" onclick={stop}>STOP MOVEMENT</button>
  <div class="switch-row"><div><strong>Workspace clear</strong><small>I can see the arm path and reach the physical power stop.</small></div>
    <button class="switch" role="switch" aria-checked={confirmed} aria-label="Confirm operator and workspace clearance" onclick={() => { confirmed = !confirmed; if (!confirmed) stop(); }}><span></span></button></div>
  <section class="preset-section" aria-label="Arm position presets">
    <div class="section-title"><h3>Position presets</h3><span>Followers / 8 seconds</span></div>
    <div class="preset-grid">
      {#each choices as choice}
        <button class="preset-card" disabled={!confirmed || occupied || !presets?.available?.includes(choice.role) || !arms?.[choice.role]?.ready} onclick={() => start('presets', choice.role)} aria-label={choice.title}>
          <span class="preset-index">{choice.number} / {choice.role === 'follower_left' ? 'LEFT' : 'RIGHT'}</span>
          <svg viewBox="0 0 160 150" aria-hidden="true"><path class="preset-guide" d="M25 125H135M80 15V120M70 25L80 15L90 25"/><path class="preset-arm" d="M55 125H105M80 125V96L69 63L80 36V21M71 13V21H89V13"/><circle cx="80" cy="96" r="5"/><circle cx="69" cy="63" r="5"/><circle cx="80" cy="36" r="4"/></svg>
          <strong>{choice.title} <span>↑</span></strong><small>Tall pose · keeps current heading</small>
        </button>
      {/each}
    </div>
    <p class="notice">Raises one follower with its tool pointing vertically up. Base yaw and tool roll stay as they are. North is not calibrated in these presets.</p>
  </section>
  <section class="puppet-section" aria-label="Puppet mode">
    <div class="switch-row"><div><p class="eyebrow">03 / PUPPET MODE</p><strong>Move the left arm by hand.</strong><small>Leader left .3 → follower left .5. Relative motion, grippers idle.</small></div>
      <button class="switch" role="switch" aria-checked={control === 'puppet' || !!pairState?.enabled} aria-label="Enable puppet mode" disabled={!confirmed || pending || !!presets?.role || control === 'presets' || !pairState || (!pairState.enabled && pairState.mode !== 'ready')} onclick={() => control === 'puppet' || pairState?.enabled ? stop() : start('puppet')}><span></span></button></div>
  </section>
  {#if pairState?.limited?.length}<div class="limit-notice" role="status">{#each pairState.limited as limit}<p>{jointNames[limit.joint]}: {degrees(limit.requested)} requested, {degrees(limit.bounded)} held ({limit.kind}).</p>{/each}</div>{/if}
  {#if error || presets?.error || pairState?.error}<p class="error-banner" role="alert">{error || presets?.error || pairState?.error}</p>{/if}
  <details class="limit-details"><summary>Movement limits and stopping</summary>
    <p class="notice">Only one mode moves at a time. Closing this panel, leaving the page, losing focus or losing heartbeat stops movement. Puppet mode ends after 60 seconds and is capped at ±14° from engagement and 14°/s. Presets use unchanged controller limits; tiny initial bound corrections up to 0.12° may occur.</p>
    {#each arms?.follower_left?.limits ?? [] as limit, index}<div class="limit-row"><span>{jointNames[index]}</span><span>{degrees(arms.follower_left.joints[index])}</span><span>{degrees(limit.min)} to {degrees(limit.max)}</span></div>{/each}
    <p class="notice">These limits do not detect obstacles. A blocked process or SDK call can delay stopping. Use the physical power stop if idle cannot be confirmed.</p>
  </details>
</dialog>
