#!/usr/bin/env python3
"""Step 1: Start container from existing image"""
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

# Upload files first
print("[1] Upload Libra.py...")
sftp.put(os.path.join(LOCAL, 'Libra.py'), f'{REMOTE}/Libra.py')
sftp.put(os.path.join(LOCAL, 'Libra.py'), '/opt/Libra/Libra.py')
print("   OK")

print("[2] Upload __init__.py files...")
for d in ['Config', 'Framework', 'Moudle', 'ORM', 'Tools']:
    lp = os.path.join(LOCAL, d, '__init__.py')
    if os.path.exists(lp):
        sftp.put(lp, f'{REMOTE}/{d}/__init__.py')
        sftp.put(lp, f'/opt/Libra/{d}/__init__.py')
        print(f"   {d}/__init__.py OK")

print("[3] Start container from existing image...")
r('docker rm libra 2>/dev/null; echo removed')
cid = r(f'docker run -d --name libra -p 5188:5188 -p 5189:3000 --restart unless-stopped -v {REMOTE}/reports:/app/reports libra:latest 2>&1').strip()
print(f"   Container: {cid[:30]}")

print("[4] Install py3-requests...")
install_out = r('docker exec --privileged libra apk add --no-cache py3-requests 2>&1')
print(f"   {install_out.strip()[:200]}")

print("[5] Copy new files into running container...")
r(f'docker cp {REMOTE}/Libra.py libra:/app/Libra.py')
for d in ['Config', 'Framework', 'Moudle', 'ORM', 'Tools']:
    r(f'docker cp {REMOTE}/{d}/__init__.py libra:/app/{d}/__init__.py')

print("[6] Clear pycache...")
r('docker exec --privileged libra find /app -name __pycache__ -exec rm -rf {} + 2>/dev/null; echo done')

print("[7] Restart Flask (kill old, start new)...")
r('docker exec --privileged libra pkill -f app_batch.py 2>/dev/null; echo killed')
r('docker exec --privileged libra pkill -f serve.py 2>/dev/null; echo killed2')
r('docker exec -d --privileged libra sh -c "cd /app && nohup python3 /app/Libra-server/app_batch.py > /app/libra_api.log 2>&1 & sleep 3 && python3 /app/serve.py" 2>/dev/null')
time.sleep(5)

print("[8] Test health...")
import urllib.request
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print("   Health:", resp.read().decode().strip())
except Exception as e:
    print("   Error:", e)

print("[9] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[OK]")
