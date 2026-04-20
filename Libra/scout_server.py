#!/usr/bin/env python3
"""Thorough reconnaissance of the server before deployment"""
import paramiko
import json

HOST = '210.44.49.21'
USER = 'root'
PASS = 'Qau2026@!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
transport = client.get_transport()

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

print("=" * 60)
print("OS & Kernel")
print("=" * 60)
out, _ = run('cat /etc/os-release | grep -E "NAME|VERSION|PRETTY"')
print(out)

print("=" * 60)
print("All listening ports (ss -tlnp)")
print("=" * 60)
out, _ = run('ss -tlnp 2>/dev/null || netstat -tlnp')
print(out)

print("=" * 60)
print("Running processes (non-system)")
print("=" * 60)
out, _ = run('ps aux | grep -v "grep|systemd|apache|tuned" | grep -E "python|node|npm|java|docker|nginx|http" || echo "(none found)"')
print(out)

print("=" * 60)
print("Installed tools")
print("=" * 60)
for tool in ['node', 'npm', 'yarn', 'pnpm', 'python3', 'python', 'pip3', 'pip', 'java', 'go', 'docker', 'nginx', 'caddy', 'apachectl', 'uvicorn', 'gunicorn', 'supervisord']:
    out, _ = run(f'which {tool} 2>/dev/null && {tool} --version 2>/dev/null || echo "not found"')
    result = out.strip()
    if 'not found' not in result and result:
        print(f'  {tool}: {result[:80]}')

print("=" * 60)
print("Docker containers")
print("=" * 60)
out, _ = run('docker ps -a 2>/dev/null || echo "docker not available"')
print(out)

print("=" * 60)
print("Node.js details")
print("=" * 60)
out, _ = run('node --version 2>/dev/null && npm --version 2>/dev/null || echo "node/npm not found"')
print(out)
out, _ = run('ls /usr/local/lib/node_modules 2>/dev/null || ls /usr/lib/node_modules 2>/dev/null || echo "no global node_modules"')
print(out)

print("=" * 60)
print("Python packages (key ones)")
print("=" * 60)
for pkg in ['flask', 'flask_cors', 'apscheduler', 'reportlab', 'fastapi', 'django', 'uvicorn', 'django', 'celery', 'redis']:
    out, _ = run(f'python3 -c "import {pkg.replace(chr(95), chr(95))}; print(\\"{pkg} OK\\")" 2>/dev/null || python -c "import {pkg.replace(chr(95), chr(95))}; print(\\"{pkg} OK\\")" 2>/dev/null || echo "{pkg} not installed"')
    print(out.strip())

print("=" * 60)
print("Disk usage")
print("=" * 60)
out, _ = run('df -h | grep -v "tmpfs|overlay|shm"')
print(out)

print("=" * 60)
print("Memory")
print("=" * 60)
out, _ = run('free -h')
print(out)

print("=" * 60)
print("Existing web services")
print("=" * 60)
out, _ = run('curl -s -o /dev/null -w "%{http_code} %{redirect_url}" http://localhost:80 2>/dev/null || echo "nothing on 80"')
print(f'  localhost:80 -> {out.strip()}')
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://localhost:443 2>/dev/null || echo "nothing on 443"')
print(f'  localhost:443 -> {out.strip()}')

client.close()
print("\n[OK] Reconnaissance complete")
