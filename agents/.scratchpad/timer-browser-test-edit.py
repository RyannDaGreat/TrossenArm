from pathlib import Path
p=Path('agents/.scratchpad/verify_presets.mjs');s=p.read_text().replace("if (body.action === 'stop') Object.assign(fake.puppet", "if (body.action === 'unlimited') Object.assign(fake.puppet, {unlimited:true, remaining_s:null});\n          if (body.action === 'stop') Object.assign(fake.puppet")
s=s.replace("  assert(await page.$eval(left,e=>e.disabled));\n  await page.click('[aria-label=\"Close robot controls\"]');",'''  assert(await page.$eval(left,e=>e.disabled));
  await page.click('[aria-label="Turn off puppet time limit"]');
  await page.waitForFunction(() => window.__observatory.status.puppet.unlimited);
  await page.waitForSelector('[aria-label="Puppet timer off — no time limit"]');
  await page.screenshot({path:'agents/.scratchpad/stopwatch-ui.png'});
  assert(actions.some(x => x.action === 'unlimited'));
  await page.click('[aria-label="Close robot controls"]');''')
p.write_text(s)
