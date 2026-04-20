#!/usr/bin/env python3
"""Upload fixed db_rules.py and retest"""
import paramiko, os, time

HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

print("[*] Uploading fixed db_rules.py...")
sftp.put(os.path.join(LOCAL, 'ORM', 'db_rules.py'), f'{REMOTE}/ORM/db_rules.py')
sftp.put(os.path.join(LOCAL, 'ORM', 'db_rules.py'), '/opt/Libra/ORM/db_rules.py')
r('docker cp /tmp/libra-build/ORM/db_rules.py libra:/app/ORM/db_rules.py')
print("    Uploaded")

print("[*] Restart container...")
r('docker restart libra')
time.sleep(10)

print("[*] Test /api/rules...")
import urllib.request, json, urllib.error
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/rules', timeout=10) as resp:
        rules = json.loads(resp.read())
        print(f"    Status: {resp.status}")
        print(f"    blacklist_rules: {len(rules['blacklink_rules'])}")
        print(f"    backdoor_rules: {len(rules['backdoor_rules'])}")
        print(f"    backdoor_paths: {len(rules['backdoor_paths'])}")
        print("    [OK] Rules endpoint works!")
except urllib.error.HTTPError as e:
    print(f"    HTTP {e.code}: {e.read().decode()[:300]}")
except Exception as e:
    print(f"    Error: {e}")

print("\n[*] Full API health check...")
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print(f"    {resp.read().decode()}")
    with urllib.request.urlopen(BASE + '/api/stats', timeout=10) as resp:
        print(f"    {resp.read().decode()}")
except Exception as e:
    print(f"    Error: {e}")

print("[*] Container:", r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print("\n[DONE] All fixed!")
