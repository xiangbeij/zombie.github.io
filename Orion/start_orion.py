#!/usr/bin/env python3
import paramiko, time

HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/Orion-build'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)

def run(cmd):
    chan = client.exec_command(cmd)
    return chan[1].read().decode('utf-8', errors='replace')

print('[*] Checking current ports...')
print('    5188:', run('ss -tlnp | grep ":5188 "').strip())
print('    5189:', run('ss -tlnp | grep ":5189 "').strip())

print('[*] Killing old Python processes on 5188...')
# Kill by PID (found earlier)
run('kill 2951375 2951374 2>/dev/null; sleep 2; echo killed')
# Also try by name
run('pkill -f "app_batch.py" 2>/dev/null; pkill -f "serve.py" 2>/dev/null; echo pkill done')

print('[*] Ports after kill:')
print('    5188:', run('ss -tlnp | grep ":5188 "').strip() or 'FREE')
print('    5189:', run('ss -tlnp | grep ":5189 "').strip() or 'FREE')

print('[*] Removing old container if exists...')
run('docker rm Orion 2>/dev/null; echo done')

print('[*] Starting Docker container...')
result = run(f'docker run -d --name Orion -p 5188:5188 -p 5189:3000 --restart unless-stopped -v {REMOTE}/reports:/app/reports Orion:latest 2>&1')
print(f'    {result.strip()[:80]}')

print('[*] Waiting 15s...')
time.sleep(15)

print('[*] Container status:')
print('    ' + run('docker ps --filter name=^Orion$ --format "{{.Names}} {{.Status}}"').strip())

print('[*] Docker logs:')
logs = run('docker logs Orion 2>&1 | head -20').strip()
for line in logs.split('\n'):
    print('    ' + line)

print('[*] Web (5189):', run('curl -s -o /dev/null -w "%{http_code}" http://localhost:5189/').strip())
print('[*] API health:', run('curl -s http://localhost:5189/api/health').strip())

client.close()
print('\n[OK] Done!')
print('  Web: http://210.44.49.21:5189')
print('  API: http://210.44.49.21:5188/api/health')
