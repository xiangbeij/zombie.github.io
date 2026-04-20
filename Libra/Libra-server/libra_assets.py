#!/usr/bin/env python3
"""
Libra Assets API v2 - Flask-based HTTP server for asset discovery & monitoring.
Runs on port 5187.
"""
import os
import sys
import sqlite3
import json
import threading
import hashlib
import re
import time
import urllib.parse
import socket
import ssl
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, Response

BASE_DIR = os.environ.get('LIBRA_DIR', '/opt/Libra')
DB_PATH = os.path.join(BASE_DIR, 'Libra.db')
PORT = 5187

app = Flask(__name__)
app.json.ensure_ascii = False

# ─── DB Helpers ─────────────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

def row_to_dict(row):
    if row is None:
        return None
    return dict(zip(row.keys(), row))

def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ─── Assets List ───────────────────────────────────────────────────────────────

@app.route('/api/assets', methods=['GET', 'POST'])
def api_assets():
    db = get_db()
    try:
        if request.method == 'GET':
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 50))
            search = request.args.get('search', '')
            asset_type = request.args.get('type', '')
            status = request.args.get('status', '')
            tags = request.args.get('tags', '')
            offset = (page - 1) * page_size

            where = ['1=1']
            args = []
            if search:
                like = f'%{search}%'
                where.append('(value LIKE ? OR title LIKE ? OR tags LIKE ?)')
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
            rows = [row_to_dict(r) for r in cur.fetchall()]

            return jsonify({
                'assets': rows, 'total': total,
                'page': page, 'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if total > 0 else 0
            })

        else:  # POST - create asset
            data = request.get_json() or {}
            asset_type = data.get('asset_type', '')
            value = data.get('value', '').strip()
            if not asset_type or not value:
                return jsonify({'error': 'asset_type and value required'}), 400

            port = int(data.get('port', 443))
            scheme = data.get('scheme', 'https')
            tags = data.get('tags', '')
            note = data.get('note', '')
            now = now_str()

            cur = db.cursor()
            cur.execute('''INSERT OR REPLACE INTO assets
                (asset_type, value, port, scheme, tags, note, status, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, 'unknown', ?, ?)''',
                [asset_type, value, port, scheme, tags, note, now, now])
            db.commit()
            return jsonify({'id': cur.lastrowid, 'status': 'created'})
    finally:
        db.close()

# ─── Asset Stats (enhanced with threat summaries) ───────────────────────────────

@app.route('/api/assets/stats', methods=['GET'])
def api_assets_stats():
    db = get_db()
    try:
        cur = db.cursor()
        total = cur.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
        by_type = {r[0]: r[1] for r in cur.execute('SELECT asset_type, COUNT(*) FROM assets GROUP BY asset_type')}
        by_status = {r[0]: r[1] for r in cur.execute('SELECT status, COUNT(*) FROM assets GROUP BY status')}
        
        # Threat summary from scan results stored in task result JSON
        threat_summary = _get_threat_summary(cur)

        return jsonify({
            'total_assets': total,
            'by_type': by_type,
            'by_status': by_status,
            'total_snapshots': cur.execute('SELECT COUNT(*) FROM asset_snapshots').fetchone()[0],
            'pending_alerts': cur.execute("SELECT COUNT(*) FROM tamper_alerts WHERE confirmed=0").fetchone()[0],
            'ip_ranges': cur.execute('SELECT COUNT(*) FROM ip_ranges').fetchone()[0],
            'cert_imports': cur.execute('SELECT COUNT(*) FROM cert_assets').fetchone()[0],
            'threat_summary': threat_summary,
        })
    finally:
        db.close()

def _get_threat_summary(cur):
    """Get threat aggregation from in-memory task results"""
    # Tasks are stored in memory in the Go process, not accessible from here
    # So we aggregate from any stored scan_results if available
    # Return zeros as placeholder - the Go API's /api/stats will be enhanced instead
    return {'total_blacklinks': 0, 'total_backdoors': 0, 'total_violations': 0, 'week_blacklinks': 0}

@app.route('/api/assets/export', methods=['GET'])
def api_export_assets():
    """导出全部资产为 CSV"""
    import csv
    import io
    db = get_db()
    try:
        cur = db.cursor()
        rows = cur.execute('''
            SELECT asset_type, value, port, scheme, title, server_fingerprint,
                   status_code, status, tags, note, first_seen, last_seen
            FROM assets ORDER BY first_seen DESC
        ''').fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['类型', '资产值', '端口', '协议', '网站标题', '服务器', '状态码', '状态', '标签', '备注', '首次发现', '最后发现'])
        for r in rows:
            writer.writerow(r)
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
                       headers={'Content-Disposition': 'attachment; filename=assets.csv'})
    finally:
        db.close()

# ─── Threat Summary API (from Go API's in-memory task store) ───────────────────

@app.route('/api/assets/threat-summary', methods=['GET'])
def api_threat_summary():
    """Aggregated threat data from all completed scan tasks.
    Reads from Libra.db if scan results are archived there,
    otherwise returns mock data for now."""
    db = get_db()
    try:
        cur = db.cursor()
        
        # Try to read scan results from db if there's a scan_results table
        # For now, return aggregated threat counts
        total_blacklinks = 0
        total_backdoors = 0
        total_violations = 0
        
        # Last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if there's archived data
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        result = {
            'total_blacklinks': total_blacklinks,
            'total_backdoors': total_backdoors,
            'total_violations': total_violations,
            'week_blacklinks': 0,
            'week_backdoors': 0,
            'week_violations': 0,
            'by_severity': {'high': 0, 'medium': 0, 'low': 0},
            'top_threats': [],  # Top threat patterns found
        }
        
        return jsonify(result)
    finally:
        db.close()

# ─── Dashboard Aggregated Stats ────────────────────────────────────────────────

@app.route('/api/dashboard/stats', methods=['GET'])
def api_dashboard_stats():
    """Enhanced dashboard stats combining scan results + assets + alerts"""
    db = get_db()
    try:
        cur = db.cursor()
        
        # Basic scan stats
        stats_rows = cur.execute("SELECT total, success, error, running FROM stats LIMIT 1").fetchall()
        if stats_rows:
            total, success, error, running = stats_rows[0]
        else:
            total, success, error, running = 0, 0, 0, 0
        
        # Threat aggregation from scan history
        # We need to look at task results - but they're in Go memory
        # For now, return basic stats
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Scan history aggregation
        recent_tasks = cur.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'success' AND finished_at > ?", 
            [week_ago]).fetchone()[0]
        recent_errors = cur.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'error' AND finished_at > ?",
            [week_ago]).fetchone()[0]
        
        # Asset stats
        total_assets = cur.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
        active_assets = cur.execute("SELECT COUNT(*) FROM assets WHERE status='active'").fetchone()[0]
        pending_alerts = cur.execute("SELECT COUNT(*) FROM tamper_alerts WHERE confirmed=0").fetchone()[0]
        
        return jsonify({
            'scan': {
                'total': total, 'success': success, 'error': error, 'running': running,
                'recent_success': recent_tasks, 'recent_errors': recent_errors
            },
            'assets': {
                'total': total_assets, 'active': active_assets,
            },
            'alerts': {
                'pending': pending_alerts,
            },
            # Threat aggregation - will be populated when Go API exposes scan results
            'threats': {
                'total_blacklinks': 0, 'total_backdoors': 0, 'total_violations': 0,
                'week_blacklinks': 0, 'week_backdoors': 0, 'week_violations': 0,
            }
        })
    finally:
        db.close()

# ─── Scan History (paginated) ──────────────────────────────────────────────────

@app.route('/api/tasks/paginated', methods=['GET'])
def api_tasks_paginated():
    """Paginated scan history with threat counts"""
    db = get_db()
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        status_filter = request.args.get('status', '')
        search = request.args.get('search', '')
        offset = (page - 1) * page_size

        where = ['1=1']
        args = []
        if status_filter:
            where.append('status = ?')
            args.append(status_filter)
        if search:
            where.append('url LIKE ?')
            args.append(f'%{search}%')

        where_sql = ' AND '.join(where)
        cur = db.cursor()

        cur.execute(f'SELECT COUNT(*) FROM tasks WHERE {where_sql}', args)
        total = cur.fetchone()[0]

        sql = f'''SELECT id, url, scan_type, status, progress, error, created_at, started_at, finished_at
            FROM tasks WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?'''
        args.extend([page_size, offset])
        cur.execute(sql, args)
        
        tasks = []
        for r in cur.fetchall():
            row = row_to_dict(r)
            # Extract threat counts from result JSON if present
            row['blacklink_count'] = 0
            row['backdoor_count'] = 0
            row['violative_count'] = 0
            tasks.append(row)

        return jsonify({
            'tasks': tasks, 'total': total,
            'page': page, 'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size if total > 0 else 0
        })
    finally:
        db.close()

# ─── IP Ranges ─────────────────────────────────────────────────────────────────

@app.route('/api/assets/ip-ranges', methods=['GET', 'POST'])
def api_ip_ranges():
    db = get_db()
    try:
        if request.method == 'GET':
            cur = db.cursor()
            cur.execute('SELECT id, cidr, description, tags, created_at FROM ip_ranges ORDER BY created_at DESC')
            return jsonify({'ip_ranges': [row_to_dict(r) for r in cur.fetchall()]})
        else:
            data = request.get_json() or {}
            cidr = data.get('cidr', '').strip()
            if not cidr:
                return jsonify({'error': 'cidr required'}), 400
            try:
                import ipaddress
                ipaddress.ip_network(cidr, strict=False)
            except:
                return jsonify({'error': 'invalid CIDR'}), 400

            now = now_str()
            cur = db.cursor()
            try:
                cur.execute('INSERT INTO ip_ranges (cidr, description, tags, created_at) VALUES (?, ?, ?, ?)',
                    [cidr, data.get('description', ''), data.get('tags', ''), now])
                db.commit()
                return jsonify({'id': cur.lastrowid, 'status': 'created'})
            except sqlite3.IntegrityError:
                return jsonify({'error': 'CIDR already exists'}), 409
    finally:
        db.close()

@app.route('/api/assets/ip-ranges/<int:range_id>', methods=['DELETE'])
def api_delete_ip_range(range_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM ip_ranges WHERE id = ?', [range_id])
        db.commit()
        return jsonify({'status': 'deleted'})
    finally:
        db.close()

# ─── Scan IP Range ─────────────────────────────────────────────────────────────

def _scan_ip(cidr, range_id):
    """Background IP scan worker"""
    import urllib.request
    try:
        import ipaddress
    except ImportError:
        return

    db = get_db()
    cur = db.cursor()
    now = now_str()
    scanned = 0

    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except:
        db.close()
        return

    for ip in network:
        ip_str = str(ip)
        last = int(ip_str.rsplit('.', 1)[-1])
        if last in (0, 1, 255):
            continue

        for port, scheme in [(80, 'http'), (443, 'https')]:
            try:
                url = f'{scheme}://{ip_str}:{port}'
                req = urllib.request.Request(url,
                    headers={'User-Agent': 'Libra-Asset-Scanner/1.0', 'Host': ip_str})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    body = resp.read()
                    status_code = resp.status
                    title = ''
                    m = re.search(r'<title[^>]*>([^<]+)</title>',
                                  body.decode('utf-8', errors='ignore'), re.I)
                    if m:
                        title = m.group(1).strip()[:200]
                    server = resp.headers.get('Server', '')[:100]

                    cur.execute('''INSERT OR REPLACE INTO assets
                        (asset_type, value, port, scheme, title, server_fingerprint, status_code,
                         status, first_seen, last_seen, ip_range_id)
                        VALUES ('ip', ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)''',
                        [ip_str, port, scheme, title, server, status_code, now, now, range_id])
                    db.commit()
                    scanned += 1
                    break
            except:
                pass

    db.close()
    print(f'[IP scan] {cidr}: found {scanned} web hosts')

@app.route('/api/assets/scan/ip', methods=['POST'])
def api_scan_ip():
    data = request.get_json() or {}
    cidr = data.get('cidr', '').strip()
    range_id = int(data.get('range_id', 0))

    if not cidr and not range_id:
        return jsonify({'error': 'cidr or range_id required'}), 400

    if not cidr and range_id:
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('SELECT cidr FROM ip_ranges WHERE id=?', [range_id])
            row = cur.fetchone()
            cidr = row[0] if row else ''
        finally:
            db.close()
        if not cidr:
            return jsonify({'error': 'IP range not found'}), 404

    t = threading.Thread(target=_scan_ip, args=(cidr, range_id), daemon=True)
    t.start()
    return jsonify({'status': 'scanning', 'cidr': cidr, 'message': 'Scan started in background'})

# ─── Domain Crawler ─────────────────────────────────────────────────────────────

def _crawl_domain(domain, range_id=0, depth=2):
    """Background domain crawler - discovers subdomains"""
    import urllib.request

    db = get_db()
    cur = db.cursor()
    now = now_str()
    found = 0

    def try_url(target_domain, scheme='https', port=443, path='/'):
        if port in (80, 443):
            url = f'{scheme}://{target_domain}{path}'
        else:
            url = f'{scheme}://{target_domain}:{port}{path}'
        try:
            req = urllib.request.Request(url,
                headers={'User-Agent': 'Libra-Asset-Crawler/1.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = resp.read()
                status = resp.status
                title = ''
                m = re.search(r'<title[^>]*>([^<]+)</title>',
                              body.decode('utf-8', errors='ignore'), re.I)
                if m:
                    title = m.group(1).strip()[:200]
                server = resp.headers.get('Server', '')[:100]

                cur.execute('''INSERT OR IGNORE INTO assets
                    (asset_type, value, port, scheme, title, server_fingerprint, status_code,
                     status, first_seen, last_seen, ip_range_id)
                    VALUES ('domain', ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)''',
                    [target_domain, port, scheme, title, server, status, now, now, range_id])
                if cur.rowcount > 0:
                    nonlocal found
                    found += 1
                db.commit()
                return body
        except:
            return None

    # Try main domain
    body = try_url(domain, 'https', 443) or try_url(domain, 'http', 80)

    if body and depth > 0:
        try:
            html = body.decode('utf-8', errors='ignore')
            hrefs = re.findall(r'href=["\'](https?://[^"\'>\s]+)["\']', html, re.I)
            for href in hrefs[:80]:
                try:
                    parsed = urllib.parse.urlparse(href)
                    href_domain = parsed.netloc.split(':')[0]
                    if href_domain == domain or href_domain.endswith('.' + domain):
                        if href_domain != domain:
                            sub_port = 443
                            sub_scheme = 'https'
                            if ':' in parsed.netloc:
                                try:
                                    sub_port = int(parsed.netloc.split(':')[1])
                                except:
                                    pass
                            cur.execute('''INSERT OR IGNORE INTO assets
                                (asset_type, value, port, scheme, status, first_seen, last_seen)
                                VALUES ('domain', ?, ?, ?, 'unknown', ?, ?)''',
                                [href_domain, sub_port, sub_scheme, now, now])
                            if cur.rowcount > 0:
                                found += 1
                            db.commit()
                except:
                    pass
        except:
            pass

    # Try common subdomains
    common = ['www', 'mail', 'ftp', 'admin', 'blog', 'm', 'app', 'api', 'cdn', 'static',
              'shop', 'student', 'jw', 'xk', 'lib', 'oa', 'vpn', 'git', 'www1', 'web']
    for prefix in common[:12]:
        subdomain = f'{prefix}.{domain}'
        if try_url(subdomain, 'https', 443):
            found += 1
        if try_url(subdomain, 'http', 80):
            found += 1

    db.close()
    print(f'[Domain crawler] {domain}: found {found} assets')

@app.route('/api/assets/scan/domain', methods=['POST'])
def api_crawl_domain():
    data = request.get_json() or {}
    domain = data.get('domain', '').strip()
    if not domain:
        return jsonify({'error': 'domain required'}), 400
    domain = re.sub(r'^https?://', '', domain).split('/')[0].split(':')[0]
    range_id = int(data.get('range_id', 0))
    depth = int(data.get('depth', 2))

    t = threading.Thread(target=_crawl_domain, args=(domain, range_id, depth), daemon=True)
    t.start()
    return jsonify({'status': 'scanning', 'domain': domain, 'message': f'Crawling {domain}...'})

# ─── Certificate Import ─────────────────────────────────────────────────────────

@app.route('/api/assets/scan/cert', methods=['POST'])
def api_import_cert():
    data = request.get_json() or {}
    pem_cert = data.get('public_key', '').strip()
    if not pem_cert:
        return jsonify({'error': 'public_key required'}), 400

    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        import base64

        lines = pem_cert.splitlines()
        start = -1
        for i, l in enumerate(lines):
            if l.startswith('-----BEGIN CERTIFICATE-----'):
                start = i
                break
        if start < 0:
            return jsonify({'error': 'invalid PEM certificate'}), 400

        pem_data = ''.join(l for l in lines[start:] if not l.startswith('-----'))
        cert_bytes = base64.b64decode(pem_data)

        cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
        sha1_fingerprint = cert.fingerprint(hashlib.sha1()).hexdigest().upper()

        domains = []
        try:
            san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            domains = san_ext.value.get_values_for_type(x509.DNSName)
        except:
            pass

        try:
            cn_attr = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            if cn_attr and not domains:
                domains = [cn_attr[0].value]
        except:
            pass

        now = now_str()
        db = get_db()
        try:
            cur = db.cursor()
            cur.execute('''INSERT OR REPLACE INTO cert_assets
                (cert_sha1, cert_subject, cert_issuer, cert_not_before, cert_not_after,
                 san_count, domains, raw_cert, imported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                [sha1_fingerprint,
                 _get_cn(cert.subject),
                 _get_cn(cert.issuer),
                 str(cert.not_valid_before_utc)[:10],
                 str(cert.not_valid_after_utc)[:10],
                 len(domains), json.dumps(domains), pem_cert, now])
            db.commit()

            cur.execute('SELECT id FROM cert_assets WHERE cert_sha1=?', [sha1_fingerprint])
            row = cur.fetchone()
            cert_id = row[0] if row else 0

            added = 0
            for domain in domains:
                domain = domain.strip()
                if not domain:
                    continue
                try:
                    cur.execute('''INSERT OR IGNORE INTO assets
                        (asset_type, value, port, scheme, cert_id, status, first_seen, last_seen)
                        VALUES ('domain', ?, 443, 'https', ?, 'unknown', ?, ?)''',
                        [domain, cert_id, now, now])
                    if cur.rowcount > 0:
                        added += 1
                except:
                    pass
            db.commit()
            return jsonify({
                'cert_sha1': sha1_fingerprint,
                'domains': domains[:50],
                'domain_count': added,
                'status': 'imported'
            })
        finally:
            db.close()
    except ImportError:
        return jsonify({'error': 'cryptography not installed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 400

def _get_cn(name):
    try:
        from cryptography.x509.oid import NameOID
        attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
        return attrs[0].value if attrs else ''
    except:
        return ''

# ─── Snapshots ─────────────────────────────────────────────────────────────────

@app.route('/api/assets/snapshot/<int:asset_id>', methods=['POST'])
def api_take_snapshot(asset_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('SELECT value, scheme, port FROM assets WHERE id=?', [asset_id])
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'asset not found'}), 404

        value, scheme, port = row[0], row[1], row[2]
        url = f'{scheme}://{value}:{port}' if not ((scheme == 'https' and port == 443) or (scheme == 'http' and port == 80)) else f'{scheme}://{value}'

        try:
            import urllib.request
            req = urllib.request.Request(url, headers={'User-Agent': 'Libra-Asset-Scanner/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                status_code = resp.status
        except Exception as e:
            return jsonify({'error': f'fetch failed: {e}'}), 500

        content_hash = hashlib.sha1(body).hexdigest()
        title = ''
        m = re.search(r'<title[^>]*>([^<]+)</title>', body.decode('utf-8', errors='ignore'), re.I)
        if m:
            title = m.group(1).strip()[:200]

        keywords = ''
        km = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']', body.decode('utf-8', errors='ignore'), re.I)
        if km:
            keywords = km.group(1)[:500]

        desc = ''
        dm = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', body.decode('utf-8', errors='ignore'), re.I)
        if dm:
            desc = dm.group(1)[:500]

        cur.execute('SELECT content_hash FROM asset_snapshots WHERE asset_id=? ORDER BY scanned_at DESC LIMIT 1', [asset_id])
        prev = cur.fetchone()
        prev_hash = prev[0] if prev else ''

        diff_ratio = 0.0
        if prev_hash and prev_hash != content_hash:
            diff_ratio = min(1.0, sum(a != b for a, b in zip(prev_hash, content_hash)) / max(len(prev_hash), 1))

        now = now_str()
        cur.execute('''INSERT INTO asset_snapshots
            (asset_id, url, title, keywords, description, content_hash, diff_ratio, scanned_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            [asset_id, url, title, keywords, desc, content_hash, diff_ratio, now])
        snapshot_id = cur.lastrowid

        cur.execute('UPDATE assets SET last_seen=?, content_hash=?, title=?, status_code=? WHERE id=?',
            [now, content_hash, title, status_code, asset_id])

        if diff_ratio > 0.3:
            detail = json.dumps({'diff_ratio': round(diff_ratio, 3)}, ensure_ascii=False)
            cur.execute('''INSERT INTO tamper_alerts
                (asset_id, snapshot_id, alert_type, alert_detail, created_at)
                VALUES (?, ?, 'content_changed', ?, ?)''',
                [asset_id, snapshot_id, detail, now])

        db.commit()
        return jsonify({'snapshot_id': snapshot_id, 'content_hash': content_hash, 'diff_ratio': diff_ratio})
    finally:
        db.close()

@app.route('/api/assets/snapshots/<int:asset_id>', methods=['GET'])
def api_get_snapshots(asset_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('''SELECT id, asset_id, url, title, keywords, description, content_hash,
            diff_ratio, scanned_at FROM asset_snapshots WHERE asset_id=? ORDER BY scanned_at DESC LIMIT 30''',
            [asset_id])
        return jsonify({'snapshots': [row_to_dict(r) for r in cur.fetchall()]})
    finally:
        db.close()

# ─── Tamper Alerts ─────────────────────────────────────────────────────────────

@app.route('/api/assets/alerts', methods=['GET'])
def api_get_alerts():
    db = get_db()
    try:
        confirmed = request.args.get('confirmed', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        offset = (page - 1) * page_size

        sql = '''SELECT a.id, a.asset_id, a.snapshot_id, a.alert_type, a.alert_detail,
            a.confirmed, a.confirmed_at, a.confirmed_by, a.created_at,
            ass.value, ass.scheme, ass.port
            FROM tamper_alerts a JOIN assets ass ON a.asset_id = ass.id WHERE 1=1'''
        args = []
        if confirmed:
            sql += ' AND a.confirmed = ?'
            args.append(confirmed)
        sql += ' ORDER BY a.created_at DESC LIMIT ? OFFSET ?'
        args.extend([page_size, offset])

        cur = db.cursor()
        cur.execute(sql, args)
        rows = []
        for r in cur.fetchall():
            d = row_to_dict(r)
            d['asset_url'] = f"{d['scheme']}://{d['value']}:{d['port']}"
            rows.append(d)

        cur.execute(f'SELECT COUNT(*) FROM tamper_alerts WHERE 1=1' + (' AND confirmed=' + confirmed if confirmed else ''))
        total = cur.fetchone()[0]

        return jsonify({'alerts': rows, 'total': total, 'page': page, 'page_size': page_size})
    finally:
        db.close()

@app.route('/api/assets/alerts/<int:alert_id>/confirm', methods=['PUT'])
def api_confirm_alert(alert_id):
    data = request.get_json() or {}
    confirmed = int(data.get('confirmed', 0))
    confirmed_by = data.get('confirmed_by', 'manual')
    now = now_str()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('UPDATE tamper_alerts SET confirmed=?, confirmed_at=?, confirmed_by=? WHERE id=?',
            [confirmed, now, confirmed_by, alert_id])
        db.commit()
        return jsonify({'status': 'updated'})
    finally:
        db.close()

@app.route('/api/assets/alerts/<int:alert_id>', methods=['DELETE'])
def api_delete_alert(alert_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute('DELETE FROM tamper_alerts WHERE id=?', [alert_id])
        db.commit()
        return jsonify({'status': 'deleted'})
    finally:
        db.close()

# ─── CORS & Health ─────────────────────────────────────────────────────────────

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, PUT, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({'status': 'ok', 'service': 'Libra Assets API v2', 'version': '2.0'})

if __name__ == '__main__':
    print(f'[*] Libra Assets API v2 starting on port {PORT}')
    app.run(host='0.0.0.0', port=PORT, threaded=True)
