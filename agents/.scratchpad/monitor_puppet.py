"""Read-only ten-second monitoring window; never enables or commands motors."""
import datetime
import json
import time
import urllib.request

MONITOR_SECONDS = 10
POLL_SECONDS = 1
end = time.monotonic()+MONITOR_SECONDS
while time.monotonic() < end:
    with urllib.request.urlopen('http://127.0.0.1:28347/api/status', timeout=3) as response:
        status = json.load(response)
    print(json.dumps({
        'time': datetime.datetime.now().isoformat(timespec='seconds'),
        'puppet': status.get('puppet'),
        'left': {role: {key: ([round(x, 4) for x in value] if key == 'joints' else value)
                       for key, value in state.items() if key in ('joints', 'modes', 'error', 'ready')}
                 for role, state in status['arms'].items() if role.endswith('_left')},
    }), flush=True)
    time.sleep(POLL_SECONDS)
