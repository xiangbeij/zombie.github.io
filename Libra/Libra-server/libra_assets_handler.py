#!/usr/bin/env python3
"""
Libra Assets Handler - Pure Python implementation for asset discovery
Handles: IP range scanning, certificate import, snapshot management
Run as a threaded HTTP server or import as module with Flask/etc.
"""
import sqlite3
import json
import threading
import os
import re
import hashlib
import socket
import ssl
import struct
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = '/opt/Libra'
DB_PATH = os.path.join(BASE_DIR, 'Libra.db')
LOCK = threading.Lock()

# ─── DB Helpers ─────────────────────────────────────────────────────────────────

def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def json_resp(w, data, status=200):
    w.send_response(status)
    w.send_header('Content-Type', 'application/json')
    w.send_header('Access-Control-Allow-Origin', '*')
    w.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, PUT, OPTIONS')
    w.send_header('Access-Control-Allow-Headers', 'Content-Type')
    w.write(json.dumps(data).encode())
    w.end_headers()

def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ─── Asset Handlers ────────────────────────────────────────────────────────────

def handle_assets_list(db, params):
    page = int(params.get('page', [1])[0])
    page_size = int(params.get('page_size', [50])[0])
    search = params.get('search', [''])[0]
    asset_type = params.get('type', [''])[0]
    status = params.get('status', [''])[0]
    tags = params.get('tags', [''])[0]
    offset = (page - 1) * page_size

    where = ['1=1']
    args = []
    if search:
        where.append('(value LIKE ? OR title LIKE ? OR tags LIKE ?)')
        like = f'%{search}%'
        args.extend([like, like, like])
    if asset_type:
        where.append('asset_type = ?')
        args.append(asset_type)
    if status:
        where.append('status = ?')
        args.append(status)
    if tags:
        where.append('tags LIKE ?')
        args.append(f'%{tags}%')

    where_sql = ' AND '.join(where)
    cur = db.cursor()

    cur.execute(f'SELECT COUNT(*) FROM assets WHERE {where_sql}', args)
    total = cur.fetchone()[0]

    sql = f'''SELECT id, asset_type, value, port, scheme, title, server_fingerprint,
        status_code, content_hash, tags, status, first_seen, last_seen, note, cert_id, ip_range_id
        FROM assets WHERE {where_sql} ORDER BY last_seen DESC LIMIT ? OFFSET ?'''
    args.extend([page_size, offset])
    cur.execute(sql, args)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {'assets': rows, 'total': total, 'page': page, 'page_size': page_size}

def handle_assets_stats(db):
    cur = db.cursor()
    total = cur.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
    by_type = {}
    for row in cur.execute('SELECT asset_type, COUNT(*) FROM assets GROUP BY asset_type'):
        by_type[row[0]] = row[1]
    by_status = {}
    for row in cur.execute('SELECT status, COUNT(*) FROM assets GROUP BY status'):
        by_status[row[0]] = row[1]
    return {
        'total_assets': total,
        'by_type': by_type,
        'by_status': by_status,
        'total_snapshots': cur.execute('SELECT COUNT(*) FROM asset_snapshots').fetchone()[0],
        'pending_alerts': cur.execute("SELECT COUNT(*) FROM tamper_alerts WHERE confirmed=0").fetchone()[0],
        'ip_ranges': cur.execute('SELECT COUNT(*) FROM ip_ranges').fetchone()[0],
        'cert_imports': cur.execute('SELECT COUNT(*) FROM cert_assets').fetchone()[0],
    }

def handle_add_ip_range(db, data):
    cidr = data.get('cidr', [''])[0].strip()
    if not cidr:
        return {'error': 'cidr required'}, 400
    try:
        socket.inet_aton(cidr.split('/')[0])  # Basic validation
    except:
        return {'error': 'invalid CIDR'}, 400
    desc = data.get('description', [''])[0]
    tags = data.get('tags', [''])[0]
    now = now_str()
    try:
        cur = db.cursor()
        cur.execute('INSERT INTO ip_ranges (cidr, description, tags, created_at) VALUES (?, ?, ?, ?)',
            [cidr, desc, tags, now])
        db.commit()
        return {'id': cur.lastrowid, 'status': 'created'}
    except sqlite3.IntegrityError:
        return {'error': 'CIDR already exists'}, 409

def handle_ip_ranges_list(db):
    cur = db.cursor()
    cur.execute('SELECT id, cidr, description, tags, created_at FROM ip_ranges ORDER BY created_at DESC')
    cols = [d[0] for d in cur.description]
    return {'ip_ranges': [dict(zip(cols, r)) for r in cur.fetchall()]}

def handle_delete_ip_range(db, range_id):
    cur = db.cursor()
    cur.execute('DELETE FROM ip_ranges WHERE id = ?', [range_id])
    db.commit()
    return {'status': 'deleted'}

def handle_import_cert(db, data):
    pem_cert = data.get('public_key', [''])[0].strip()
    if not pem_cert:
        return {'error': 'public_key required'}, 400

    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        import base64

        # Extract certificate from PEM
        cert_block = pem_cert
        for start in ['-----BEGIN CERTIFICATE-----', '-----BEGIN CERTIFICATE-----']:
            idx = cert_block.find(start)
            if idx >= 0:
                break
        if idx < 0:
            return {'error': 'invalid PEM certificate'}, 400

        # Get DER bytes
        lines = cert_block[idx:].splitlines()
        pem_data = ''.join(l for l in lines if not l.startswith('-----'))
        cert_bytes = base64.b64decode(pem_data)

        cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
        sha1_fingerprint = cert.fingerprint(hashlib.sha1()).hex().upper()

        # Extract SANs
        try:
            san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            domains = san_ext.value.get_values_for_type(x509.DNSName)
        except:
            domains = []

        # Also add CN if no SANs
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        if cn and not domains:
            domains = [cn[0].value]

        now = now_str()
        cur = db.cursor()
        cur.execute('''INSERT OR REPLACE INTO cert_assets
            (cert_sha1, cert_subject, cert_issuer, cert_not_before, cert_not_after,
             san_count, domains, raw_cert, imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [sha1_fingerprint,
             (cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value if cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME) else ''),
             (cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value if cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME) else ''),
             cert.not_valid_before_utc.isoformat() if hasattr(cert.not_valid_before_utc, 'isoformat') else str(cert.not_valid_before_utc)[:10],
             cert.not_valid_after_utc.isoformat() if hasattr(cert.not_valid_after_utc, 'isoformat') else str(cert.not_valid_after_utc)[:10],
             len(domains), json.dumps(domains), pem_cert, now])
        db.commit()

        # Create domain assets
        cur.execute('SELECT id FROM cert_assets WHERE cert_sha1 = ?', [sha1_fingerprint])
        cert_id_row = cur.fetchone()
        cert_id = cert_id_row[0] if cert_id_row else 0

        added = 0
        for domain in domains:
            if domain.strip():
                try:
                    cur.execute('''INSERT OR IGNORE INTO assets
                        (asset_type, value, port, scheme, cert_id, status, first_seen, last_seen)
                        VALUES ('domain', ?, 443, 'https', ?, 'unknown', ?, ?)''',
                        [domain.strip(), cert_id, now, now])
                    if cur.rowcount > 0:
                        added += 1
                except:
                    pass
        db.commit()
        return {'cert_sha1': sha1_fingerprint, 'domains': domains[:20], 'domain_count': added, 'status': 'imported'}
    except ImportError:
        return {'error': 'cryptography library not installed (pip install cryptography)'}, 500
    except Exception as e:
        return {'error': str(e)}, 400

def handle_create_asset(db, data):
    asset_type = data.get('asset_type', [''])[0]
    value = data.get('value', [''])[0].strip()
    if not asset_type or not value:
        return {'error': 'asset_type and value required'}, 400
    port = int(data.get('port', [443])[0])
    scheme = data.get('scheme', ['https'])[0]
    tags = data.get('tags', [''])[0]
    note = data.get('note', [''])[0]
    now = now_str()
    cur = db.cursor()
    cur.execute('''INSERT OR REPLACE INTO assets
        (asset_type, value, port, scheme, tags, note, status, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, 'unknown', ?, ?)''',
        [asset_type, value, port, scheme, tags, note, now, now])
    db.commit()
    return {'id': cur.lastrowid, 'status': 'created'}

def handle_take_snapshot(db, asset_id):
    cur = db.cursor()
    cur.execute('SELECT value, scheme, port FROM assets WHERE id = ?', [asset_id])
    row = cur.fetchone()
    if not row:
        return {'error': 'asset not found'}, 404
    value, scheme, port = row

    url = f'{scheme}://{value}:{port}'
    if (scheme == 'https' and port == 443) or (scheme == 'http' and port == 80):
        url = f'{scheme}://{value}'

    try:
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'Libra-Asset-Scanner/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read()
            status_code = resp.status
    except Exception as e:
        return {'error': f'failed to fetch: {e}'}, 500

    content_hash = hashlib.sha1(body).hexdigest()
    title = ''
    m = re.search(r'<title[^>]*>([^<]+)</title>', body.decode('utf-8', errors='ignore'), re.I)
    if m:
        title = m.group(1).strip()

    # Get previous hash
    cur.execute('SELECT content_hash FROM asset_snapshots WHERE asset_id = ? ORDER BY scanned_at DESC LIMIT 1', [asset_id])
    prev_row = cur.fetchone()
    prev_hash = prev_row[0] if prev_row else ''

    diff_ratio = 0.0
    if prev_hash and prev_hash != content_hash:
        diff_ratio = min(1.0, sum(a != b for a, b in zip(prev_hash, content_hash)) / max(len(prev_hash), 1))

    now = now_str()
    cur.execute('''INSERT INTO asset_snapshots
        (asset_id, url, title, content_hash, diff_ratio, scanned_at)
        VALUES (?, ?, ?, ?, ?, ?)''',
        [asset_id, url, title, content_hash, diff_ratio, now])
    snapshot_id = cur.lastrowid

    cur.execute('UPDATE assets SET last_seen = ?, content_hash = ?, title = ?, status_code = ? WHERE id = ?',
        [now, content_hash, title, status_code, asset_id])

    # Alert on significant change
    if diff_ratio > 0.3:
        cur.execute('''INSERT INTO tamper_alerts
            (asset_id, snapshot_id, alert_type, alert_detail, created_at)
            VALUES (?, ?, 'content_changed', ?, ?)''',
            [asset_id, snapshot_id, json.dumps({'diff_ratio': diff_ratio}), now])

    db.commit()
    return {'snapshot_id': snapshot_id, 'content_hash': content_hash, 'diff_ratio': diff_ratio}

def handle_get_snapshots(db, asset_id):
    cur = db.cursor()
    cur.execute('''SELECT id, asset_id, url, title, keywords, description, content_hash,
        diff_ratio, scanned_at FROM asset_snapshots WHERE asset_id = ? ORDER BY scanned_at DESC LIMIT 30''',
        [asset_id])
    cols = [d[0] for d in cur.description]
    return {'snapshots': [dict(zip(cols, r)) for r in cur.fetchall()]}

def handle_get_alerts(db, confirmed=''):
    cur = db.cursor()
    sql = '''SELECT a.id, a.asset_id, a.snapshot_id, a.alert_type, a.alert_detail,
        a.confirmed, a.confirmed_at, a.confirmed_by, a.created_at,
        ass.value, ass.scheme, ass.port
        FROM tamper_alerts a JOIN assets ass ON a.asset_id = ass.id WHERE 1=1'''
    args = []
    if confirmed:
        sql += ' AND a.confirmed = ?'
        args.append(confirmed)
    sql += ' ORDER BY a.created_at DESC LIMIT 100'
    cur.execute(sql, args)
    cols = [d[0] for d in cur.description]
    rows = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        d['asset_url'] = f"{d['scheme']}://{d['value']}:{d['port']}"
        rows.append(d)
    return {'alerts': rows}

def handle_confirm_alert(db, alert_id, data):
    confirmed = int(data.get('confirmed', [0])[0])
    confirmed_by = data.get('confirmed_by', ['manual'])[0]
    now = now_str()
    cur = db.cursor()
    cur.execute('UPDATE tamper_alerts SET confirmed=?, confirmed_at=?, confirmed_by=? WHERE id=?',
        [confirmed, now, confirmed_by, alert_id])
    db.commit()
    return {'status': 'updated'}

def handle_delete_alert(db, alert_id):
    cur = db.cursor()
    cur.execute('DELETE FROM tamper_alerts WHERE id=?', [alert_id])
    db.commit()
    return {'status': 'deleted'}

# ─── IP Scan (no masscan, pure Python) ─────────────────────────────────────────

def scan_ip_range_worker(cidr, range_id):
    """Scan IP range in background thread - pure Python TCP scan"""
    import urllib.request
    try:
        import ipaddress
        network = ipaddress.ip_network(cidr, strict=False)
    except:
        return

    db = get_db()
    cur = db.cursor()
    now = now_str()
    scanned = 0

    for ip in network:
        ip_str = str(ip)
        # Skip common non-web IPs
        last = int(ip_str.split('.')[-1])
        if last in (0, 1, 255):
            continue

        # Try HTTP on 80 and HTTPS on 443
        for port, scheme in [(80, 'http'), (443, 'https')]:
            try:
                url = f'{scheme}://{ip_str}:{port}'
                req = urllib.request.Request(url, headers={'User-Agent': 'Libra-Asset-Scanner/1.0', 'Host': ip_str})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    body = resp.read()
                    status_code = resp.status
                    title = ''
                    m = re.search(r'<title[^>]*>([^<]+)</title>', body.decode('utf-8', errors='ignore'), re.I)
                    if m:
                        title = m.group(1).strip()
                    server = resp.headers.get('Server', '')

                    cur.execute('''INSERT OR REPLACE INTO assets
                        (asset_type, value, port, scheme, title, server_fingerprint, status_code,
                         status, first_seen, last_seen, ip_range_id)
                        VALUES ('ip', ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)''',
                        [ip_str, port, scheme, title, server, status_code, now, now, range_id])
                    db.commit()
                    scanned += 1
                    break  # Found open port, don't try other port
            except:
                pass

    db.close()
    print(f'[IP scan] {cidr}: scanned {scanned} hosts')

def handle_scan_ip(db, data):
    import concurrent.futures
    cidr = data.get('cidr', [''])[0].strip()
    range_id = int(data.get('range_id', [0])[0])
    if not cidr and not range_id:
        return {'error': 'cidr or range_id required'}, 400
    if not cidr and range_id:
        cur = db.cursor()
        cur.execute('SELECT cidr FROM ip_ranges WHERE id=?', [range_id])
        row = cur.fetchone()
        cidr = row[0] if row else ''
    if not cidr:
        return {'error': 'CIDR not found'}, 404
    # Start background scan
    t = threading.Thread(target=scan_ip_range_worker, args=(cidr, range_id), daemon=True)
    t.start()
    return {'status': 'scanning', 'cidr': cidr}

# ─── HTTP Handler ─────────────────────────────────────────────────────────────

def run_server(port=5187):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f'[assets] {self.address_string()} {fmt % args}')

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, PUT, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def do_GET(self):
            db = get_db()
            parsed = urlparse(self.path)
            path = parsed.path
            params = parse_qs(parsed.query)

            try:
                if path == '/api/assets':
                    json_resp(self, handle_assets_list(db, params))
                elif path == '/api/assets/stats':
                    json_resp(self, handle_assets_stats(db))
                elif path == '/api/assets/ip-ranges':
                    json_resp(self, handle_ip_ranges_list(db))
                elif path.startswith('/api/assets/snapshots/'):
                    asset_id = path.split('/')[-1]
                    json_resp(self, handle_get_snapshots(db, asset_id))
                elif path == '/api/assets/alerts':
                    confirmed = params.get('confirmed', [''])[0]
                    json_resp(self, handle_get_alerts(db, confirmed))
                else:
                    json_resp(self, {'error': 'not found'}, 404)
            except Exception as e:
                import traceback
                traceback.print_exc()
                json_resp(self, {'error': str(e)}, 500)
            finally:
                db.close()

        def do_POST(self):
            db = get_db()
            parsed = urlparse(self.path)
            path = parsed.path
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len) if content_len > 0 else b''
            try:
                import json as _json
                data = _json.loads(body) if body else {}
            except:
                data = {}

            try:
                if path == '/api/assets':
                    json_resp(self, handle_create_asset(db, data))
                elif path == '/api/assets/ip-ranges':
                    resp, status = handle_add_ip_range(db, data)
                    json_resp(self, resp, status)
                elif path == '/api/assets/scan/ip':
                    json_resp(self, handle_scan_ip(db, data))
                elif path == '/api/assets/scan/cert':
                    resp, status = handle_import_cert(db, data)
                    json_resp(self, resp, status)
                elif path.startswith('/api/assets/snapshot/'):
                    asset_id = path.split('/')[-1]
                    resp, status = handle_take_snapshot(db, asset_id)
                    json_resp(self, resp, status)
                elif path.startswith('/api/assets/alerts/') and path.endswith('/confirm'):
                    alert_id = path.split('/')[-2]
                    json_resp(self, handle_confirm_alert(db, alert_id, data))
                else:
                    json_resp(self, {'error': 'not found'}, 404)
            except Exception as e:
                import traceback; traceback.print_exc()
                json_resp(self, {'error': str(e)}, 500)
            finally:
                db.close()

        def do_DELETE(self):
            db = get_db()
            path = self.path
            try:
                if path.startswith('/api/assets/ip-ranges/'):
                    range_id = path.split('/')[-1]
                    json_resp(self, handle_delete_ip_range(db, range_id))
                elif path.startswith('/api/assets/alerts/'):
                    alert_id = path.split('/')[-1]
                    json_resp(self, handle_delete_alert(db, alert_id))
                else:
                    json_resp(self, {'error': 'not found'}, 404)
            except Exception as e:
                json_resp(self, {'error': str(e)}, 500)
            finally:
                db.close()

    srv = HTTPServer(('0.0.0.0', port), Handler)
    print(f'[assets] Python asset server running on port {port}')
    srv.serve_forever()

if __name__ == '__main__':
    run_server()
