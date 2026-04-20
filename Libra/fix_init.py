#!/usr/bin/env python3
"""Fix __init__.py missing - the root cause of import failures"""
import paramiko, os, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
REMOTE = '/tmp/libra-build'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = client.open_sftp()
def r(cmd): return client.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

# Upload __init__.py to all package dirs (6 dirs)
init_dirs = ['Config', 'Framework', 'Moudle', 'ORM', 'Tools', 'Libra-server']
for d in init_dirs:
    lp = os.path.join(LOCAL, d, '__init__.py')
    for remote_base in [f'{REMOTE}', '/opt/Libra']:
        rp = f'{remote_base}/{d}/__init__.py'
        try:
            sftp.put(lp, rp)
        except Exception as e:
            pass
    # Also copy into running container
    r(f'docker cp {REMOTE}/{d}/__init__.py libra:/app/{d}/__init__.py 2>/dev/null || true')
    print(f'  {d}/__init__.py')

print('\nTesting direct Libra.py run inside container...')
# Test: run Libra.py directly with PYTHONPATH inside container
test_out = r('docker exec --privileged libra /bin/sh -c "PYTHONPATH=/app python3 /app/Libra.py -u https://httpbin.org/get -t HomePage_Scan 2>&1 | head -20"')
print(test_out[:500])

print('\nRestarting container to pick up changes...')
r('docker restart libra')
time.sleep(12)

print('Testing via API...')
import urllib.request, json
BASE = 'http://210.44.49.21:5189'
try:
    with urllib.request.urlopen(BASE + '/api/health', timeout=10) as resp:
        print('  Health:', resp.read().decode().strip())
    data = json.dumps({'url': 'https://httpbin.org/get', 'scan_type': 'HomePage_Scan'}).encode()
    req = urllib.request.Request(BASE + '/api/scan', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r2 = json.loads(resp.read())
        print('  Task created:', r2.get('task_id'))
        for i in range(12):
            time.sleep(5)
            with urllib.request.urlopen(BASE + f'/api/scan/{r2["task_id"]}', timeout=10) as st:
                sd = json.loads(st.read())
                s = sd.get('status')
                print(f'  [{i+1}] {s}')
                if s == 'success':
                    print('  SUCCESS!')
                    break
                elif s in ('error', 'timeout'):
                    print('  ERROR:', sd.get('error', '')[:100])
                    break
except Exception as e:
    print('  Error:', e)

print('Container:', r('docker ps --filter name=^libra$ --format "{{.Names}} {{.Status}}"'))
client.close()
print('\n[OK]')
