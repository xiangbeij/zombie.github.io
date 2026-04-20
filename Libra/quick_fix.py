#!/usr/bin/env python3
"""Start container from existing image + quick fix"""
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()
def rb(cmd, timeout=30):
    chan = client.exec_command(cmd)
    out = chan[1].read()
    err = chan[2].read()
    return out.decode('utf-8', errors='replace'), err.decode('utf-8', errors='replace')

print("[1] Upload fixed files...")
sftp.put(os.path.join(LOCAL, 'Libra.py'), f'{REMOTE}/Libra.py')
for d in ['Config', 'Framework', 'Moudle', 'ORM', 'Tools']:
    lp = os.path.join(LOCAL, d, '__init__.py')
    if os.path.exists(lp):
        sftp.put(lp, f'{REMOTE}/{d}/__init__.py')

print("[2] Install py3-requests in running container...")
# Start a temp container to install requests
out, err = rb('docker run -d --name libra-temp -p 51881:5188 -p 51891:3000 --restart unless-stopped -v /tmp/libra-build/reports:/app/reports libra:latest 2>&1', timeout=30)
cid = out.strip()
print(f"  Temp container: {cid[:20]}")
time.sleep(5)

print("  Installing py3-requests...")
out2, err2 = rb('docker exec --privileged libra-temp apk add --no-cache py3-requests 2>&1', timeout=60)
print(f"  {out2.strip()[:200]}")

print("[3] Copy new files into container...")
rb('docker stop libra-temp 2>/dev/null; docker rm libra-temp 2>/dev/null; echo done')
out3, err3 = rb('docker run -d --name libra-temp -v /tmp/libra-build:/mnt/src:ro libra:latest sh -c "cp -r /mnt/src/Libra.py /app/ && cp -r /mnt/src/Config /app/ && cp -r /mnt/src/Framework /app/ && cp -r /mnt/src/Moudle /app/ && cp -r /mnt/src/ORM /app/ && cp -r /mnt/src/Tools /app/ && rm -rf /app/__pycache__ /app/*/__pycache__ && echo DONE" 2>&1', timeout=60)
print(f"  Copy: {out3.strip()[:100]}")

print("[4] Commit the changes to a new image...")
out4, err4 = rb('docker commit libra-temp libra:v2 2>&1', timeout=60)
print(f"  Commit: {out4.strip()}")

print("[5] Stop and remove temp, start final container...")
out5, err5 = rb('docker stop libra-temp 2>/dev/null; docker rm libra-temp 2>/dev/null; docker run -d --name libra -p 5188:5188 -p 5189:3000 --restart unless-stopped -v /tmp/libra-build/reports:/app/reports libra:v2 2>&1', timeout=30)
print(f"  Final container: {out5.strip()[:60]}")

time.sleep(12)

print("[6] Test imports inside container...")
test = r('docker exec --privileged libra python3 -c "import sys; sys.path.insert(0,\'/app\'); from Framework.Libra_Console import Console; print(\'Framework:OK\'); from Moudle.task_console import task_console; print(\'Moudle:OK\'); import requests; print(\'requests:OK\')" 2>&1')
print(f"  {test.strip()}")

print("[7] Test scan via API...")
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print("  Health:", resp.read().decode().strip())
    data = json.dumps({'url': 'https://httpbin.org/get', 'scan_type': 'HomePage_Scan'}).encode()
    req = urllib.request.Request(BASE + '/api/scan', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r3 = json.loads(resp.read())
        print("  Task:", r3.get('task_id'))
        for i in range(12):
            time.sleep(5)
            with urllib.request.urlopen(BASE + f'/api/scan/{r3["task_id"]}', timeout=10) as st:
                sd = json.loads(st.read())
                s = sd.get('status')
                print(f"  [{i+1}] {s}")
                if s == 'success':
                    res = sd.get('result', {})
                    print(f"  SUCCESS! bl={len(res.get('blacklink_list', []))} died={len(res.get('diedlink_list', []))}")
                    break
                elif s in ('error', 'timeout'):
                    print(f"  ERROR: {sd.get('error', '')[:200]}")
                    break
except Exception as e:
    print("  Error:", e)

print("[8] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[DONE] http://210.44.49.21:5189")
