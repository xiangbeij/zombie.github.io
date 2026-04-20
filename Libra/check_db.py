#!/usr/bin/env python3
"""Check what tables exist in the database"""
import paramiko

HOST, USER, PASS = '210.44.49.21', 'root', 'Qau2026@!'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=22, username=USER, password=PASS, timeout=15)

# Check tables in the database inside container
script = '''docker exec libra python3 -c "
import sqlite3
conn = sqlite3.connect('/app/Libra.db')
cursor = conn.cursor()
cursor.execute(\\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;\\")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {t[0]}')
    cnt = cursor.fetchone()[0]
    print(f'  {t[0]}: {cnt} rows')
conn.close()
"'''
def r(cmd): return c.exec_command(cmd)[1].read().decode('utf-8', errors='replace').strip()
print(r(script))

# Also check /opt/Libra/Libra.db
script2 = '''python3 -c "
import sqlite3
conn = sqlite3.connect('/opt/Libra/Libra.db')
cursor = conn.cursor()
cursor.execute(\\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;\\")
tables = cursor.fetchall()
print('Tables in /opt/Libra/Libra.db:', [t[0] for t in tables])
conn.close()
"'''
print(r(script2))
c.close()
