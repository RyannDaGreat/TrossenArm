<script>
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
