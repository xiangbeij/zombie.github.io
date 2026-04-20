#!/usr/bin/env python3
"""Switch server to all-in-one serve.py"""
import paramiko

HOST = '210.44.49.21'
USER = 'root'
PASS = 'Qau2026@!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)

# Kill old http.server on 5189
print('[*] Killing old http.server on 5189...')
client.exec_command("pkill -f 'http.server.*5189' 2>/dev/null || true")

import time; time.sleep(1)

# Upload new serve.py
print('[*] Uploading serve.py...')
sftp = client.open_sftp()
sftp.put(r'E:\tool\openclaw-data\.openclaw\workspace\Libra\Libra-server\serve.py',
         '/opt/Libra/Libra-server/serve.py')
sftp.close()

# Also upload updated api lib (with correct BASE_URL)
# First rebuild with correct base URL
import subprocess, os
dist_dir = r'E:\tool\openclaw-data\.openclaw\workspace\Libra\Libra-web\dist'

# Check the current api JS
print('[*] Checking current API URL in built JS...')
js_file = os.path.join(dist_dir, 'assets')
import glob
js_files = glob.glob(os.path.join(dist_dir, 'assets', '*.js'))
print(f'JS files: {js_files}')

# Start new all-in-one server
print('[*] Starting all-in-one server on 5189...')
cmd = 'cd /opt/Libra/Libra-server && nohup python serve.py > /opt/Libra/serve.log 2>&1 &'
client.exec_command(cmd)
time.sleep(3)

# Test
stdin, stdout, stderr = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:5189/')
code = stdout.read().decode().strip()
print(f'[*] Frontend (index.html) status: {code}')

stdin, stdout, stderr = client.exec_command('curl -s http://localhost:5189/api/health')
health = stdout.read().decode().strip()
print(f'[*] API health via proxy: {health}')

print('[+] Done!')
client.close()
