#!/usr/bin/env python3
"""Build and deploy Libra Docker container on remote server"""
import paramiko
import os
import time

HOST = '210.44.49.21'
USER = 'root'
PASS = 'Qau2026@!'
LOCAL = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
REMOTE = '/opt/Libra-docker'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=30)
sftp = client.open_sftp()

def run(cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=False)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

print("[*] Uploading files to server...")
# Create remote dir
client.exec_command(f'mkdir -p {REMOTE}')

# Upload Dockerfile
print("  Dockerfile...")
sftp.put(os.path.join(LOCAL, 'Dockerfile'), f'{REMOTE}/Dockerfile')

# Upload Vue source (for npm build on server)
print("  Vue source...")
for root, dirs, files in os.walk(os.path.join(LOCAL, 'Libra-web')):
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__', 'dist')]
    rel = os.path.relpath(root, os.path.join(LOCAL, 'Libra-web'))
    rd = os.path.join(REMOTE, 'Libra-web', rel if rel != '.' else '')
    rd = rd.replace('\\', '/')
    try:
        client.exec_command(f'mkdir -p "{rd}"')
    except: pass
    for file in files:
        lp = os.path.join(root, file)
        rp = os.path.join(rd, file).replace('\\', '/')
        try:
            sftp.put(lp, rp)
        except Exception as e:
            print(f'  [!] {rp}: {e}')

# Upload Libra source
print("  Libra source...")
for root, dirs, files in os.walk(LOCAL):
    # Skip web/node_modules/dist
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__', 'dist', 'Libra-web', 'Libra-server', 'reports', '__pycache__')]
    rel = os.path.relpath(root, LOCAL)
    rd = os.path.join(REMOTE, rel if rel != '.' else '')
    rd = rd.replace('\\', '/')
    try:
        client.exec_command(f'mkdir -p "{rd}"')
    except: pass
    for file in files:
        lp = os.path.join(root, file)
        rp = os.path.join(rd, file).replace('\\', '/')
        try:
            sftp.put(lp, rp)
        except: pass

# Upload API server files
print("  API server files...")
for f in ['app_batch.py', 'serve.py']:
    sftp.put(os.path.join(LOCAL, 'Libra-server', f), f'{REMOTE}/Libra-server/{f}')

print("[+] Upload complete")

# Stop old containers
print("\n[*] Stopping old libra containers...")
out, _ = run('docker ps -a --filter "name=libra" -q')
container_ids = out.strip().split('\n')
for cid in container_ids:
    if cid.strip():
        run(f'docker stop {cid.strip()} 2>/dev/null; docker rm {cid.strip()} 2>/dev/null')
        print(f"  Removed: {cid[:12]}")

# Build image
print("\n[*] Building Docker image (this may take a few minutes)...")
# Use docker build with no cache flag to ensure fresh build
out, err = run(f'cd {REMOTE} && docker build -t libra:latest . 2>&1', timeout=600)
if 'Successfully built' in out or 'Successfully tagged' in out:
    print("[+] Image built successfully")
    # Find the image ID
    for line in out.split('\n'):
        if 'Successfully built' in line or 'Successfully tagged' in line:
            print(f"  {line.strip()}")
else:
    print("[!] Build output:")
    print(out[-1000:])
    if err:
        print("STDERR:", err[-500:])

# Run container
print("\n[*] Starting container...")
out, err = run(
    f'docker run -d --name libra-web '
    f'-p 5189:3000 -p 5188:5188 '
    f'--restart unless-stopped '
    f'libra:latest 2>&1'
)
container_name = out.strip()
print(f"  Container: {container_name[:50]}")
time.sleep(5)

# Check status
out, _ = run('docker ps --filter "name=libra" --format "{{.Names}} {{.Status}}"')
print(f"\n[*] Container status: {out.strip()}")

# Test
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://localhost:5189/ 2>/dev/null || echo "failed"')
print(f"[*] Frontend HTTP: {out.strip()}")
out, _ = run('curl -s http://localhost:5189/api/health 2>/dev/null || echo "failed"')
print(f"[*] API health: {out.strip()}")

# Show exposed port
out, _ = run('docker port libra-web 2>/dev/null || echo "no ports"')
print(f"[*] Exposed ports: {out.strip()}")

client.close()
print("\n[OK] Done!")
