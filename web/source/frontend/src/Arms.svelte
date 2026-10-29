<script>
  import { onMount } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
  let { arms } = $props();
  let host;
  const roles = ['leader_left', 'leader_right', 'follower_left', 'follower_right'];
  const colors = [0xcb3c26, 0xe3a339, 0x367c84, 0x3160a2];

  /** Pure function. Map robot XYZ to Three.js Y-up coordinates. @param {number[]} p XYZ. @returns {THREE.Vector3} @example xyz([1,2,3]) // Vector3(1,3,-2) */
  function xyz(p) { return new THREE.Vector3(p[0], p[2], -p[1]); }

  onMount(() => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xe9e7e0);
    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 20);
    camera.position.set(1.8, 1.65, 2.05);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    host.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.3, 0);
    controls.enableDamping = true;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x555555, 3));
    scene.add(new THREE.GridHelper(2.4, 24, 0x99968d, 0xccc8bf));
    const jointGeometry = new THREE.SphereGeometry(0.016, 12, 8);
    const displays = roles.map((role, index) => {
      const group = new THREE.Group();
      group.position.set(index % 2 ? 0.48 : -0.48, 0, index < 2 ? -0.45 : 0.45);
      scene.add(group);
      group.add(new THREE.AxesHelper(0.12));
      const material = new THREE.MeshStandardMaterial({ color: colors[index] });
      const points = Array.from({ length: 9 }, () => {
        const mesh = new THREE.Mesh(jointGeometry, material); group.add(mesh); return mesh;
      });
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(27), 3));
      const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: colors[index] }));
      group.add(line);
      const arrow = new THREE.ArrowHelper(new THREE.Vector3(1,0,0), new THREE.Vector3(), 0.13, colors[index]);
      group.add(arrow);
      return { role, group, points, geometry, arrow };
    });
    const resize = new ResizeObserver(() => {
      const { width, height } = host.getBoundingClientRect();
      renderer.setSize(width, height); camera.aspect = width/height; camera.updateProjectionMatrix();
    });
    resize.observe(host);
    let running = true;
    /** Command. Draw current telemetry in separate schematic base frames. @returns {void} @example draw() // schedules next screen frame */
    function draw() {
      if (!running) return;
      for (const display of displays) {
        const state = arms?.[display.role];
        display.group.visible = !!state?.ready && !state.error;
        if (!display.group.visible) continue;
        const attribute = display.geometry.getAttribute('position');
        state.points.forEach((p, index) => {
          const vector = xyz(p); display.points[index].position.copy(vector);
          attribute.setXYZ(index, vector.x, vector.y, vector.z);
        });
        attribute.needsUpdate = true;
        display.geometry.computeBoundingSphere();
        display.arrow.position.copy(xyz(state.points.at(-1)));
        display.arrow.setDirection(xyz([state.tool[0][0], state.tool[1][0], state.tool[2][0]]).normalize());
      }
      controls.update(); renderer.render(scene, camera); requestAnimationFrame(draw);
    }
    draw();
    return () => {
      running = false; resize.disconnect(); controls.dispose();
      scene.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
      renderer.dispose(); renderer.domElement.remove();
    };
  });
</script>

<section class="geometry-panel">
  <header><h2>Live kinematics</h2><span>DRAG TO ORBIT</span></header>
  <p class="notice">Four separate base frames. Layout is schematic—not a calibrated map of the room.</p>
  <div class="scene" bind:this={host} aria-label="Live 3D geometry for all four arms"></div>
  <div class="arm-list">
    {#each roles as role, index}
      <article class="arm" style={`--arm-color: var(--${role}-color)`}>
        <h3>{role.replaceAll('_', ' ')}</h3>
        {#if arms?.[role]?.ready}
          <div class="joint-values">{arms[role].joints.map(value => `${(value*180/Math.PI).toFixed(1)}°`).join(' / ')}</div>
          <small>{arms[role].modes.slice(0,6).every(mode => mode === 'idle') ? 'BRAKED / IDLE' : arms[role].modes.join(' · ')} · FK error {(arms[role].fk_error_m*1000).toFixed(3)} mm</small>
        {:else}<small class="error">{arms?.[role]?.error ?? 'Connecting controller…'}</small>{/if}
      </article>
    {/each}
  </div>
  <p class="notice">Model: official WXAI DH geometry. Arrow = tool +X. Encoders drive the model; controller XYZ checks the calculation. Physical base placement and camera extrinsics are not calibrated.</p>
</section>
