#!/usr/bin/env python3
"""Upload new Vue build to server"""
import paramiko
import os

HOST = '210.44.49.21'
USER = 'root'
PASS = 'Qau2026@!'
LOCAL_DIST = r'E:\tool\openclaw-data\.openclaw\workspace\Libra\Libra-web\dist'
REMOTE_WEB = '/opt/Libra/Libra-web'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)

# Kill old server
print('[*] Killing old server on 5189...')
client.exec_command("pkill -f 'serve.py' 2>/dev/null || true")
client.exec_command("pkill -f 'http.server.*5189' 2>/dev/null || true")

import time; time.sleep(1)

# Upload new dist
sftp = client.open_sftp()
print('[*] Uploading new dist...')
uploaded = 0
for root, dirs, files in os.walk(LOCAL_DIST):
    rel = os.path.relpath(root, LOCAL_DIST)
    remote_dir = os.path.join(REMOTE_WEB, 'dist', rel if rel != '.' else '').replace('\\', '/')
    try:
        client.exec_command(f'mkdir -p "{remote_dir}"')
    except:
        pass
    for file in files:
        local_path = os.path.join(root, file)
        remote_file = os.path.join(remote_dir, file).replace('\\', '/')
        try:
            sftp.put(local_path, remote_file)
            uploaded += 1
        except Exception as e:
            print(f'  [!] {remote_file}: {e}')
print(f'[+] Uploaded {uploaded} files')
sftp.close()

# Restart all-in-one server
print('[*] Restarting all-in-one server...')
client.exec_command('cd /opt/Libra/Libra-server && nohup python serve.py > /opt/Libra/serve.log 2>&1 &')
time.sleep(3)

# Test
stdin, stdout, stderr = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:5189/')
code = stdout.read().decode().strip()
print(f'[*] Frontend: HTTP {code}')

stdin, stdout, stderr = client.exec_command('curl -s http://localhost:5189/api/health')
health = stdout.read().decode().strip()
print(f'[*] API: {health}')

print('\n[+] Fully deployed!')
print('    Web UI:  http://210.44.49.21:5189')
print('    API:     http://210.44.49.21:5189/api/health')

client.close()
