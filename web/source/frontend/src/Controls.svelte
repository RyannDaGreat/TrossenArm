<script>
  import { onMount } from 'svelte';
  import Stopwatch from './widgets/Stopwatch/Stopwatch.svelte';
  let { state: leftState, rightState, presets, arms } = $props();
  let dialog;
  let confirmed = $state(false);
  const jointNames = ['Base yaw', 'Shoulder', 'Elbow', 'Wrist pitch', 'Wrist yaw', 'Tool roll', 'Gripper'];
  const heartbeatMs = 100, requestTimeoutMs = 1500;
  const choices = [{ role: 'follower_left', title: 'Left follower up', number: '01' }, { role: 'follower_right', title: 'Right follower up', number: '02' }, { role: 'leader_left', title: 'Left leader up', number: '03' }, { role: 'leader_right', title: 'Right leader up', number: '04' }];
  const keys = ['left', 'right', ...choices.map(choice => choice.role)];
  let sessions = $state(Object.fromEntries(keys.map(key => [key, { running: false, pending: false, error: '', unlimited: false }])));
  const transport = Object.fromEntries(keys.map(key => [key, { client: crypto.randomUUID(), sequence: 0, generation: 0, sending: false, timer: null }]));
  let independent = $derived(!!presets?.arms);

  /** Query. Read the server state belonging to a single control channel. */
  function stateFor(key) { return key === 'left' ? leftState : key === 'right' ? rightState : presets?.arms?.[key]; }
  /** Query. Include unconfirmed stops and requests still in flight in reservations. */
  function busy(key) { const state = stateFor(key); return sessions[key].running || sessions[key].pending || !!state?.enabled || !!state?.role || !!state?.stop_pending || state?.active === true || state?.active === null; }
  /** Query. Disable only channels that would overlap the requested physical arms. */
  function blocked(key) {
    if (!independent || !confirmed || busy(key)) return true;
    if (key === 'left' || key === 'right') return busy(`leader_${key}`) || busy(`follower_${key}`) || stateFor(key)?.mode !== 'ready';
    return busy(key.split('_')[1]) || !presets?.available?.includes(key) || !arms?.[key]?.ready;
  }
  /** Query. Build intent with immutable channel identity and monotonic ordering. */
  function body(key, action) {
    const channel = transport[key];
    return { action, client: channel.client, sequence: ++channel.sequence, ...(key.includes('_') ? {role:key} : {side:key}) };
  }
  /** Query. Select the endpoint from the channel, never from the last clicked card. */
  function endpoint(key) { return `/api/${key.includes('_') ? 'presets' : 'puppet'}`; }
  /** Command. Send one channel's intent and preserve the original rejection reason. */
  async function send(key, action) {
    const response = await fetch(endpoint(key), {method:'POST', headers:{'Content-Type':'application/json'}, signal:AbortSignal.timeout(requestTimeoutMs), body:JSON.stringify(body(key, action))});
    const result = await response.json();
    if (!response.ok) {
      let reason = result.detail;
      if (reason === 'Puppet mode is not armed') {
        const statusResponse = await fetch('/api/status', {signal:AbortSignal.timeout(requestTimeoutMs)});
        if (statusResponse.ok) {
          const status = await statusResponse.json();
          reason = (key === 'right' ? status.puppet_right : status.puppet)?.error || 'Following stopped. Use Up on both arms, wait for them to stop, then enable this pair again.';
        }
      }
      throw new Error(reason || `Control request failed (${response.status})`);
    }
    return result;
  }
  /** Command. Expire only this channel; peer heartbeats remain live. */
  function release(key) { sessions[key].running = false; clearInterval(transport[key].timer); }
  /** Command. Stop one channel, including cancellation of an in-flight start. */
  async function stopOne(key) {
    const needed = busy(key);
    transport[key].generation++;
    release(key);
    if (needed) { try { await send(key, 'stop'); } catch (failure) { sessions[key].error = String(failure.message); } }
  }
  /** Command. Stop every channel concurrently so a slow peer cannot block another stop. */
  async function stop() { await Promise.all(keys.map(stopOne)); }
  /** Command. Renew a single channel, without overlapping that channel's requests. */
  async function heartbeat(key) {
    const channel = transport[key], session = sessions[key], token = channel.generation;
    if (!session.running || channel.sending) return;
    channel.sending = true;
    try {
      await send(key, session.unlimited ? 'unlimited' : 'hold');
      if (channel.generation === token) session.unlimited = false;
    } catch (failure) {
      if (channel.generation !== token) return;
      release(key);
      if (!key.includes('_') || !String(failure.message).includes('No running preset')) session.error = failure.message;
    } finally { channel.sending = false; }
  }
  /** Command. Start a named channel; delayed responses cannot revive cancelled intent. */
  async function start(key) {
    if (blocked(key)) return;
    const channel = transport[key], session = sessions[key], token = ++channel.generation;
    session.pending = true; session.running = true; session.error = ''; session.unlimited = false;
    try {
      await send(key, key.includes('_') ? 'start' : 'arm');
      if (channel.generation !== token) { await send(key, 'stop'); return; }
      await heartbeat(key);
      if (session.running && channel.generation === token) channel.timer = setInterval(() => heartbeat(key), heartbeatMs);
    } catch (failure) { if (channel.generation === token) { session.error = failure.message; release(key); } }
    finally { session.pending = false; }
  }
  /** Command. Reconnect an exited owner; this never enables following. */
  async function reconnect(key) {
    release(key); sessions[key].error = ''; sessions[key].pending = true;
    try { await send(key, 'reconnect'); }
    catch (failure) { sessions[key].error = failure.message; }
    finally { sessions[key].pending = false; }
  }
  /** Command. Require a fresh acknowledgement when opening controls. */
  function open() { confirmed = false; dialog.showModal(); }
  /** Command. Stop all channels before closing. */
  async function close() { await stop(); dialog.close(); }
  onMount(() => {
    /** Command. Queue per-channel stop beacons; independent heartbeat deadlines remain active. */
    function leaving() {
      for (const key of keys) {
        const needed = busy(key);
        transport[key].generation++; release(key);
        if (needed && !navigator.sendBeacon(endpoint(key), new Blob([JSON.stringify(body(key,'stop'))], {type:'application/json'}))) console.error(`Stop for ${key} could not be queued; heartbeat expiry remains active`);
      }
    }
    window.addEventListener('pagehide', leaving); window.addEventListener('blur', stop);
    return () => { leaving(); window.removeEventListener('pagehide', leaving); window.removeEventListener('blur', stop); };
  });
</script>


<button class="control-launch" onclick={open}>Robot controls <span>↗</span></button>
<dialog bind:this={dialog} class="control-modal" oncancel={(event) => { event.preventDefault(); close(); }}>
  <header><div><p class="eyebrow">TROSSEN / OPERATOR CONTROL</p><h2>Choose a movement.</h2></div><button class="icon-button" onclick={close} aria-label="Close robot controls">×</button></header>
  <div class="control-state" role="status"><span>Independent arm controls</span><span>{keys.filter(busy).length} in use</span></div>
  {#if !independent}<p class="notice">Independent controls are prepared but the running controller has not been updated yet.</p>{/if}
  <button class="stop-control" onclick={stop}>STOP MOVEMENT</button>
  <div class="switch-row"><div><strong>Workspace clear</strong><small>I can see the arm path and reach the physical power stop.</small></div>
    <button class="switch" role="switch" aria-checked={confirmed} aria-label="Confirm operator and workspace clearance" onclick={() => { confirmed = !confirmed; if (!confirmed) stop(); }}><span></span></button></div>
  <details class="preset-section" aria-label="Arm position presets">
    <summary class="section-title"><h3>Position presets</h3><span>4 arms / 8 seconds <span class="section-chevron" aria-hidden="true">›</span></span></summary>
    <div class="preset-grid">
      {#each choices as choice}
        <div class="arm-preset">
        <button class="preset-card" class:moving={busy(choice.role)} disabled={blocked(choice.role)} onclick={() => start(choice.role)} aria-label={choice.title}>
          <span class="preset-index">{choice.number} / {choice.role.endsWith('left') ? 'LEFT' : 'RIGHT'}</span>
          <svg viewBox="0 0 160 150" aria-hidden="true"><path class="preset-guide" d="M25 125H135M80 15V120M70 25L80 15L90 25"/><path class="preset-arm" d="M55 125H105M80 125V96L69 63L80 36V21M71 13V21H89V13"/><circle cx="80" cy="96" r="5"/><circle cx="69" cy="63" r="5"/><circle cx="80" cy="36" r="4"/></svg>
          <strong>{choice.title} <span>↑</span></strong><small>Tall pose · {stateFor(choice.role)?.heading?.startsWith('Align') ? 'aligns pair bases' : 'keeps current heading'}</small>
          {#if busy(choice.role)}<progress max="8" value={Math.max(0, 8-(stateFor(choice.role)?.remaining_s ?? 8))} aria-label={`${choice.title} progress`}></progress><small>{stateFor(choice.role)?.mode === 'stopping' ? 'Stopping…' : `${Math.ceil(stateFor(choice.role)?.remaining_s ?? 8)} seconds remaining`}</small>{/if}
        </button>
        {#if busy(choice.role)}<button class="arm-stop" onclick={() => stopOne(choice.role)} aria-label={`Stop ${choice.title}`}>Stop this arm</button>{/if}
        {#if sessions[choice.role].error || stateFor(choice.role)?.error}<p class="error-banner" role="alert">{sessions[choice.role].error || stateFor(choice.role)?.error}</p>{/if}
        </div>
      {/each}
    </div>
    <p class="notice">Raises one selected arm with its tool pointing vertically up. Up sets the verified north base heading, resets wrist yaw and tool roll, and opens the gripper.</p>
  </details>
  <details class="puppet-section" aria-label="Puppet mode" open>
    <summary class="section-title"><h3>Puppet mode</h3><span>Choose left or right <span class="section-chevron" aria-hidden="true">›</span></span></summary>
    <div class="preset-grid">
      {#each ['left', 'right'] as choice}
        {@const state = choice === 'left' ? leftState : rightState}
        {@const running = sessions[choice].running || !!state?.enabled}
        <article class="preset-card puppet-card">
          <span class="preset-index">{choice.toUpperCase()} / LEADER → FOLLOWER</span>
          <svg viewBox="0 0 160 150" aria-hidden="true"><path class="preset-guide" d="M12 125H148M69 65H94M86 57L94 65L86 73"/><path class="preset-arm" d="M15 125H55M35 125V96L24 63L35 36V21M26 13V21H44V13M105 125H145M125 125V96L114 63L125 36V21M116 13V21H134V13"/><circle cx="35" cy="96" r="5"/><circle cx="24" cy="63" r="5"/><circle cx="125" cy="96" r="5"/><circle cx="114" cy="63" r="5"/></svg>
          <strong>Move the {choice} arm by hand.</strong>
          <small>Its follower copies all six joints and the gripper. Use Up on both {choice} arms first; base headings must match.</small>
          <div class="switch-row">
            <span>{running ? 'Following' : 'Enable puppet mode'}</span>
            {#if running}<Stopwatch remaining={state?.remaining_s ?? 60} unlimited={!!state?.unlimited} onclick={() => { sessions[choice].unlimited = true; }} />{/if}
            <button class="switch" role="switch" aria-checked={running} aria-label={`Enable ${choice} puppet mode`} disabled={!running && blocked(choice)} onclick={() => running ? stopOne(choice) : start(choice)}><span></span></button>
          </div>
          {#if running && state?.limited?.length}<div class="limit-notice" role="status">{#each state.limited as limit}<p>{jointNames[limit.joint]}: requested {(limit.requested*(limit.joint === 6 ? 1000 : 180/Math.PI)).toFixed(limit.joint === 6 ? 3 : 1)}{limit.joint === 6 ? ' mm' : '°'}, held at {(limit.bounded*(limit.joint === 6 ? 1000 : 180/Math.PI)).toFixed(limit.joint === 6 ? 3 : 1)}{limit.joint === 6 ? ' mm' : '°'} ({limit.kind}).</p>{/each}</div>{/if}
          {#if sessions[choice].error || state?.error}<p class="error-banner" role="alert">{state?.error || sessions[choice].error}</p>{/if}
          {#if state?.can_reconnect}<button class="arm-stop" disabled={sessions[choice].pending} onclick={() => reconnect(choice)}>Reconnect {choice} arms</button>{/if}
          {#if sessions[choice].error && state?.mode === 'ready' && !state?.stop_pending}<button class="arm-stop" onclick={() => { sessions[choice].error = ''; }}>Dismiss message</button>{/if}
        </article>
      {/each}
    </div>
  </details>
  <details class="limit-details"><summary>Movement limits and stopping</summary>
    <p class="notice">Both puppet pairs can follow at once. Up moves are independent; stop the matching puppet pair before raising either of its arms. Each card stops its own movement. STOP MOVEMENT, closing this panel, leaving the page, or losing focus stops all channels. Each channel also stops when its browser heartbeat expires.</p>
    <p class="notice">Click a pair’s stopwatch to remove its 60-second session limit. Puppet mode approaches your hand position at up to 29°/s and 20 mm/s gripper speed, within controller limits. Up resets the wrists and opens the gripper. {presets?.arms?.follower_right?.heading?.startsWith('Align') ? 'It also sets matching base angles for each pair.' : 'The running controller still preserves base heading; Up cannot correct a base mismatch until the controller update is loaded.'}</p>
    <p class="notice">These controls do not detect obstacles. Use the physical power stop if idle cannot be confirmed.</p>
  </details>
</dialog>
