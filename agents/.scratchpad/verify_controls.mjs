import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { writeFile } from 'node:fs/promises';
const require = createRequire(new URL('../../web/source/frontend/package.json', import.meta.url));
const puppeteer = require('puppeteer-core');
assert(process.env.CHROME_BIN);
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_BIN, headless: true,
  args: ['--enable-webgl', '--enable-unsafe-swiftshader'], defaultViewport: { width: 1600, height: 1100 } });
const actions = [];
const errors = [];
const fake = { mode: 'ready', enabled: false, active: false, error: null, remaining_s: 60 };
try {
  const page = await browser.newPage();
  page.on('pageerror', error => { errors.push(String(error)); console.error(error); });
  await page.setRequestInterception(true);
  page.on('request', async request => {
    try {
      if (request.url().endsWith('/api/puppet')) {
        const body = JSON.parse(request.postData()); actions.push(body);
        if (body.action === 'arm') fake.enabled = true;
        if (body.action === 'hold') { fake.active = true; fake.mode = 'active'; }
        if (['stop', 'disarm'].includes(body.action)) { fake.enabled = false; fake.active = false; fake.mode = 'ready'; }
        await request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(fake) });
      } else if (request.url().endsWith('/api/status')) {
        const status = await (await fetch(request.url())).json();
        status.puppet = { ...fake };
        await request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(status) });
      } else await request.continue();
    } catch (error) { errors.push(String(error)); console.error(error); await request.abort(); }
  });
  await page.goto('http://127.0.0.1:28347', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__observatory.status?.puppet?.mode === 'ready');
  await page.click('.control-launch');
  const enable = '[aria-label="Enable puppet mode"]';
  assert(await page.$eval(enable, element => element.disabled));
  await page.click('[aria-label="Confirm operator and workspace clearance"]');
  assert(!(await page.$eval(enable, element => element.disabled)));
  await page.click(enable);
  await page.waitForFunction(() => document.querySelector('[aria-label="Enable puppet mode"]').getAttribute('aria-checked') === 'true');
  await new Promise(resolve => setTimeout(resolve, 450));
  assert(fake.active, 'Toggle should follow without holding a mouse button');
  await page.click('.stop-control');
  await page.waitForFunction(() => document.querySelector('[aria-label="Enable puppet mode"]').getAttribute('aria-checked') === 'false');
  assert(actions.filter(action => action.action === 'hold').length >= 2);
  assert.equal(actions.at(-1).action, 'stop');
  assert(actions.every((action, index) => index === 0 || action.sequence > actions[index-1].sequence));
  await page.screenshot({ path: 'agents/.scratchpad/web-controls.png', fullPage: true });
  assert.equal(errors.length, 0);
  console.log('PASS: themed modal, workspace gate, latched toggle, automatic heartbeat, monotonic sequence, explicit stop. ALL CONTROL POSTS MOCKED; NO MOTION.');
  await writeFile('agents/.scratchpad/puppet-ui-verification.json', JSON.stringify({ actions, errors, hardwareCommands: 0 }, null, 2)+'\n');
} finally { await browser.close(); }
