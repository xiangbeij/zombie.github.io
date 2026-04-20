#!/usr/bin/env python3
import paramiko, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

print("[1] Clear __pycache__ inside container...")
r('docker exec --privileged libra find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true')
print("    Done")

print("\n[2] Test direct Libra.py inside container with clean cache...")
test = r('docker exec --privileged libra /bin/sh -c "PYTHONPATH=/app python3 /app/Libra.py -u https://httpbin.org/get -t HomePage_Scan 2>&1 | head -20"')
print(test[:500])

print("\n[3] Restart container fresh...")
r('docker restart libra')
time.sleep(12)

print("\n[4] Test via API...")
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print("    Health:", resp.read().decode().strip())
    data = json.dumps({'url': 'https://httpbin.org/get', 'scan_type': 'HomePage_Scan'}).encode()
    req = urllib.request.Request(BASE + '/api/scan', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r2 = json.loads(resp.read())
        print("    Task:", r2.get('task_id'), r2.get('message'))
        for i in range(12):
            time.sleep(5)
            with urllib.request.urlopen(BASE + f'/api/scan/{r2["task_id"]}', timeout=10) as st:
                sd = json.loads(st.read())
                s = sd.get('status')
                print(f"    [{i+1}] {s}")
                if s == 'success':
                    res = sd.get('result', {})
                    print(f"    SUCCESS! url={res.get('taskurl')} bl={len(res.get('blacklink_list', []))} died={len(res.get('diedlink_list', []))}")
                    break
                elif s in ('error', 'timeout'):
                    print(f"    FAILED: {sd.get('error', '')[:200]}")
                    break
except Exception as e:
    print("    Error:", e)

print("\n[5] Container logs (last 10 lines):")
print(r('docker logs libra 2>&1 | tail -10'))

c.close()
