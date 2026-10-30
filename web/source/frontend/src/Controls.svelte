<script>
  import { onMount } from 'svelte';
  import Stopwatch from './widgets/Stopwatch/Stopwatch.svelte';
  let unlimitedRequested = $state(false);
  let { state: leftState, rightState, presets, arms } = $props();
  let side = $state("left");
  let pairState = $derived(side === "left" ? leftState : rightState);
  let dialog;
  let confirmed = $state(false);
  let control = $state(null);
  let pending = $state(false);
  let error = $state('');
  let timer, sequence = 0, sending = false, generation = 0;
  const client = crypto.randomUUID();
  const heartbeatMs = 100, requestTimeoutMs = 1500;
  const jointNames = ['Base yaw', 'Shoulder', 'Elbow', 'Wrist pitch', 'Wrist yaw', 'Tool roll', 'Gripper'];
  const choices = [{ role: 'follower_left', title: 'Left follower up', number: '01' }, { role: 'follower_right', title: 'Right follower up', number: '02' }, { role: 'leader_left', title: 'Left leader up', number: '03' }, { role: 'leader_right', title: 'Right leader up', number: '04' }];
  let occupied = $derived(!!control || pending || !!leftState?.enabled || !!rightState?.enabled || !!presets?.role);
  let visibleState = $derived(presets?.role ? presets : pairState);

  /** Pure function. Convert radians to a degree label. @param {number} value Radians. @returns {string} @example degrees(Math.PI/2) // '90.0°' */
  function degrees(value) { return `${(value*180/Math.PI).toFixed(1)}°`; }

  /** Command. Queue ordered intent. @param {string} kind API control. @param {string} action Intent. @param {string} [role] Arm. @returns {Promise<object>} State. */
  async function send(kind, action, role) {
    const response = await fetch(`/api/${kind}`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(requestTimeoutMs), body: JSON.stringify({ action, role, ...(kind === "puppet" ? {side} : {}), client, sequence: ++sequence }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `Control HTTP ${response.status}`);
    return result;
  }

  /** Command. Report failure and expire local intent. @param {Error} failure Failure. @returns {void} */
  function fail(failure) { error = String(failure); console.error(failure); control = null; clearInterval(timer); }

  /** Command. Latch cancellation even while a start request is in flight. @returns {Promise<void>} */
  async function stop() {
    generation++;
    if (!control) side = rightState?.enabled ? 'right' : leftState?.enabled ? 'left' : side;
    const kind = control || (presets?.role ? 'presets' : pairState?.enabled ? 'puppet' : null);
    control = null; clearInterval(timer);
    if (kind) { try { await send(kind, 'stop'); } catch (failure) { fail(failure); } }
  }

  /** Command. Renew intent without overlapping requests. @returns {Promise<void>} */
  async function heartbeat() {
    if (!control || sending) return;
    sending = true;
    const kind = control;
    try {
      await send(kind, kind === 'puppet' && unlimitedRequested ? 'unlimited' : 'hold');
      unlimitedRequested = false;
    } catch (failure) {
      // Finishing a preset releases ownership before the next browser poll.
      if (kind === 'presets' && String(failure).includes('No running preset')) { control = null; clearInterval(timer); }
      else fail(failure);
    } finally { sending = false; }
  }

  /** Command. Start one selected mode; cancellation cannot revive a delayed response. @param {string} kind Control API. @param {string} [role] Arm. @param {string} [selectedSide] Pair to control. @returns {Promise<void>} */
  async function start(kind, role, selectedSide = side) {
    if (occupied || !confirmed) return;
    side = selectedSide;
    pending = true; error = ''; control = kind; unlimitedRequested = false;
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
      if (!control) side = rightState?.enabled ? 'right' : leftState?.enabled ? 'left' : side;
      const kind = control || (presets?.role ? 'presets' : pairState?.enabled ? 'puppet' : null);
      if (kind && !navigator.sendBeacon(`/api/${kind}`, new Blob([
        JSON.stringify({ action: 'stop', ...(kind === 'puppet' ? {side} : {}), client, sequence: ++sequence })
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
  <div class="control-state" class:active={visibleState?.active} role="status"><span>{presets?.role?.replaceAll('_', ' ') || `${side} puppet pair`} / {visibleState?.mode ?? 'connecting'}</span><span>{visibleState?.mode === 'stop_unconfirmed' ? 'USE PHYSICAL STOP' : visibleState?.active ? visibleState.unlimited ? 'No time limit' : `${Math.ceil(visibleState.remaining_s ?? 0)} seconds left` : visibleState?.stop_confirmed ? 'Idle confirmed' : 'Awaiting owner'}</span></div>
  <button class="stop-control" onclick={stop}>STOP MOVEMENT</button>
  <div class="switch-row"><div><strong>Workspace clear</strong><small>I can see the arm path and reach the physical power stop.</small></div>
    <button class="switch" role="switch" aria-checked={confirmed} aria-label="Confirm operator and workspace clearance" onclick={() => { confirmed = !confirmed; if (!confirmed) stop(); }}><span></span></button></div>
  <details class="preset-section" aria-label="Arm position presets">
    <summary class="section-title"><h3>Position presets</h3><span>4 arms / 8 seconds · expand</span></summary>
    <div class="preset-grid">
      {#each choices as choice}
        <button class="preset-card" disabled={!confirmed || occupied || !presets?.available?.includes(choice.role) || !arms?.[choice.role]?.ready} onclick={() => start('presets', choice.role)} aria-label={choice.title}>
          <span class="preset-index">{choice.number} / {choice.role.endsWith('left') ? 'LEFT' : 'RIGHT'}</span>
          <svg viewBox="0 0 160 150" aria-hidden="true"><path class="preset-guide" d="M25 125H135M80 15V120M70 25L80 15L90 25"/><path class="preset-arm" d="M55 125H105M80 125V96L69 63L80 36V21M71 13V21H89V13"/><circle cx="80" cy="96" r="5"/><circle cx="69" cy="63" r="5"/><circle cx="80" cy="36" r="4"/></svg>
          <strong>{choice.title} <span>↑</span></strong><small>Tall pose · keeps current heading</small>
        </button>
      {/each}
    </div>
    <p class="notice">Raises one selected arm with its tool pointing vertically up. Base yaw stays as it is; wrist yaw and tool roll reset to zero and the gripper opens. North is not calibrated in these presets.</p>
  </details>
  <section class="puppet-section" aria-label="Puppet mode">
    <div class="section-title"><h3>Puppet mode</h3><span>Choose left or right</span></div>
    <div class="preset-grid">
      {#each ['left', 'right'] as choice}
        {@const state = choice === 'left' ? leftState : rightState}
        {@const running = (control === 'puppet' && side === choice) || !!state?.enabled}
        <article class="preset-card puppet-card">
          <span class="preset-index">{choice.toUpperCase()} / LEADER → FOLLOWER</span>
          <svg viewBox="0 0 160 150" aria-hidden="true"><path class="preset-guide" d="M12 125H148M69 65H94M86 57L94 65L86 73"/><path class="preset-arm" d="M15 125H55M35 125V96L24 63L35 36V21M26 13V21H44V13M105 125H145M125 125V96L114 63L125 36V21M116 13V21H134V13"/><circle cx="35" cy="96" r="5"/><circle cx="24" cy="63" r="5"/><circle cx="125" cy="96" r="5"/><circle cx="114" cy="63" r="5"/></svg>
          <strong>Move the {choice} arm by hand.</strong>
          <small>Its follower copies all six joints and the gripper. Use Up on both {choice} arms first; base headings must match.</small>
          <div class="switch-row">
            <span>{running ? 'Following' : 'Enable puppet mode'}</span>
            {#if running}<Stopwatch remaining={state?.remaining_s ?? 60} unlimited={!!state?.unlimited} onclick={() => { unlimitedRequested = true; }} />{/if}
            <button class="switch" role="switch" aria-checked={running} aria-label={`Enable ${choice} puppet mode`} disabled={!confirmed || pending || (!running && (occupied || state?.mode !== 'ready'))} onclick={() => running ? stop() : start('puppet', undefined, choice)}><span></span></button>
          </div>
        </article>
      {/each}
    </div>
  </section>
  {#if pairState?.limited?.length}<div class="limit-notice" role="status">{#each pairState.limited as limit}<p>{jointNames[limit.joint]}: {limit.joint === 6 ? `${(limit.requested*1000).toFixed(1)} mm` : degrees(limit.requested)} requested, {limit.joint === 6 ? `${(limit.bounded*1000).toFixed(1)} mm` : degrees(limit.bounded)} held ({limit.kind}).</p>{/each}</div>{/if}
  {#if error || presets?.error || pairState?.error}<p class="error-banner" role="alert">{error || presets?.error || pairState?.error}</p>{/if}
  <details class="limit-details"><summary>Movement limits and stopping</summary>
    <p class="notice">Only one mode moves at a time. Closing this panel, leaving the page, losing focus or losing heartbeat stops movement. Click the stopwatch to remove the 60-second session limit. Puppet mode catches up at up to 29°/s and 20 mm/s gripper speed within controller limits. Presets use unchanged controller limits; tiny initial bound corrections up to 0.12° may occur.</p>
    {#each arms?.[`follower_${side}`]?.limits ?? [] as limit, index}<div class="limit-row"><span>{jointNames[index]}</span><span>{degrees(arms[`follower_${side}`].joints[index])}</span><span>{degrees(limit.min)} to {degrees(limit.max)}</span></div>{/each}
    <p class="notice">These limits do not detect obstacles. A blocked process or SDK call can delay stopping. Use the physical power stop if idle cannot be confirmed.</p>
  </details>
</dialog>
