<script>
  import { onMount } from 'svelte';
  import Camera from './Camera.svelte';
  import Arms from './Arms.svelte';
  import Controls from './Controls.svelte';
  let status = $state(null);
  let error = $state('');
  let updated = $state(0);
  const roles = ['top', 'bottom', 'left', 'right'];
  onMount(() => {
    let active = true;
    let timer;
    /** Command. Fetch one telemetry snapshot; never overlap requests. @returns {Promise<void>} @example poll() // updates status and schedules another read */
    async function poll() {
      try {
        const response = await fetch('/api/status', { cache: 'no-store' });
        if (!response.ok) throw new Error(`Status HTTP ${response.status}`);
        status = await response.json(); updated = Date.now(); error = '';
        window.__observatory.status = $state.snapshot(status);
      } catch (failure) {
        error = String(failure); console.error(failure);
      } finally {
        if (active) timer = setTimeout(poll, 50);
      }
    }
    poll();
    return () => { active = false; clearTimeout(timer); };
  });
</script>

<svelte:head><meta name="description" content="Four live robot cameras and encoder-driven WXAI geometry." /></svelte:head>
<header class="masthead">
  <div><p class="eyebrow">TROSSEN / LAB OBSERVATORY</p><h1>See what the robots see.</h1></div>
  <div class="connection"><strong>{error ? 'CONNECTION ERROR' : status ? 'LIVE SYSTEM' : 'CONNECTING'}</strong><span>Target 30 fps per camera · operator-held left-pair controls</span><Controls state={status?.puppet} follower={status?.arms?.follower_left} /></div>
</header>
{#if error}<p class="error-banner">{error} · Last update {updated ? new Date(updated).toLocaleTimeString() : 'none'}</p>{/if}
<main>
  <section class="camera-panel" aria-label="Four live cameras">
    <div class="section-title"><h2>01 / Camera array</h2><span>Actual capture + browser draw rates</span></div>
    <div class="camera-grid">
      {#each roles as role}<Camera {role} stats={status?.cameras?.[role]} />{/each}
    </div>
    <p class="notice">The delay figure is an upper bound from capture-read return to browser draw acknowledgement, not exposure-to-screen latency. Red cards indicate missing or stale frames. No recorded footage is substituted.</p>
  </section>
  <Arms arms={status?.arms} />
</main>
<footer class="page-footer"><span>WXAI / FOUR CAMERAS / FOUR ARMS</span><span>Futura system font; sans-serif if unavailable · No automatic startup motion</span></footer>
