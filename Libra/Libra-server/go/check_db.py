import sqlite3
conn = sqlite3.connect('/opt/Libra/Libra.db')
cur = conn.cursor()
cur.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name="blacklink_rules"')
print('Schema:', cur.fetchone())
cur.execute('SELECT * FROM blacklink_rules LIMIT 2')
print('Data:', cur.fetchall())
conn.close()
