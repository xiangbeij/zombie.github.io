#!/usr/bin/env python3
import paramiko

HOST = '210.44.49.21'
USER = 'root'
PASS = 'Qau2026@!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)

# Check what's in the dist folder
stdin, stdout, stderr = client.exec_command('find /opt/Libra/Libra-web/dist -type f 2>/dev/null | head -20')
print('Files in dist:')
print(stdout.read().decode('utf-8', errors='replace'))

# Check running services
stdin, stdout, stderr = client.exec_command('ps aux | grep -E "python|http" | grep -v grep | grep -v docker')
print('\nRunning Python services:')
print(stdout.read().decode('utf-8', errors='replace'))

# Check ports
stdin, stdout, stderr = client.exec_command('ss -tlnp | grep -E "5188|5189"')
print('\nPorts 5188/5189:')
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
