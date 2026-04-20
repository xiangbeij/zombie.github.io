#!/usr/bin/env python3
import paramiko, time
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

# Test what happens when we run Libra.py with PYTHONPATH from inside the container
script = r'''docker exec libra /bin/sh -c '
echo "=== Python and PYTHONPATH ==="
python3 -c "import sys; print(\\"sys.executable:\\", sys.executable); print(\\"PYTHONPATH:\\", sys.path)"

echo ""
echo "=== Run Libra.py directly ==="
PYTHONPATH=/app python3 /app/Libra.py -u https://httpbin.org/get -t HomePage_Scan 2>&1 | head -20

echo ""
echo "=== Files in /app ==="
ls /app/
ls /app/Framework/
ls /app/Moudle/
' '''
print(r(script))
c.close()
