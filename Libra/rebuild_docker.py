#!/usr/bin/env python3
"""Rebuild Docker image with all fixes"""
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

print("[*] Stop + remove old container...")
r('docker stop libra 2>/dev/null; docker rm libra 2>/dev/null; echo done')

print("[*] Upload files...")
sftp.put(os.path.join(LOCAL, 'Dockerfile2'), f'{REMOTE}/Dockerfile')
sftp.put(os.path.join(LOCAL, 'Libra.py'), f'{REMOTE}/Libra.py')
sftp.put(os.path.join(LOCAL, 'Libra.py'), '/opt/Libra/Libra.py')
for d in ['Config', 'Framework', 'Moudle', 'ORM', 'Tools', 'Libra-server']:
    lp = os.path.join(LOCAL, d, '__init__.py')
    if os.path.exists(lp):
        sftp.put(lp, f'{REMOTE}/{d}/__init__.py')
        sftp.put(lp, f'/opt/Libra/{d}/__init__.py')
print("  All files uploaded")

print("[*] Rebuilding Docker image...")
out, err = r(f'cd {REMOTE} && docker build -t libra:latest . 2>&1', timeout=600)
if 'Successfully' in out:
    print("  BUILD OK")
else:
    print("  BUILD output:")
    for line in out.split('\n')[-15:]: print(' ', line)

print("[*] Starting container...")
cid = r(f'docker run -d --name libra -p 5188:5188 -p 5189:3000 --restart unless-stopped -v {REMOTE}/reports:/app/reports libra:latest 2>&1').strip()
print(f"  {cid[:30]}")

time.sleep(15)

print("[*] Testing scan...")
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print("  Health:", resp.read().decode().strip())
    data = json.dumps({'url': 'https://httpbin.org/get', 'scan_type': 'HomePage_Scan'}).encode()
    req = urllib.request.Request(BASE + '/api/scan', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r2 = json.loads(resp.read())
        print("  Task:", r2.get('task_id'))
        for i in range(12):
            time.sleep(5)
            with urllib.request.urlopen(BASE + f'/api/scan/{r2["task_id"]}', timeout=10) as st:
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

print("[*] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[DONE] http://210.44.49.21:5189")
