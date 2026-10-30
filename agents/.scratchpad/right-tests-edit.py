from pathlib import Path
p=Path('web/source/backend/presets.py');s=p.read_text().replace('            if action == "start":\n                pair', '            if action == "start":\n                if role not in ROLES:\n                    raise ValueError("Unknown arm role")\n                pair');p.write_text(s)
p=Path('agents/.scratchpad/presets_offline_test.py');s=p.read_text().replace("hub.pair.set_state(mode='ready')", "hub.pair.set_state(mode='ready')\n        hub.right_pair.set_state(mode='ready')");p.write_text(s)
p=Path('agents/.scratchpad/test_control_api.py');s=p.read_text().replace('            pair.request.side_effect = ValueError("Pair not ready")','''            with patch.object(server.hub, 'right_pair') as right:
                right.snapshot.return_value = {'mode':'ready'}
                response = await client.post('/api/puppet',json={**body,'side':'right'},headers={'Origin':'http://127.0.0.1:28347'})
                assert response.status_code == 200
                right.request.assert_called_once_with('arm','offline-client',1)
            pair.request.side_effect = ValueError("Pair not ready")''');p.write_text(s)
p=Path('agents/.scratchpad/verify_presets.mjs');s=p.read_text().replace('for (const role of [', 'fake.puppet_right = {...fake.puppet};\nfor (const role of [',1)
s=s.replace("        } else {\n          if (body.action", "        } else {\n          const pair = body.side === 'right' ? fake.puppet_right : fake.puppet;\n          if (body.action").replace('Object.assign(fake.puppet,','Object.assign(pair,')
s=s.replace("  await page.setViewport({width:390,height:844});",'''  await page.click('.control-launch');
  await page.click('[aria-label="Confirm operator and workspace clearance"]');
  await page.select('[aria-label="Puppet arm pair"]','right');
  await page.click(puppet);
  await page.waitForFunction(() => window.__observatory.status.puppet_right.enabled);
  await page.click('[aria-label="Turn off puppet time limit"]');
  await page.waitForFunction(() => window.__observatory.status.puppet_right.unlimited);
  await page.click('.stop-control');
  await page.waitForFunction(() => !window.__observatory.status.puppet_right.enabled);
  assert(actions.some(x => x.kind === 'puppet' && x.side === 'right' && x.action === 'arm'));
  await page.click('[aria-label="Close robot controls"]');
  await page.setViewport({width:390,height:844});''')
p.write_text(s)
