#!/usr/bin/env python3
import paramiko
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

print("=== task_rulefind.py (server) ===")
print(r('docker exec --privileged libra head -20 /app/Moudle/task_rulefind.py'))
print("\n=== task_response.py (server) ===")
print(r('docker exec --privileged libra head -10 /app/Moudle/task_response.py'))
c.close()
