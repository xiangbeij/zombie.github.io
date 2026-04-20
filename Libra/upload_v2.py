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
def rmkdir(path):
    parts = []
    while path and path != '/':
        parts.append(path); path = os.path.dirname(path)
    parts.reverse()
    for p in parts:
        try: sftp.mkdir(p)
        except: pass
def upload_tree(local_dir, remote_dir):
    cnt = 0
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        rd = os.path.join(remote_dir, rel if rel != '.' else '').replace('\\', '/')
        rmkdir(rd)
        for file in files:
            lp = os.path.join(root, file)
            rp = os.path.join(rd, file).replace('\\', '/')
            sftp.put(lp, rp); cnt += 1
    return cnt

print("[*] Upload new dist...")
n = upload_tree(os.path.join(LOCAL, 'Libra-web', 'dist'), f'{REMOTE}/Libra-web/dist')
print(f"    {n} files")
print("[*] Upload new app_batch.py with AI endpoint...")
sftp.put(os.path.join(LOCAL, 'Libra-server', 'app_batch.py'), f'{REMOTE}/Libra-server/app_batch.py')
sftp.put(os.path.join(LOCAL, 'Libra-server', 'app_batch.py'), '/opt/Libra/Libra-server/app_batch.py')
r('docker cp /tmp/libra-build/Libra-server/app_batch.py libra:/app/Libra-server/app_batch.py')
print("[*] Restart container...")
r('docker restart libra')
time.sleep(10)
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print("    Health:", resp.read().decode().strip())
    with urllib.request.urlopen(BASE + '/', timeout=10) as resp:
        print("    Web root: HTTP", resp.status)
    # Test AI
    test_data = json.dumps({'result': {'taskurl':'https://example.com','blacklink_list':[{'url':'x.com','blacklinkres':['bad']}],'backdoor_list':[],'violativelink_list':[],'diedlink_list':[]}}).encode()
    req = urllib.request.Request(BASE + '/api/ai-analyze', data=test_data, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r2 = json.loads(resp.read())
        print(f"    AI: risk={r2.get('risk_level')} source={r2.get('source')}")
except Exception as e:
    print("    Error:", e)
print("[*] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[OK] Done!")
