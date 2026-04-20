import sqlite3
conn = sqlite3.connect('/opt/Libra/Libra.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assets'")
print('assets table:', cur.fetchone())
cur.execute('SELECT COUNT(*) FROM assets')
print('assets count:', cur.fetchone())
cur.execute('SELECT * FROM assets LIMIT 3')
for row in cur.fetchall():
    print(row)
conn.close()
