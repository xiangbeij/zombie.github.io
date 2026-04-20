#!/usr/bin/env python3
"""资产管理 Handler - 站点 CRUD + SSL 证书检测"""
import sys
import sqlite3
import json
import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse

DB_PATH = '/opt/Libra/Libra.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def list_sites():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*,
               (SELECT days_left FROM ssl_certs WHERE site_id=s.id ORDER BY checked_at DESC LIMIT 1) as ssl_days_left
        FROM sites s ORDER BY s.id DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_site(site_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sites WHERE id=?", (site_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def create_site(data):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sites (name, url, org, owner, contact, scan_type, schedule, enabled, ssl_expiry_warn)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (data['name'], data['url'], data.get('org',''), data.get('owner',''),
          data.get('contact',''), data.get('scan_type','HomePage_Scan'),
          data.get('schedule',''), data.get('enabled',1), data.get('ssl_expiry_warn',30)))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_site(new_id)

def update_site(site_id, data):
    conn = get_db()
    cur = conn.cursor()
    fields = []
    vals = []
    for k in ['name','url','org','owner','contact','scan_type','schedule','enabled','ssl_expiry_warn']:
        if k in data:
            fields.append(f"{k}=?")
            vals.append(data[k])
    if fields:
        vals.append(site_id)
        cur.execute(f"UPDATE sites SET {','.join(fields)}, updated_at=datetime('now','localtime') WHERE id=?", vals)
        conn.commit()
    conn.close()
    return get_site(site_id)

def delete_site(site_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM sites WHERE id=?", (site_id,))
    conn.commit()
    conn.close()
    return True

def check_ssl(site_url):
    """检测站点 SSL 证书信息"""
    try:
        parsed = urlparse(site_url if site_url.startswith('http') else f'https://{site_url}')
        host = parsed.netloc or parsed.path
        port = parsed.port or 443

        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                issuer = dict(x[0] for x in cert['issuer'])[('organizationName', '')]
                days_left = (not_after - datetime.now()).days

                return {
                    'domain': host,
                    'issuer': issuer,
                    'valid_from': not_before.strftime('%Y-%m-%d'),
                    'valid_until': not_after.strftime('%Y-%m-%d'),
                    'days_left': days_left,
                    'status': 'valid' if days_left > 0 else 'expired'
                }
    except Exception as e:
        return {'error': str(e), 'domain': site_url, 'status': 'error'}

def check_site_ssl(site_id):
    """检测站点 SSL 并存入数据库"""
    site = get_site(site_id)
    if not site:
        return {'error': 'Site not found'}

    ssl_info = check_ssl(site['url'])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ssl_certs (site_id, domain, issuer, valid_from, valid_until, days_left)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (site_id, ssl_info.get('domain',''), ssl_info.get('issuer',''),
          ssl_info.get('valid_from',''), ssl_info.get('valid_until',''),
          ssl_info.get('days_left', 0)))
    conn.commit()
    log_id = cur.lastrowid
    conn.close()

    return {'site_id': site_id, 'ssl': ssl_info}

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No action specified'}))
        return

    action = sys.argv[1]

    if action == 'list':
        data = list_sites()
        print(json.dumps(data, ensure_ascii=False))

    elif action == 'get' and len(sys.argv) >= 3:
        print(json.dumps(get_site(int(sys.argv[2])), ensure_ascii=False))

    elif action == 'create':
        payload = json.loads(sys.stdin.read())
        print(json.dumps(create_site(payload), ensure_ascii=False))

    elif action == 'update' and len(sys.argv) >= 3:
        payload = json.loads(sys.stdin.read())
        print(json.dumps(update_site(int(sys.argv[2]), payload), ensure_ascii=False))

    elif action == 'delete' and len(sys.argv) >= 3:
        delete_site(int(sys.argv[2]))
        print(json.dumps({'ok': True}))

    elif action == 'ssl-check' and len(sys.argv) >= 3:
        result = check_site_ssl(int(sys.argv[2]))
        print(json.dumps(result, ensure_ascii=False))

    else:
        print(json.dumps({'error': f'Unknown action: {action}'}))

if __name__ == '__main__':
    main()
