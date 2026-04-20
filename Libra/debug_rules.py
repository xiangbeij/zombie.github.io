#!/usr/bin/env python3
"""Check the app_batch.py content in the container"""
import paramiko

HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)

def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

# Check what app_batch.py looks like in the container
print("=== Checking app_batch.py in container ===")
out = r('docker exec libra cat /app/Libra-server/app_batch.py | head -60')
print(out[:2000])

# Check the get_rules function
print("\n=== Checking get_rules function ===")
out = r('docker exec libra grep -n "sys.path" /app/Libra-server/app_batch.py')
print("sys.path lines:", out)

out = r('docker exec libra sed -n "610,630p" /app/Libra-server/app_batch.py')
print("\nget_rules section:", out)

# Check actual sys.path when running
print("\n=== Testing import in container ===")
test_script = '''
python3 -c "
import sys, os
BASE_DIR = "/app"
sys.path.insert(0, os.path.join(BASE_DIR, 'ORM'))
sys.path.insert(0, BASE_DIR)
print('sys.path:', sys.path[:3])
try:
    from Config.config_db import get_connection1
    print('Config import: OK')
except Exception as e:
    print('Config import ERROR:', e)
try:
    from db_rules import rulesnum
    print('db_rules import: OK')
except Exception as e:
    print('db_rules ERROR:', e)
"'''
out = r(f'docker exec libra /bin/sh -c \'{test_script}\'')
print(out)

c.close()
