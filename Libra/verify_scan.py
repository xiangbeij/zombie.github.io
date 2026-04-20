#!/usr/bin/env python3
import urllib.request, json, time
BASE = 'http://210.44.49.21:5189'
def api(path, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())
print("=== Testing scan after __init__.py fix ===")
r2 = api('/api/scan', {'url': 'https://httpbin.org/get', 'scan_type': 'HomePage_Scan'})
print("Scan created:", r2.get('task_id'))
for i in range(12):
    time.sleep(5)
    st = api(f'/api/scan/{r2["task_id"]}')
    s = st.get('status')
    print(f"[{i+1}] status={s}")
    if s == 'success':
        res = st.get('result', {})
        print(f"  SUCCESS! url={res.get('taskurl')} died={len(res.get('diedlink_list', []))}")
        break
    elif s in ('error', 'timeout'):
        print("  FAILED:", st.get('error', '')[:200])
        break
else:
    print("  Still running after 60s")
