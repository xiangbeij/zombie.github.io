#!/usr/bin/env python3
"""Build and deploy Orion via Docker"""
import paramiko
import os
import time

HOST = '210.44.49.21'
USER = 'root'
PASS = 'Qau2026@!'
LOCAL = r'/opt/Orion-data\.openclaw\workspace\Orion'
REMOTE = '/tmp/Orion-build'

def rmkdir(sftp, path):
    dirs = []
    while path and path != '/':
        dirs.append(path)
        path = os.path.dirname(path)
    dirs.reverse()
    for d in dirs:
        try:
            sftp.mkdir(d)
        except:
            pass

def upload_file(sftp, local_path, remote_path):
    rmkdir(sftp, os.path.dirname(remote_path))
    sftp.put(local_path, remote_path)

def upload_tree(sftp, local_dir, remote_dir, extensions=None, exclude=None):
    exclude = exclude or set()
    count = 0
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in exclude]
        rel = os.path.relpath(root, local_dir)
        rd = os.path.join(remote_dir, rel if rel != '.' else '').replace('\\', '/')
        rmkdir(sftp, rd)
        for file in files:
            if extensions and not any(file.endswith(e) for e in extensions):
                continue
            lp = os.path.join(root, file)
            rp = os.path.join(rd, file).replace('\\', '/')
            upload_file(sftp, lp, rp)
            count += 1
    return count

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=30)
sftp = client.open_sftp()

def run(cmd, timeout=120):
    chan = client.exec_command(cmd)
    stdout = chan[1].read()
    stderr = chan[2].read()
    return stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace')

print("[*] Preparing remote build directory...")
try:
    sftp.rmdir(REMOTE)
except:
    pass
rmkdir(sftp, REMOTE)

print("[*] Uploading Dockerfile2...")
upload_file(sftp, os.path.join(LOCAL, 'Dockerfile2'), REMOTE + '/Dockerfile')
print("  Dockerfile: OK")

print("  Vue dist...")
n = upload_tree(sftp, os.path.join(LOCAL, 'Orion-web', 'dist'), REMOTE + '/Orion-web/dist')
print(f"  Vue dist: {n} files")

print("  Orion source...")
for f in ['orion.py', 'orion.db']:
    upload_file(sftp, os.path.join(LOCAL, f), REMOTE + '/' + f)

for sub in ['Config', 'Framework', 'Moudle', 'ORM', 'Tools']:
    n = upload_tree(sftp, os.path.join(LOCAL, sub), REMOTE + '/' + sub)
    print(f"  {sub}: {n} files")

print("  API server files...")
rmkdir(sftp, REMOTE + '/Orion-server')
for f in ['app_batch.py', 'serve.py']:
    fp = os.path.join(LOCAL, 'Orion-server', f)
    if os.path.exists(fp):
        upload_file(sftp, fp, REMOTE + '/Orion-server/' + f)
        print(f"  {f}: OK")

print(f"[+] All uploaded to {REMOTE}")

# Stop old containers
print("\n[*] Cleaning up old containers...")
out, _ = run('docker ps -a --filter "name=Orion" -q')
for cid in out.strip().split('\n'):
    if cid.strip():
        run(f'docker stop {cid.strip()} 2>/dev/null')
        run(f'docker rm {cid.strip()} 2>/dev/null')
        print(f"  Removed: {cid[:12]}")

# Build image
print("\n[*] Building Docker image (5-10 min)...")
out, err = run(f'cd {REMOTE} && docker build -t Orion:latest . 2>&1', timeout=600)
if 'Successfully' in out:
    print("  [OK] Image built")
    for line in out.split('\n'):
        if 'Successfully' in line:
            print(f"    {line.strip()[:100]}")
else:
    print("[!] Build issues:")
    for line in out.split('\n')[-15:]:
        print(f"  {line}")
    if err:
        print("STDERR:", err[-300:])

# Start container
print("\n[*] Starting container (ports 5188=API, 5189=Web)...")
out, err = run(
    f'docker run -d --name Orion -p 5188:5188 -p 5189:3000 '
    f'--restart unless-stopped '
    f'-v {REMOTE}/reports:/app/reports '
    f'Orion:latest 2>&1'
)
cid = out.strip()
print(f"  Container: {cid[:30]}")

print("  Waiting 10s for startup...")
time.sleep(10)

out, _ = run('docker ps --filter "name=^Orion$" --format "{{.Names}} {{.Status}}"')
print(f"  Status: {out.strip()}")

out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://localhost:5189/')
print(f"  Web (5189): HTTP {out.strip()}")

out, _ = run('curl -s http://localhost:5189/api/health')
print(f"  API health: {out.strip()}")

print("\n[*] Copying files to /opt/Orion (persistent)...")
run('mkdir -p /opt/Orion')
for item in ['orion.py', 'orion.db', 'Config', 'Framework', 'Moudle', 'ORM', 'Tools']:
    run(f'cp -r "{REMOTE}/{item}" "/opt/Orion/" 2>/dev/null || true')
run(f'cp -r "{REMOTE}/Orion-server" "/opt/Orion/" 2>/dev/null || true')
print("[+] /opt/Orion updated")

client.close()
print("\n======================================================")
print("  DONE!")
print("  Web UI:  http://210.44.49.21:5189")
print("  API:     http://210.44.49.21:5189/api/health")
print("======================================================")
