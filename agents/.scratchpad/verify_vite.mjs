import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { writeFile } from 'node:fs/promises';
const require = createRequire(new URL('../../web/source/frontend/package.json', import.meta.url));
const puppeteer = require('puppeteer-core');
assert(process.env.CHROME_BIN, 'Set CHROME_BIN to the local Chrome executable');
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_BIN, headless: true,
  args: ['--enable-webgl', '--enable-unsafe-swiftshader'], defaultViewport: { width: 1600, height: 1100 } });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => { errors.push(String(error)); console.error(error); });
  page.on('console', message => { if (message.type() === 'error') console.error(message.text()); });
  await page.goto('http://127.0.0.1:43179', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Object.keys(window.__observatory.streams).length === 4 &&
    Object.values(window.__observatory.status?.arms ?? {}).filter(arm => arm.ready).length === 4,
    { timeout: 30000 });
  const start = await page.evaluate(() => ({ time: performance.now(), streams: structuredClone(window.__observatory.streams) }));
  console.log('All four camera canvases and all four arm models are live. Measuring 20 seconds.');
  await new Promise(resolve => setTimeout(resolve, 20000));
  const finish = await page.evaluate(() => ({ time: performance.now(), metrics: structuredClone(window.__observatory),
    canvases: [...document.querySelectorAll('canvas')].map(canvas => ({width: canvas.width, height: canvas.height})) }));
  const duration = (finish.time-start.time)/1000;
  const fps = Object.fromEntries(Object.entries(finish.metrics.streams).map(([role, value]) =>
    [role, (value.count-start.streams[role].count)/duration]));
  const result = { duration, drawn_fps: fps, cameras: finish.metrics.status.cameras,
    arms: Object.fromEntries(Object.entries(finish.metrics.status.arms).map(([role, value]) =>
      [role, {ready: value.ready, modes: value.modes, fk_error_m: value.fk_error_m}])),
    errors: [...errors, ...finish.metrics.errors], canvases: finish.canvases };
  console.log(JSON.stringify(result, null, 2));
  await writeFile('agents/.scratchpad/web-verification.json', JSON.stringify(result, null, 2)+'\n');
  await page.screenshot({ path: 'agents/.scratchpad/web-viewer.png', fullPage: true });
  assert.equal(result.errors.length, 0);
  assert.equal(result.canvases.length, 5);
  assert(Object.values(fps).every(value => value > 20), 'Basic streaming health below 20 draw fps; inspect measured rates');
  assert(Object.values(result.arms).every(value => value.fk_error_m < 0.005));
  console.log('PASS: four real camera feeds, four telemetry-driven models, no JS errors. See measured FPS for target compliance.');
} finally {
  await browser.close();
}
