#!/usr/bin/env python3
"""Upload new app_batch.py and restart"""
import paramiko, os, time

HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

print("[*] Uploading new app_batch.py with AI endpoint...")
sftp.put(os.path.join(LOCAL, 'Libra-server', 'app_batch.py'), f'{REMOTE}/Libra-server/app_batch.py')
sftp.put(os.path.join(LOCAL, 'Libra-server', 'app_batch.py'), '/opt/Libra/Libra-server/app_batch.py')
r('docker cp /tmp/libra-build/Libra-server/app_batch.py libra:/app/Libra-server/app_batch.py')
print("    Uploaded")

print("[*] Restarting...")
r('docker restart libra')
time.sleep(10)

print("[*] Test...")
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
try:
    # Test health
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print("    Health:", resp.read().decode().strip())
    # Test AI endpoint (mock data)
    test_data = json.dumps({'result': {'taskurl': 'https://example.com', 'blacklink_list': [{'url': 'https://x.com/bad.js', 'blacklinkres': ['malicious']}], 'backdoor_list': [], 'violativelink_list': [], 'diedlink_list': []}}).encode()
    req = urllib.request.Request(BASE + '/api/ai-analyze', data=test_data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        print(f"    AI analysis: risk={result.get('risk_level')} source={result.get('source')}")
        print(f"    Analysis: {result.get('analysis', '')[:80]}")
except Exception as e:
    print("    Error:", e)

print("[*] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[OK]")
