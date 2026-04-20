#!/usr/bin/env python3
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

# Upload files
print('[1] Upload Dockerfile2...')
sftp.put(os.path.join(LOCAL, 'Dockerfile2'), REMOTE + '/Dockerfile')
print('[2] Rebuild Docker image...')
chan = client.exec_command('cd /tmp/libra-build && docker build -t libra:latest . 2>&1')
# Stream output
while True:
    try:
        ch = chan[1].read(8192)
        if not ch: break
        txt = ch.decode('utf-8', errors='replace')
        print(txt, end='', flush=True)
    except: break
print('[3] Container status:')
print(r('docker ps --filter name=libra --format "{{.Names}} {{.Status}}"'))
client.close()
