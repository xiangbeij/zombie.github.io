#!/usr/bin/env python3
"""Deploy Libra to remote server via SSH"""
import paramiko
import os
import time

HOST = '210.44.49.21'
PORT = 22
USER = 'root'
PASS = 'Qau2026@!'

LOCAL_LIBRA = r'E:\tool\openclaw-data\.openclaw\workspace\Libra'
REMOTE_PATH = '/opt/Libra'

def main():
    print(f'[*] Connecting to {HOST}...')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    print('[+] Connected!')

    # 1. Check existing services on relevant ports
    print('\n[*] Checking existing services...')
    stdin, stdout, stderr = client.exec_command('ss -tlnp | grep -E ":(21|22|80|3000|443|5188|8000|8080)" 2>/dev/null || netstat -tlnp | grep -E ":(21|22|80|3000|443|5188|8000|8080)"')
    print(stdout.read().decode('utf-8', errors='replace'))
    print(stderr.read().decode('utf-8', errors='replace'))

    # 2. Check if port 21 is in use and what for
    print('\n[*] Checking port 21 usage...')
    stdin, stdout, stderr = client.exec_command('ss -tlnp | grep ":21 "')
    out = stdout.read().decode('utf-8', errors='replace')
    print(out or '(port 21 not in use for TCP listening)')

    # 3. Create remote directory
    print(f'\n[*] Creating {REMOTE_PATH}...')
    client.exec_command(f'mkdir -p {REMOTE_PATH}')

    # 4. Upload files via SFTP
    print('[*] Uploading files via SFTP...')
    sftp = client.open_sftp()
    uploaded = 0
    for root, dirs, files in os.walk(LOCAL_LIBRA):
        # Skip node_modules and dist cache
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__', 'dist')]
        rel = os.path.relpath(root, LOCAL_LIBRA)
        remote_dir = os.path.join(REMOTE_PATH, rel if rel != '.' else '').replace('\\', '/')
        try:
            client.exec_command(f'mkdir -p "{remote_dir}"')
        except:
            pass
        for file in files:
            if file in ('node_modules', '.git'):
                continue
            local_path = os.path.join(root, file)
            remote_file = os.path.join(remote_dir, file).replace('\\', '/')
            try:
                sftp.put(local_path, remote_file)
                uploaded += 1
                if uploaded % 20 == 0:
                    print(f'  ... uploaded {uploaded} files')
            except Exception as e:
                print(f'  [!] Failed: {remote_file} -> {e}')

    print(f'[+] Uploaded {uploaded} files')

    # 5. Install Python dependencies on server
    print('\n[*] Installing Python dependencies on server...')
    cmd = 'pip install flask flask-cors apscheduler reportlab -q 2>&1'
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out[-500:] if out else '')
    print(err[-200:] if err else '')
    if 'ERROR' in err or 'error' in out[-300:]:
        print('[!] Some dependencies may have failed to install')

    # 6. Stop old service if running on 5188
    print('\n[*] Checking for existing Libra service on port 5188...')
    stdin, stdout, stderr = client.exec_command("ps aux | grep 'app.*5188' | grep -v grep")
    old = stdout.read().decode('utf-8', errors='replace')
    if old:
        print(f'  Found old process, killing...')
        client.exec_command("pkill -f 'app.*5188' || taskkill /F /IM python.exe 2>/dev/null || true")
        time.sleep(1)
    else:
        print('  No existing process found')

    # 7. Start new service
    print('\n[*] Starting Libra API service on port 5188...')
    start_cmd = f'cd {REMOTE_PATH}/Libra-server && nohup python app_batch.py > {REMOTE_PATH}/libra_server.log 2>&1 &'
    client.exec_command(start_cmd)
    time.sleep(3)

    # 8. Check if running
    stdin, stdout, stderr = client.exec_command(f'curl -s http://localhost:5188/api/health 2>/dev/null || wget -qO- http://localhost:5188/api/health 2>/dev/null || echo "API not responding"')
    resp = stdout.read().decode('utf-8', errors='replace').strip()
    print(f'  API health: {resp}')

    # 9. Build and serve Vue frontend
    print('\n[*] Building Vue frontend on server...')
    build_cmd = f'cd {REMOTE_PATH}/Libra-web && npm install --silent 2>&1 | tail -3 && npm run build 2>&1 | tail -5'
    stdin, stdout, stderr = client.exec_command(build_cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out[-500:])
    if err:
        print('ERR:', err[-200:])

    # 10. Check if nginx is available and configure it
    print('\n[*] Setting up frontend serving...')
    nginx_check = client.exec_command('which nginx 2>/dev/null || echo "nginx not found"')
    nginx_path = nginx_check[1].read().decode().strip()
    print(f'  nginx: {nginx_path}')

    if nginx_path:
        # Configure nginx for the Vue build
        nginx_conf = f'''
server {{
    listen 5189;
    server_name _;
    root {REMOTE_PATH}/Libra-web/dist;
    index index.html;
    location / {{
        try_files $uri $uri/ /index.html;
    }}
    location /api {{
        proxy_pass http://127.0.0.1:5188;
        proxy_set_header Host $host;
    }}
}}
'''
        client.exec_command(f'echo "{nginx_conf}" > /etc/nginx/sites-available/libra')
        client.exec_command('ln -sf /etc/nginx/sites-available/libra /etc/nginx/sites-enabled/libra 2>/dev/null || true')
        client.exec_command('nginx -t && nginx -s reload 2>/dev/null || true')
        print('  nginx configured, frontend available at http://210.44.49.21:5189')
    else:
        # Use Python's built-in HTTP server as fallback
        serve_cmd = f'cd {REMOTE_PATH}/Libra-web/dist && nohup python -m http.server 5189 > {REMOTE_PATH}/libra_web.log 2>&1 &'
        client.exec_command(serve_cmd)
        print('  Frontend available at http://210.44.49.21:5189 (http.server)')

    print('\n[+] Deployment complete!')
    print(f'  API:  http://210.44.49.21:5188')
    print(f'  Web:  http://210.44.49.21:5189')

    client.close()

if __name__ == '__main__':
    main()
