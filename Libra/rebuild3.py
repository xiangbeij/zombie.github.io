#!/usr/bin/env python3
"""Full rebuild and start of Libra Docker container"""
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()
def rb(cmd): return client.exec_command(cmd)

print("[1] Check existing image...")
img = r('docker images libra:latest --format "{{.Repository}}:{{.Tag}} {{.Size}}"')
print(f"  Image: {img or 'NOT FOUND'}")

print("[2] Upload all files...")
# Dockerfile
sftp.put(os.path.join(LOCAL, 'Dockerfile2'), f'{REMOTE}/Dockerfile')
# Updated Libra.py with sys.path fix
sftp.put(os.path.join(LOCAL, 'Libra.py'), f'{REMOTE}/Libra.py')
# __init__.py files
for d in ['Config', 'Framework', 'Moudle', 'ORM', 'Tools', 'Libra-server']:
    lp = os.path.join(LOCAL, d, '__init__.py')
    if os.path.exists(lp):
        sftp.put(lp, f'{REMOTE}/{d}/__init__.py')
        print(f"  {d}/__init__.py")
print("  All files uploaded")

print("[3] Build Docker image (takes 5-15 min)...")
# Use docker build with streaming output
chan = client.exec_command(f'cd {REMOTE} && docker build -t libra:latest . 2>&1')
out_lines = []
while True:
    line = chan[1].readline()
    if not line:
        break
    line = line.decode('utf-8', errors='replace')
    out_lines.append(line)
    if len(out_lines) % 20 == 0:
        print(f"  ... build in progress ({len(out_lines)} lines)")

full_out = ''.join(out_lines)
if 'Successfully' in full_out:
    print("  BUILD OK")
else:
    print("  BUILD output last 30 lines:")
    for line in full_out.split('\n')[-30:]:
        if line.strip(): print('  ', line.strip()[:100])

print("[4] Start container...")
r('docker rm libra 2>/dev/null; echo removed')
cid = r(f'docker run -d --name libra -p 5188:5188 -p 5189:3000 --restart unless-stopped -v {REMOTE}/reports:/app/reports libra:latest 2>&1').strip()
print(f"  Container: {cid[:30]}")

print("[5] Waiting 20s for startup...")
time.sleep(20)

print("[6] Test imports inside container...")
test_out = r('docker exec --privileged libra python3 -c "import sys; sys.path.insert(0,\'/app\'); from Framework.Libra_Console import Console; print(\'Framework:OK\'); from Moudle.task_console import task_console; print(\'Moudle:OK\'); import requests; print(\'requests:OK\')" 2>&1')
print(f"  {test_out.strip()}")

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
