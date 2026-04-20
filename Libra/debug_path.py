#!/usr/bin/env python3
import paramiko
HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)
def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()

# Test 1: What is sys.path[0] when running python3 /app/Libra.py?
test = r('docker exec --privileged libra /bin/sh -c "python3 -c \\"import sys; print(sys.path[:3])\\" 2>&1"')
print("sys.path:", test)

# Test 2: Can we import Framework from /app?
test2 = r('docker exec --privileged libra /bin/sh -c "cd /app && python3 -c \\"import sys; print(sys.path[:3])\\" 2>&1"')
print("sys.path from /app:", test2)

# Test 3: Try the actual import
test3 = r('docker exec --privileged libra /bin/sh -c "cd /app && python3 -c \\"from Framework.Libra_Console import Console; print(\\\\\\"OK\\\\\\")\\" 2>&1"')
print("Import Framework:", test3)

# Test 4: Check PYTHONPATH effect
test4 = r('docker exec --privileged libra /bin/sh -c "PYTHONPATH=/app python3 -c \\"import sys; print(sys.path[:3])\\" 2>&1"')
print("sys.path with PYTHONPATH=/app:", test4)

# Test 5: Try with PYTHONPATH
test5 = r('docker exec --privileged libra /bin/sh -c "PYTHONPATH=/app python3 -c \\"from Framework.Libra_Console import Console; print(\\\\\\"OK\\\\\\")\\" 2>&1"')
print("Import with PYTHONPATH:", test5)

# Test 6: Check what's at line 6 of task_rulefind on server
test6 = r('docker exec --privileged libra python3 -c "open(\'/app/Moudle/task_rulefind.py\').readlines()[5]"')
print("Line 6 of task_rulefind.py:", test6)

# Test 7: How many lines does the server task_rulefind.py have?
test7 = r('docker exec --privileged libra wc -l /app/Moudle/task_rulefind.py')
print("Lines in server task_rulefind.py:", test7)

c.close()
