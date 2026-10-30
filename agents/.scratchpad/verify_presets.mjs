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
try {
  const page = await browser.newPage();
  page.on('pageerror', error => { errors.push(String(error)); console.error(error); });
  await page.setRequestInterception(true);
  page.on('request', async request => {
    try {
      if (request.method() === 'POST') {
        assert(request.url().startsWith(base+'/api/'));
        const kind = request.url().split('/').at(-1);
        assert(['presets', 'puppet'].includes(kind));
        const body = JSON.parse(request.postData()); actions.push({kind,...body});
        if (kind === 'presets') {
          if (body.action === 'start') Object.assign(fake.presets, {role: body.role, mode:'moving', active:true, stop_confirmed:false, remaining_s:8});
          if (body.action === 'stop') Object.assign(fake.presets, {role:null, mode:'ready', active:false, stop_confirmed:true});
        } else {
          const pair = body.side === 'right' ? fake.puppet_right : fake.puppet;
          if (rejectRight && body.side === 'right' && body.action === 'hold') {
            Object.assign(pair, {enabled:false, active:false, mode:'ready', error:'Use Up on both right arms first: upright, wrists reset, grippers open'});
            await request.respond({status:409, contentType:'application/json', body:JSON.stringify({detail:'Puppet mode is not armed'})});
            return;
          }
          if (body.action === 'arm') Object.assign(pair, {enabled:true, active:true, mode:'active', remaining_s:60});
          if (body.action === 'unlimited') Object.assign(pair, {unlimited:true, remaining_s:null});
          if (body.action === 'stop') Object.assign(pair, {enabled:false, active:false, mode:'ready'});
        }
        await request.respond({status:200,contentType:'application/json',body:JSON.stringify(fake[kind])});
      } else if (request.url().endsWith('/api/status')) await request.respond({status:200,contentType:'application/json',body:JSON.stringify(fake)});
      else await request.continue();
    } catch (error) { errors.push(String(error)); console.error(error); await request.abort(); }
  });
  await page.goto(base, {waitUntil:'domcontentloaded'});
  await page.waitForFunction(() => window.__observatory.status?.presets);
  await page.click('.control-launch');
  assert.equal(await page.$$('article.puppet-card').then(cards => cards.length), 2);
  assert.equal(await page.$('select'), null);
  assert(await page.$eval('.puppet-section', e=>e.open));
  await page.click('.puppet-section summary');
  assert(!(await page.$eval('.puppet-section', e=>e.open)));
  await page.click('.puppet-section summary');
  assert(!(await page.$eval('.preset-section', e=>e.open)));
  await page.click('.preset-section summary');
  const left = '[aria-label="Left follower up"]', right = '[aria-label="Right follower up"]', puppet = '[aria-label="Enable left puppet mode"]';
  assert(await page.$eval(left, e=>e.disabled));
  await page.click('[aria-label="Confirm operator and workspace clearance"]');
  assert(!(await page.$eval(left,e=>e.disabled)));
  await page.screenshot({path:'agents/.scratchpad/presets-ui-desktop.png'});
  await page.click(left);
  await page.waitForFunction(() => window.__observatory.status.presets.role === 'follower_left');
  assert(await page.$eval(right,e=>e.disabled)); assert(await page.$eval(puppet,e=>e.disabled));
  await new Promise(resolve=>setTimeout(resolve,350));
  assert(actions.filter(x=>x.kind==='presets'&&x.action==='hold').length>=2);
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));
  await page.waitForFunction(() => window.__observatory.status.presets.role === null);
  await page.click(right);
  await page.waitForFunction(() => window.__observatory.status.presets.role === 'follower_right');
  await page.click('.stop-control');
  await page.waitForFunction(() => window.__observatory.status.presets.role === null);
  for (const [label, role] of [['Left leader up','leader_left'],['Right leader up','leader_right']]) {
    await page.click(`[aria-label="${label}"]`);
    await page.waitForFunction(role => window.__observatory.status.presets.role === role, {}, role);
    await page.click('.stop-control');
    await page.waitForFunction(() => window.__observatory.status.presets.role === null);
  }
  await page.click('.preset-section summary');
  assert(!(await page.$eval('.preset-section', e=>e.open)));
  await page.click('.preset-section summary');
  await page.click(puppet);
  await page.waitForFunction(() => window.__observatory.status.puppet.enabled);
  assert(await page.$eval(left,e=>e.disabled));
  assert(await page.$eval('[aria-label="Enable right puppet mode"]', e=>e.disabled));
  await page.click('[aria-label="Turn off puppet time limit"]');
  await page.waitForFunction(() => window.__observatory.status.puppet.unlimited);
  await page.waitForSelector('[aria-label="Puppet timer off — no time limit"]');
  await page.screenshot({path:'agents/.scratchpad/stopwatch-ui.png'});
  assert(actions.some(x => x.action === 'unlimited'));
  await page.click('[aria-label="Close robot controls"]');
  await page.waitForFunction(() => !window.__observatory.status.puppet.enabled);
  await page.click('.control-launch');
  await page.click('[aria-label="Confirm operator and workspace clearance"]');
  assert.equal(await page.$('select'), null);
  await page.click('[aria-label="Enable right puppet mode"]');
  await page.waitForFunction(() => window.__observatory.status.puppet_right.enabled);
  await page.click('[aria-label="Turn off puppet time limit"]');
  await page.waitForFunction(() => window.__observatory.status.puppet_right.unlimited);
  await page.click('.stop-control');
  await page.waitForFunction(() => !window.__observatory.status.puppet_right.enabled);
  assert(actions.some(x => x.kind === 'puppet' && x.side === 'right' && x.action === 'arm'));
  await page.click('[aria-label="Close robot controls"]');
  await page.setViewport({width:390,height:844});
  await page.evaluate(() => { document.querySelector(".preset-section").open = false; });
  await page.click('.control-launch');
  assert(await page.$eval('dialog', e => e.getBoundingClientRect().width <= innerWidth));
  await page.screenshot({path:'agents/.scratchpad/presets-ui-mobile.png'});
  assert(actions.every((x,i)=>i===0||x.sequence>actions[i-1].sequence));
  assert.equal(errors.length,0);
  await writeFile('agents/.scratchpad/presets-ui-results.json',JSON.stringify({actions,errors,hardwareCommands:0},null,2));
  console.log('PASS: illustrated presets, clearance gate, both arms, heartbeat, exclusive puppet mode, focus-loss stop, Stop, modal close, mobile fit. Every POST intercepted. No hardware/server startup.');
} finally { await browser.close(); await new Promise(resolve=>server.close(resolve)); }
