"""
Simulate camera scan by calling the Flask app endpoints using test_client.
This doesn't require an actual camera and runs the server code in-process.

Run:
    python -m tests.simulate_camera_scan
or
    python tests/simulate_camera_scan.py

"""
import json
import sys
import os

# Ensure project root is on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app

TEST_QR = os.environ.get('TEST_QR', 'SIM-QR-0001')
TEST_SESSION = os.environ.get('TEST_SESSION', 'sim-session-1')


def run_simulation():
    print('Starting scan simulation using Flask test client...')
    with app.test_client() as client:
        # Call health first
        r = client.get('/health')
        print('/health ->', r.status_code, r.get_data(as_text=True))

        payload = {'qr_id': TEST_QR, 'session_id': TEST_SESSION}
        print('POST /api/scan_qr', payload)
        resp = client.post('/api/scan_qr', data=json.dumps(payload), content_type='application/json')
        print('Response status:', resp.status_code)
        try:
            data = resp.get_json()
        except Exception:
            data = resp.get_data(as_text=True)
        print('Response JSON/data:')
        print(json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, dict) else data)


if __name__ == '__main__':
    run_simulation()
