#!/usr/bin/env python3
"""Deploy Libra directly on Rocky Linux host - no Docker"""
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/opt/Libra'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()
def rb(cmd, timeout=30):
    chan = client.exec_command(cmd)
    return chan[1].read().decode('utf-8', errors='replace'), chan[2].read().decode('utf-8', errors='replace')

print("[1] Stop any existing Libra containers/processes...")
r('docker stop libra 2>/dev/null; docker rm libra 2>/dev/null; pkill -f app_batch.py 2>/dev/null; pkill -f serve.py 2>/dev/null; pkill -f "libra" 2>/dev/null; echo done')

print("[2] Check host Python packages...")
out, err = rb('pip3 install flask flask-cors apscheduler reportlab requests -q 2>&1', timeout=60)
print(f"   pip install: {out.strip()[:200]} {err.strip()[:200]}")

print("[3] Check Node.js...")
out = r('node --version 2>/dev/null && npm --version 2>/dev/null')
print(f"   Node: {out}")

print("[4] Create remote directory...")
r(f'mkdir -p {REMOTE}')

print("[5] Upload all source files...")
for root, dirs, files in os.walk(LOCAL):
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__', 'dist')]
    rel = os.path.relpath(root, LOCAL)
    rd = os.path.join(REMOTE, rel if rel != '.' else '').replace('\\', '/')
    try: client.exec_command(f'mkdir -p "{rd}"')
    except: pass
    for file in files:
        if file.endswith('.pyc'): continue
        lp = os.path.join(root, file)
        rp = os.path.join(rd, file).replace('\\', '/')
        try: sftp.put(lp, rp)
        except Exception as e:
            print(f"   [!] {rp}: {e}")

# Upload Vue dist separately
dist_dir = os.path.join(LOCAL, 'Libra-web', 'dist')
if os.path.exists(dist_dir):
    for root, dirs, files in os.walk(dist_dir):
        rel = os.path.relpath(root, dist_dir)
        rd = os.path.join(REMOTE, 'Libra-web', 'dist', rel if rel != '.' else '').replace('\\', '/')
        try: client.exec_command(f'mkdir -p "{rd}"')
        except: pass
        for file in files:
            lp = os.path.join(root, file)
            rp = os.path.join(rd, file).replace('\\', '/')
            try: sftp.put(lp, rp)
            except: pass
print("   Upload complete")

print("[6] Kill anything on 5188/5189...")
r('fuser -k 5188/tcp 2>/dev/null; fuser -k 5189/tcp 2>/dev/null; echo ports cleared')

print("[7] Start API server on 5188...")
r(f'cd {REMOTE}/Libra-server && nohup python3 app_batch.py > {REMOTE}/libra_api.log 2>&1 &')
time.sleep(3)

print("[8] Start all-in-one serve.py on 5189...")
r(f'cd {REMOTE}/Libra-server && nohup python3 serve.py > {REMOTE}/serve.log 2>&1 &')
time.sleep(3)

print("[9] Verify ports...")
out = r('ss -tlnp | grep -E "5188|5189"')
print(f"   {out or 'NO PORTS!'}")

print("[10] Test health...")
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print(f"   Health: {resp.read().decode().strip()}")
    with urllib.request.urlopen(BASE + '/', timeout=10) as resp:
        print(f"   Web root: HTTP {resp.status}")
except Exception as e:
    print(f"   Error: {e}")

print("[11] Test scan...")
try:
    data = json.dumps({'url': 'https://httpbin.org/get', 'scan_type': 'HomePage_Scan'}).encode()
    req = urllib.request.Request(BASE + '/api/scan', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r2 = json.loads(resp.read())
        print(f"   Task: {r2.get('task_id')}")
        for i in range(12):
            time.sleep(5)
            with urllib.request.urlopen(BASE + f'/api/scan/{r2["task_id"]}', timeout=10) as st:
                sd = json.loads(st.read())
                s = sd.get('status')
                print(f"   [{i+1}] {s}")
                if s == 'success':
                    res = sd.get('result', {})
                    print(f"   SUCCESS! bl={len(res.get('blacklink_list', []))} died={len(res.get('diedlink_list', []))}")
                    break
                elif s in ('error', 'timeout'):
                    print(f"   ERROR: {sd.get('error', '')[:200]}")
                    break
except Exception as e:
    print(f"   Scan Error: {e}")

print("\n[DONE] http://210.44.49.21:5189")
client.close()
