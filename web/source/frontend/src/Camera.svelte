<script>
  import { onMount } from 'svelte';
  let { role, stats } = $props();
  let canvas;
  let error = $state('');
  let drawn = $state(0);
  let age = $state(Infinity);

  onMount(() => {
    const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/camera/${role}`);
    socket.binaryType = 'arraybuffer';
    const times = [];
    let last = 0;
    let count = 0;
    let alive = true;
    socket.onmessage = async (event) => {
      try {
        if (typeof event.data === 'string') throw new Error(JSON.parse(event.data).error);
        const packet = new DataView(event.data);
        const sequence = packet.getBigUint64(0).toString();
        const image = await createImageBitmap(new Blob([event.data.slice(16)], { type: 'image/jpeg' }));
        await new Promise(resolve => requestAnimationFrame(resolve));
        if (!alive) { image.close(); return; }
        if (canvas.width !== image.width || canvas.height !== image.height) {
          canvas.width = image.width; canvas.height = image.height;
        }
        canvas.getContext('2d', { alpha: false }).drawImage(image, 0, 0);
        image.close();
        last = performance.now();
        times.push(last);
        while (times.length > 2 && last-times[0] > 3000) times.shift();
        count += 1;
        window.__observatory.streams[role] = { count, sequence, lastDraw: last, width: canvas.width, height: canvas.height };
        if (socket.readyState === WebSocket.OPEN) socket.send(sequence);
      } catch (failure) {
        error = String(failure);
        console.error(role, failure);
        window.__observatory.errors.push(`${role}: ${failure}`);
        socket.close();
      }
    };
    socket.onerror = () => { error = 'Stream connection failed'; };
    socket.onclose = () => { if (alive && !error) error = 'Stream disconnected'; };
    const timer = setInterval(() => {
      drawn = times.length > 1 ? (times.length-1)*1000/(times.at(-1)-times[0]) : 0;
      age = last ? performance.now()-last : Infinity;
    }, 500);
    return () => { alive = false; clearInterval(timer); socket.close(); };
  });
</script>

<article class="camera" class:failed={error || stats?.error || age > 1000}>
  <header><h2>{role} view</h2><span class="live">{age < 1000 && !error ? 'LIVE' : 'WAITING'}</span></header>
  <canvas bind:this={canvas} width="640" height="480" aria-label={`${role} live camera`}></canvas>
  <footer>
    <span>{(stats?.capture_fps ?? 0).toFixed(1)} capture / {drawn.toFixed(1)} draw fps</span>
    <span>{(stats?.ack_age_ms ?? 0).toFixed(0)} ms read→draw upper bound</span>
  </footer>
  <div class="identity">{stats?.device?.serial ?? 'Serial unavailable · session mapping'} · {stats?.error || error || '640 × 480 / latest frame only'}</div>
</article>
