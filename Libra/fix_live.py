#!/usr/bin/env python3
"""Fix running container - install requests + fix sys.path"""
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

print("[1] Stop container...")
r('docker stop libra 2>/dev/null; echo done')

print("[2] Install py3-requests inside container...")
print(" ", r('docker exec --privileged libra apk add --no-cache py3-requests 2>&1')[:200])

print("[3] Upload new Libra.py...")
sftp.put(os.path.join(LOCAL, 'Libra.py'), f'{REMOTE}/Libra.py')
r(f'docker cp {REMOTE}/Libra.py libra:/app/Libra.py')

print("[4] Upload __init__.py files...")
for d in ['Config', 'Framework', 'Moudle', 'ORM', 'Tools']:
    lp = os.path.join(LOCAL, d, '__init__.py')
    if os.path.exists(lp):
        sftp.put(lp, f'{REMOTE}/{d}/__init__.py')
        r(f'docker cp {REMOTE}/{d}/__init__.py libra:/app/{d}/__init__.py')

print("[5] Clear __pycache__...")
r('docker exec --privileged libra find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; echo done')

# Write test script to file inside container
test_script = '''
import sys
sys.path.insert(0, '/app')
from Framework.Libra_Console import Console
print("Framework OK")
from Moudle.task_console import task_console
print("Moudle OK")
import requests
print("requests OK")
print("ALL IMPORTS GOOD")
'''

# Write the test script to a temp file
test_file_local = os.path.join(os.path.dirname(__file__), 'test_imports.py')
with open(test_file_local, 'w') as f:
    f.write(test_script)
sftp.put(test_file_local, '/tmp/test_imports.py')
r('docker cp /tmp/test_imports.py libra:/tmp/test_imports.py')

print("[6] Test imports inside container...")
test_out = r('docker exec --privileged libra python3 /tmp/test_imports.py 2>&1')
print("  ", test_out[:300])

print("[7] Start container...")
r('docker start libra')
time.sleep(12)

print("[8] Test scan via API...")
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

print("[9] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[DONE] http://210.44.49.21:5189")
