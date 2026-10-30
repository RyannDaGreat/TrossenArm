"""ASGI intent/security tests without server startup or hardware access."""
import asyncio
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "web/source/backend"))
import server


async def test():
    """Command. Exercise in-memory HTTP routes; return None after security assertions pass."""
    pair = Mock()
    pair.snapshot.return_value = {"mode": "ready", "enabled": True}
    transport = httpx.ASGITransport(app=server.app, client=("127.0.0.1", 50000))
    with patch.object(server.hub, "pair", pair):
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:28347") as client:
            body = {"action": "arm", "client": "offline-client", "sequence": 1}
            assert (await client.post("/api/puppet", json=body)).status_code == 403
            assert (await client.post("/api/puppet", json=body, headers={"Origin": "https://evil.example"})).status_code == 403
            assert (await client.post("/api/puppet", json={**body, "action": "set_positions"},
                                      headers={"Origin": "http://127.0.0.1:28347"})).status_code == 422
            response = await client.post("/api/puppet", json=body, headers={"Origin": "http://127.0.0.1:28347"})
            assert response.status_code == 200, response.text
            pair.request.assert_called_once_with("arm", "offline-client", 1)
            with patch.object(server.hub, 'right_pair') as right:
                right.snapshot.return_value = {'mode':'ready'}
                response = await client.post('/api/puppet',json={**body,'side':'right'},headers={'Origin':'http://127.0.0.1:28347'})
                assert response.status_code == 200
                right.request.assert_called_once_with('arm','offline-client',1)
            pair.request.side_effect = ValueError("Pair not ready")
            assert (await client.post("/api/puppet", json=body,
                                      headers={"Origin": "http://127.0.0.1:28347"})).status_code == 409
    print("PASS: missing/foreign Origin blocked; arbitrary commands rejected; intent queued only; readiness errors explicit. No hardware accessed.")


asyncio.run(test())
