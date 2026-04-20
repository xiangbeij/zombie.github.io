#!/usr/bin/env python3
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()
print("[*] Uploading fixed app_batch.py...")
sftp.put(os.path.join(LOCAL, 'Libra-server', 'app_batch.py'), f'{REMOTE}/Libra-server/app_batch.py')
sftp.put(os.path.join(LOCAL, 'Libra-server', 'app_batch.py'), '/opt/Libra/Libra-server/app_batch.py')
r('docker cp /tmp/libra-build/Libra-server/app_batch.py libra:/app/Libra-server/app_batch.py')
print("[*] Restart container...")
r('docker restart libra')
time.sleep(10)
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
print("[*] Testing scan...")
try:
    resp = urllib.request.urlopen(BASE + '/api/health', timeout=10)
    print("    Health:", resp.read().decode().strip())
    # Test scan
    data = json.dumps({'url': 'https://httpbin.org', 'scan_type': 'HomePage_Scan'}).encode()
    req = urllib.request.Request(BASE + '/api/scan', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r2 = json.loads(resp.read())
        print("    Scan started:", r2.get('task_id'), r2.get('message'))
        # Poll
        for i in range(12):
            time.sleep(5)
            with urllib.request.urlopen(BASE + f'/api/scan/{r2["task_id"]}', timeout=10) as st:
                st_data = json.loads(st.read())
                s = st_data.get('status')
                print(f"    [{i+1}] status={s}")
                if s == 'success':
                    print("    SUCCESS! result:", st_data.get('result', {}).get('taskurl'))
                    break
                elif s in ('error', 'timeout'):
                    print("    FAILED:", st_data.get('error'))
                    break
except Exception as e:
    print("    Error:", e)
print("[*] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[OK]")
