#!/usr/bin/env python3
import paramiko
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()
print("=== Files inside container /app ===")
print(r('docker exec libra ls /app/'))
print("\n=== /app/Framework ===")
print(r('docker exec libra ls /app/Framework/'))
print("\n=== /app/Moudle ===")
print(r('docker exec libra ls /app/Moudle/'))
print("\n=== __init__.py in /app/Framework ===")
print(r('docker exec libra cat /app/Framework/__init__.py 2>&1 || echo "NOT FOUND"'))
print("\n=== /app/Config ===")
print(r('docker exec libra ls /app/Config/'))
c.close()
