#!/usr/bin/env python3
import paramiko, os, tempfile

HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
sftp = c.open_sftp()

# Write script using exec_command echo (avoids SFTP issues)
script = r'''cat > /tmp/test_flask.py << 'PYEOF'
import urllib.request, json, time, socket

# Test 1: Direct socket to Flask on 5188
print("=== Test 1: Direct socket to 5188 ===")
s = socket.socket()
s.settimeout(5)
r = s.connect_ex(('127.0.0.1', 5188))
print("Connect:", "OK" if r == 0 else f"FAIL {r}")
s.close()

# Test 2: HTTP POST to Flask
print("\n=== Test 2: POST /api/schedule ===")
data = json.dumps({"name":"test","url":"http://x.com","scan_type":"HomePage_Scan","cron_expr":"hourly"}).encode()
req = urllib.request.Request("http://127.0.0.1:5188/api/schedule", data=data, headers={"Content-Type":"application/json"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("Status:", resp.status)
        print("Body:", json.loads(resp.read()).get('status'))
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:100])

# Test 3: GET /api/health  
print("\n=== Test 3: GET /api/health ===")
try:
    with urllib.request.urlopen("http://127.0.0.1:5188/api/health", timeout=5) as r:
        print("Status:", r.status, r.read().decode())
except Exception as e:
    print("ERROR:", e)

PYEOF
python3 /tmp/test_flask.py'''

def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

print("Running Flask tests inside container...")
out = r(script)
print(out[:2000])

print("\n=== Docker logs ===")
print(r('docker logs libra 2>&1 | tail -20'))

c.close()
