#!/usr/bin/env python3
"""Upload fixed serve.py and restart container"""
import paramiko, os, time

HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()

def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

# 1. Upload fixed serve.py
print("[*] Uploading fixed serve.py...")
sftp.put(os.path.join(LOCAL, 'Libra-server', 'serve.py'), f'{REMOTE}/Libra-server/serve.py')
print("    OK")

# 2. Also update in /opt/Libra
sftp.put(os.path.join(LOCAL, 'Libra-server', 'serve.py'), '/opt/Libra/Libra-server/serve.py')
print("[*] Copied to /opt/Libra too")

# 3. Stop container, copy new file into it, restart
print("[*] Stopping container...")
r('docker stop libra 2>&1')
print("    Stopped")

print("[*] Copying new serve.py into container filesystem...")
# Extract container, replace file, re-import
r('docker cp /tmp/libra-build/Libra-server/serve.py libra:/app/serve.py')
print("    Copied")

print("[*] Starting container...")
cid = r('docker start libra 2>&1').strip()
print(f"    Started: {cid}")

print("[*] Waiting 8s for startup...")
time.sleep(8)

print("[*] Testing POST /api/schedule through proxy...")
# Test POST through proxy (via external IP)
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
data = json.dumps({
    'name': '测试定时任务',
    'url': 'https://example.com',
    'scan_type': 'HomePage_Scan',
    'cron_expr': 'hourly'
}).encode()
req = urllib.request.Request(
    BASE + '/api/schedule',
    data=data,
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        print(f"    Status: {resp.status}")
        print(f"    Response: {result}")
except Exception as e:
    print(f"    ERROR: {e}")

print("\n[*] Testing batch scan...")
r2 = None
try:
    data2 = json.dumps({
        'urls': ['https://example.com', 'https://httpbin.org'],
        'scan_type': 'HomePage_Scan'
    }).encode()
    req2 = urllib.request.Request(BASE + '/api/batch', data=data2,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        r2 = json.loads(resp2.read())
        print(f"    Batch ID: {r2.get('batch_id')}")
        print(f"    Tasks: {len(r2.get('task_ids', []))}")
except Exception as e:
    print(f"    Batch ERROR: {e}")

print("\n[*] Final health check...")
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as r:
        print(f"    {r.read().decode()}")
except Exception as e:
    print(f"    Health ERROR: {e}")

print("\n[*] Container status:")
print("   ", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))

client.close()
print("\n[OK] Done!")
print("  Web: http://210.44.49.21:5189")
