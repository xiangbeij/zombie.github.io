#!/usr/bin/env python3
import paramiko
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()
print("Docker images:", r('docker images libra'))
print("Port 5188:", r('ss -tlnp | grep ":5188"'))
print("Port 5189:", r('ss -tlnp | grep ":5189"'))
print("Python3:", r('python3 --version'))
print("pip3:", r('pip3 --version'))
print("node:", r('node --version 2>/dev/null || echo "no node"'))
c.close()
