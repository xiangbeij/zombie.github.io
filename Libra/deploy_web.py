#!/usr/bin/env python3
"""Upload Vue dist to remote server"""
import paramiko
import os

HOST = '210.44.49.21'
PORT = 22
USER = 'root'
PASS = 'Qau2026@!'

LOCAL_DIST = r'E:\tool\openclaw-data\.openclaw\workspace\Libra\Libra-web\dist'
REMOTE_WEB = '/opt/Libra/Libra-web'

def main():
    print(f'[*] Connecting to {HOST}...')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    print('[+] Connected!')

    sftp = client.open_sftp()

    # Remove old dist and recreate
    print('[*] Cleaning old dist...')
    client.exec_command(f'rm -rf {REMOTE_WEB}/dist')

    # Upload dist files
    print('[*] Uploading dist folder...')
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

    # Kill old http.server if any
    print('[*] Restarting web server on 5189...')
    client.exec_command("pkill -f 'python.*http.server.*5189' 2>/dev/null; sleep 1")
    client.exec_command(f'cd {REMOTE_WEB}/dist && nohup python -m http.server 5189 > {REMOTE_WEB}/web.log 2>&1 &')
    import time; time.sleep(2)

    # Test
    stdin, stdout, stderr = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:5189/ 2>/dev/null')
    code = stdout.read().decode().strip()
    print(f'[+] Web server HTTP status: {code}')

    # Also update the API CORS to allow the web port
    print('\n[✓] Done!')
    print(f'  API:  http://210.44.49.21:5188/api/health')
    print(f'  Web:  http://210.44.49.21:5189')

    client.close()

if __name__ == '__main__':
    main()
