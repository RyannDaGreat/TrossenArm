import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
const require = createRequire(new URL('../../web/source/frontend/package.json', import.meta.url));
const puppeteer = require('puppeteer-core');
const root = resolve('web/source/frontend/dist');
const server = createServer(async (request, response) => {
  try {
    assert.equal(request.method, 'GET', 'Static test server must never receive motor POSTs');
    const file = resolve(root, `.${request.url === '/' ? '/index.html' : request.url}`);
    assert(file.startsWith(`${root}/`));
    const data = await readFile(file);
    response.setHeader('Content-Type', { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' }[extname(file)] || 'application/octet-stream');
    response.end(data);
  } catch (error) { console.log('Static fixture response:', error.message); response.statusCode = 404; response.end('fixture only'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true,
  args: ['--enable-webgl', '--enable-unsafe-swiftshader'], defaultViewport: { width: 1440, height: 1080 } });
const actions = [], errors = [];
let rejectRight = false;
const fake = { puppet: { mode: 'ready', enabled: false, active: false, stop_pending: false, stop_confirmed: true },
  presets: { mode: 'ready', role: null, active: false, stop_confirmed: true, available: ['follower_left', 'follower_right', 'leader_left', 'leader_right'] }, cameras: {}, arms: {} };
fake.puppet_right = {...fake.puppet};
for (const role of ['follower_left', 'follower_right', 'leader_left', 'leader_right']) fake.arms[role] = { ready: true, joints: [0,0,0,0,0,0], modes: Array(7).fill('idle'), fk_error_m: 0,
  points: Array.from({length:9}, (_,i) => [0,0,i/10]), tool: [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], limits: [] };
fake.presets.arms = Object.fromEntries(fake.presets.available.map(role => [role, {mode:'ready', role:null, active:false, stop_confirmed:true, remaining_s:0}]));
try {
  const page = await browser.newPage();
  page.on('pageerror', error => errors.push(String(error)));
  await page.setRequestInterception(true);
  page.on('request', async request => {
    if (request.method() === 'POST') {
      assert(request.url().startsWith(base+'/api/'));
      const kind = request.url().split('/').at(-1), body = JSON.parse(request.postData());
      actions.push({kind,...body});
      const state = kind === 'puppet' ? (body.side === 'left' ? fake.puppet : fake.puppet_right) : fake.presets.arms[body.role];
      assert(state, 'Every command must identify its channel');
      if (body.action === 'arm') Object.assign(state,{mode:'active',active:true,enabled:true,remaining_s:60});
      if (body.action === 'start') Object.assign(state,{mode:'moving',active:true,role:body.role,remaining_s:4});
      if (body.action === 'unlimited') Object.assign(state,{unlimited:true,remaining_s:null});
      if (body.action === 'stop') Object.assign(state,{mode:'ready',active:false,enabled:false,role:null,stop_confirmed:true});
      await request.respond({status:200,contentType:'application/json',body:JSON.stringify(state)});
    } else if (request.url().endsWith('/api/status')) await request.respond({status:200,contentType:'application/json',body:JSON.stringify(fake)});
    else await request.continue();
  });
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(() => window.__observatory.status?.presets?.arms);
  await page.click('.control-launch');
  await page.click('[aria-label="Confirm operator and workspace clearance"]');
  await page.click('[aria-label="Enable left puppet mode"]');
  await page.waitForFunction(() => window.__observatory.status.puppet.enabled);
  assert(!(await page.$eval('[aria-label="Enable right puppet mode"]', e=>e.disabled)));
  await page.click('[aria-label="Enable right puppet mode"]');
  await page.waitForFunction(() => window.__observatory.status.puppet_right.enabled);
  assert.equal(await page.$$eval('.puppet-card [role="switch"][aria-checked="true"]', es=>es.length),2);
  await page.click('.puppet-card:first-child [aria-label="Turn off puppet time limit"]');
  await page.waitForFunction(() => window.__observatory.status.puppet.unlimited);
  assert(!fake.puppet_right.unlimited);
  await page.click('[aria-label="Enable left puppet mode"]');
  await page.waitForFunction(() => !window.__observatory.status.puppet.enabled && window.__observatory.status.puppet_right.enabled);
  const rightHolds = actions.filter(a=>a.side==='right'&&a.action==='hold').length;
  await new Promise(resolve=>setTimeout(resolve,350));
  assert(actions.filter(a=>a.side==='right'&&a.action==='hold').length>rightHolds);
  await page.click('.stop-control');
  await page.waitForFunction(() => !window.__observatory.status.puppet_right.enabled);
  await page.click('.preset-section summary');
  const labels = ['Left follower up','Right follower up','Left leader up','Right leader up'];
  for (const label of labels) await page.click(`[aria-label="${label}"]`);
  await page.waitForFunction(() => Object.values(window.__observatory.status.presets.arms).every(s=>s.active));
  assert.equal(await page.$$eval('progress',es=>es.length),4);
  assert(await page.$$eval('progress',es=>es.every(e=>e.value===4&&e.max===8)));
  assert(await page.$eval('[aria-label="Enable left puppet mode"]', e=>e.disabled));
  await page.screenshot({path:'agents/.scratchpad/independent-controls.png',fullPage:true});
  await page.click('[aria-label="Stop Left follower up"]');
  await page.waitForFunction(() => !window.__observatory.status.presets.arms.follower_left.active);
  assert(fake.presets.arms.follower_right.active && fake.presets.arms.leader_left.active && fake.presets.arms.leader_right.active);
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));
  await page.waitForFunction(() => Object.values(window.__observatory.status.presets.arms).every(s=>!s.active));
  for (const key of ['left','right',...fake.presets.available]) {
    const channel = actions.filter(a=>(a.side||a.role)===key);
    assert(channel.every((a,i)=>i===0||a.sequence>channel[i-1].sequence));
    assert.equal(new Set(channel.map(a=>a.client)).size,1);
  }
  assert.equal(new Set(actions.map(a=>a.client)).size,6);
  assert.deepEqual(errors,[]);
  console.log('PASS: both puppet pairs, independent timers/stops, four simultaneous Up cards/progress, overlap exclusion, global blur stop, six ordered clients. All motor POSTs intercepted.');
} finally { await browser.close(); await new Promise(resolve=>server.close(resolve)); }
