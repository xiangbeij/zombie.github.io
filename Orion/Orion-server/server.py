#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Orion-server - Flask API Server
鍖呭惈: 鎵归噺鎵弿 / 瀹氭椂浠诲姟 / 鎶ュ憡瀵煎嚭
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import json
import os
import sys
import uuid
import threading
import time
import csv
from datetime import datetime, timedelta
from io import StringIO, BytesIO
import re

# 鈹€鈹€ APScheduler for scheduled tasks 鈹€鈹€
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    print("[WARN] apscheduler not installed, scheduled tasks disabled. Run: pip install apscheduler")

# 鈹€鈹€ Report export 鈹€鈹€
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARN] reportlab not installed, PDF export disabled. Run: pip install reportlab")

app = Flask(__name__)
CORS(app)

# 鈹€鈹€ Paths 鈹€鈹€
BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
ORION_PY = os.path.join(BASE_DIR, 'orion.py')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# 鈹€鈹€ In-memory stores 鈹€鈹€
TASKS = {}
TASK_RESULTS = {}
BATCH_QUEUES = {}        # batch_id -> list of task_ids
SCHEDULED_JOBS = {}      # job_id -> {id, name, url, scan_type, cron_expr, enabled, last_run}
scheduler = None


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?# Helpers
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
def _run_orion_scan(task_id, url, scan_type):
    """Execute Orion scan in background thread."""
    import re
    ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = BASE_DIR
        result = subprocess.run(
            [sys.executable, ORION_PY, '-u', url, '-t', scan_type],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=BASE_DIR,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        # Strip ANSI escape sequences from stdout
        output = ANSI_RE.sub('', result.stdout)
        # Parse JSON from stdout (last JSON-like block)
        parsed = None
        for line in reversed(output.splitlines()):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    parsed = json.loads(line)
                    break
                except:
                    pass

        if parsed:
            TASK_RESULTS[task_id] = parsed
            TASKS[task_id]['status'] = 'success'
        else:
            # Debug: write raw output to file
            debug_file = f'/tmp/orion_scan_debug_{task_id}.txt'
            with open(debug_file, 'w') as f:
                f.write(f'returncode={result.returncode}\n')
                f.write(f'stdout({len(result.stdout)} bytes):\n{result.stdout[-1000:]}\n')
                f.write(f'stderr({len(result.stderr)} bytes):\n{result.stderr[-500:]}\n')
            err = result.stderr[:300] if result.stderr else 'Parse error (no stderr)'
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['error'] = f'Parse error (check {debug_file})'
    except subprocess.TimeoutExpired:
        TASKS[task_id]['status'] = 'timeout'
        TASKS[task_id]['error'] = 'Scan timeout (>10min)'
    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        TASKS[task_id]['error'] = str(e)
    finally:
        TASKS[task_id]['finished_at'] = datetime.now().isoformat()


def _make_task(url, scan_type):
    task_id = str(uuid.uuid4())[:8]
    TASKS[task_id] = {
        'id': task_id,
        'url': url,
        'scan_type': scan_type,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'progress': 0,
        'batch_id': None,
    }
    t = threading.Thread(target=_run_orion_scan, args=(task_id, url, scan_type), daemon=True)
    t.start()
    return task_id


def _get_task_summary(result):
    """Extract a clean summary dict from Orion result."""
    if not result:
        return {}
    return {
        'taskurl': result.get('taskurl', ''),
        'tasktype': result.get('tasktype', ''),
        'datetime': result.get('datetime', ''),
        'status': result.get('status', ''),
        'blacklink_count': len(result.get('blacklink_list', [])),
        'backdoor_count': len(result.get('backdoor_list', [])),
        'violativelink_count': len(result.get('violativelink_list', [])),
        'diedlink_count': len(result.get('diedlink_list', [])),
        'blacklink_list': result.get('blacklink_list', []),
        'backdoor_list': result.get('backdoor_list', []),
        'violativelink_list': result.get('violativelink_list', []),
        'diedlink_list': result.get('diedlink_list', []),
    }


def _trigger_scan(url, scan_type):
    """Trigger a scan and return task_id immediately."""
    return _make_task(url, scan_type)


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?# Core Scan API
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
@app.route('/api/scan', methods=['POST'])
def start_scan():
    data = request.json
    url = data.get('url', '').strip()
    scan_type = data.get('scan_type', 'HomePage_Scan')
    if not url:
        return jsonify({'status': 'error', 'message': 'URL required'}), 400
    if scan_type not in ['HomePage_Scan', 'SecondPage_Scan', 'AllSite_Scan', 'CustomPage_Scan']:
        return jsonify({'status': 'error', 'message': 'Invalid scan_type'}), 400

    task_id = _make_task(url, scan_type)
    return jsonify({'status': 'accepted', 'task_id': task_id, 'message': f'Scan started: {scan_type} -> {url}'})


@app.route('/api/scan/<task_id>', methods=['GET'])
def get_scan_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    result = TASK_RESULTS.get(task_id, {})
    return jsonify({**task, 'result': result})


@app.route('/api/scan/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    TASKS.pop(task_id, None)
    TASK_RESULTS.pop(task_id, None)
    return jsonify({'status': 'deleted'})


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    limit = int(request.args.get('limit', 100))
    tasks_list = []
    for tid, task in reversed(list(TASKS.items())):
        task_item = {**task}
        if tid in TASK_RESULTS:
            task_item['result'] = TASK_RESULTS[tid]
        tasks_list.append(task_item)
        if len(tasks_list) >= limit:
            break
    return jsonify({'tasks': tasks_list, 'total': len(TASKS)})


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?# Batch Scan API
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
@app.route('/api/batch', methods=['POST'])
def create_batch():
    """Create a batch scan with multiple URLs."""
    data = request.json
    urls = data.get('urls', [])
    scan_type = data.get('scan_type', 'HomePage_Scan')

    if not urls:
        return jsonify({'status': 'error', 'message': 'URLs required'}), 400
    if not isinstance(urls, list):
        return jsonify({'status': 'error', 'message': 'urls must be a list'}), 400

    batch_id = str(uuid.uuid4())[:8]
    task_ids = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        task_id = _make_task(url, scan_type)
        TASKS[task_id]['batch_id'] = batch_id
        task_ids.append(task_id)

    BATCH_QUEUES[batch_id] = {
        'id': batch_id,
        'task_ids': task_ids,
        'total': len(task_ids),
        'created_at': datetime.now().isoformat(),
        'scan_type': scan_type,
    }
    return jsonify({
        'status': 'accepted',
        'batch_id': batch_id,
        'task_ids': task_ids,
        'total': len(task_ids),
        'message': f'Batch scan created with {len(task_ids)} URLs'
    })


@app.route('/api/batch/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    batch = BATCH_QUEUES.get(batch_id)
    if not batch:
        return jsonify({'status': 'error', 'message': 'Batch not found'}), 404

    completed = 0
    success = 0
    error = 0
    running = 0
    for tid in batch['task_ids']:
        s = TASKS.get(tid, {}).get('status', 'unknown')
        if s in ('success', 'error', 'timeout'):
            completed += 1
        if s == 'success':
            success += 1
        elif s in ('error', 'timeout'):
            error += 1
        elif s in ('pending', 'running'):
            running += 1

    # Collect results for completed tasks
    results = {}
    for tid in batch['task_ids']:
        if tid in TASK_RESULTS:
            results[tid] = _get_task_summary(TASK_RESULTS[tid])
            results[tid]['status'] = TASKS.get(tid, {}).get('status', '')

    return jsonify({
        **batch,
        'completed': completed,
        'success': success,
        'error': error,
        'running': running,
        'pending': batch['total'] - completed - running,
        'results': results,
    })


@app.route('/api/batch', methods=['GET'])
def list_batches():
    return jsonify({'batches': list(BATCH_QUEUES.values())})


@app.route('/api/batch/<batch_id>', methods=['DELETE'])
def delete_batch(batch_id):
    batch = BATCH_QUEUES.pop(batch_id, None)
    if not batch:
        return jsonify({'status': 'error', 'message': 'Batch not found'}), 404
    for tid in batch['task_ids']:
        TASKS.pop(tid, None)
        TASK_RESULTS.pop(tid, None)
    return jsonify({'status': 'deleted'})


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?# Scheduled Scan API
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
def _run_scheduled_job(job_id):
    job = SCHEDULED_JOBS.get(job_id)
    if not job or not job.get('enabled'):
        return
    task_id = _trigger_scan(job['url'], job['scan_type'])
    SCHEDULED_JOBS[job_id]['last_run'] = datetime.now().isoformat()
    SCHEDULED_JOBS[job_id]['last_task_id'] = task_id

    # Store result back
    def wait_and_store():
        time.sleep(5)
        if task_id in TASK_RESULTS:
            SCHEDULED_JOBS[job_id]['last_result'] = _get_task_summary(TASK_RESULTS[task_id])

    threading.Thread(target=wait_and_store, daemon=True).start()


def _setup_scheduler():
    global scheduler
    if not SCHEDULER_AVAILABLE:
        return
    scheduler = BackgroundScheduler()
    scheduler.start()
    _reschedule_all()


def _reschedule_all():
    if not scheduler:
        return
    # Remove existing scan jobs
    for job in scheduler.get_jobs():
        if job.id.startswith('orion_scan_'):
            scheduler.remove_job(job.id)
    # Re-add all enabled jobs
    for job_id, job in SCHEDULED_JOBS.items():
        if job.get('enabled'):
            _add_scheduler_job(job_id, job)


def _add_scheduler_job(job_id, job):
    if not scheduler or not SCHEDULER_AVAILABLE:
        return
    expr = job['cron_expr']
    # Parse cron: "0 H */d ..." or simple "*/5 * * * *"
    try:
        if expr == 'hourly':
            scheduler.add_job(_run_scheduled_job, 'cron', minute=0, id=f'orion_scan_{job_id}', args=[job_id])
        elif expr == 'daily':
            scheduler.add_job(_run_scheduled_job, 'cron', hour=0, minute=0, id=f'orion_scan_{job_id}', args=[job_id])
        elif expr == 'weekly':
            scheduler.add_job(_run_scheduled_job, 'cron', day_of_week='mon', hour=0, minute=0, id=f'orion_scan_{job_id}', args=[job_id])
        else:
            # Try as literal cron expression
            parts = expr.split()
            if len(parts) == 5:
                scheduler.add_job(_run_scheduled_job, 'cron', minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4], id=f'orion_scan_{job_id}', args=[job_id])
            else:
                scheduler.add_job(_run_scheduled_job, 'cron', minute=parts[0], hour=parts[1], id=f'orion_scan_{job_id}', args=[job_id])
    except Exception as e:
        print(f"[SCHEDULER] Failed to add job {job_id}: {e}")


@app.route('/api/schedule', methods=['POST'])
def create_schedule():
    data = request.json
    name = data.get('name', '').strip()
    url = data.get('url', '').strip()
    scan_type = data.get('scan_type', 'HomePage_Scan')
    cron_expr = data.get('cron_expr', 'hourly')  # hourly/daily/weekly or cron string

    if not url or not name:
        return jsonify({'status': 'error', 'message': 'name and url required'}), 400

    job_id = str(uuid.uuid4())[:8]
    SCHEDULED_JOBS[job_id] = {
        'id': job_id,
        'name': name,
        'url': url,
        'scan_type': scan_type,
        'cron_expr': cron_expr,
        'enabled': True,
        'created_at': datetime.now().isoformat(),
        'last_run': None,
        'last_task_id': None,
        'last_result': None,
    }

    _add_scheduler_job(job_id, SCHEDULED_JOBS[job_id])
    return jsonify({'status': 'created', 'job': SCHEDULED_JOBS[job_id]})


@app.route('/api/schedule', methods=['GET'])
def list_schedules():
    return jsonify({'jobs': list(SCHEDULED_JOBS.values())})


@app.route('/api/schedule/<job_id>', methods=['PUT'])
def update_schedule(job_id):
    job = SCHEDULED_JOBS.get(job_id)
    if not job:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404

    data = request.json
    for field in ['name', 'url', 'scan_type', 'cron_expr', 'enabled']:
        if field in data:
            job[field] = data[field]

    _reschedule_all()
    return jsonify({'status': 'updated', 'job': job})


@app.route('/api/schedule/<job_id>', methods=['DELETE'])
def delete_schedule(job_id):
    job = SCHEDULED_JOBS.pop(job_id, None)
    if not job:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404
    if scheduler:
        try:
            scheduler.remove_job(f'orion_scan_{job_id}')
        except:
            pass
    return jsonify({'status': 'deleted'})


@app.route('/api/schedule/<job_id>/run', methods=['POST'])
def trigger_schedule_now(job_id):
    job = SCHEDULED_JOBS.get(job_id)
    if not job:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404
    threading.Thread(target=_run_scheduled_job, args=[job_id], daemon=True).start()
    return jsonify({'status': 'triggered', 'job_id': job_id})


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?# Report Export API
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
@app.route('/api/report/<task_id>', methods=['GET'])
def export_report(task_id):
    """Export scan result as PDF or JSON."""
    fmt = request.args.get('format', 'json')
    result = TASK_RESULTS.get(task_id)
    task = TASKS.get(task_id, {})

    if not result:
        return jsonify({'status': 'error', 'message': 'Result not found'}), 404

    summary = _get_task_summary(result)
    summary['task_id'] = task_id

    if fmt == 'json':
        return jsonify(summary)

    elif fmt == 'csv':
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['Orion Scan Report'])
        writer.writerow(['鐩爣绔欑偣', summary['taskurl']])
        writer.writerow(['鎵弿绫诲瀷', summary['tasktype']])
        writer.writerow(['鎵弿鏃堕棿', summary['datetime']])
        writer.writerow([])

        # Blacklink
        if summary['blacklink_list']:
            writer.writerow(['绫诲瀷', '闂鍦板潃', '璇︽儏', '鏉ユ簮'])
            for item in summary['blacklink_list']:
                for link in item.get('blacklinkres', []):
                    writer.writerow(['榛戦摼', item['url'], link, ','.join(item.get('master', []))])
            writer.writerow([])

        if summary['backdoor_list']:
            writer.writerow(['绫诲瀷', '闂鍦板潃', '鐗瑰緛', '鏉ユ簮'])
            for item in summary['backdoor_list']:
                for bk in item.get('backdoorres', []):
                    writer.writerow(['鍚庨棬', item['url'], bk, ','.join(item.get('master', []))])
            writer.writerow([])

        if summary['violativelink_list']:
            writer.writerow(['绫诲瀷', '闂鍦板潃', '鍐呭', '鏉ユ簮'])
            for item in summary['violativelink_list']:
                for v in item.get('violativelinkres', []):
                    writer.writerow(['杩濊', item['url'], v, ','.join(item.get('master', []))])
            writer.writerow([])

        if summary['diedlink_list']:
            writer.writerow(['绫诲瀷', '澶辨晥鍦板潃', '鐘舵€佺爜', '鏉ユ簮'])
            for item in summary['diedlink_list']:
                writer.writerow(['姝婚摼', item['url'], item.get('status_code', ''), ','.join(item.get('master', []))])

        output.seek(0)
        return send_file(
            BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'orion_report_{task_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
        )

    elif fmt == 'pdf':
        if not REPORTLAB_AVAILABLE:
            return jsonify({'status': 'error', 'message': 'PDF export requires reportlab. Run: pip install reportlab'}), 501

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = styles['Title']
        title_style.textColor = colors.HexColor('#1a1a2e')
        story.append(Paragraph(f'Orion 瀹夊叏妫€娴嬫姤鍛?, styles['Title']))
        story.append(Spacer(1, 0.3*cm))

        # Meta
        meta_data = [
            ['鐩爣绔欑偣', summary['taskurl']],
            ['鎵弿绫诲瀷', summary['tasktype']],
            ['鎵弿鏃堕棿', summary['datetime']],
            ['鎶ュ憡鐢熸垚', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ]
        meta_table = Table(meta_data, colWidths=[3*cm, 12*cm])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f0f5')),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.5*cm))

        # Summary
        summary_data = [['妫€娴嬮」', '鏁伴噺', '鐘舵€?]]

        def make_status(count, threshold=0):
            return '鈿狅笍 鍙戠幇濞佽儊' if count > threshold else '鉁?姝ｅ父'

        summary_data.append(['馃敆 榛戦摼妫€娴?, summary['blacklink_count'], make_status(summary['blacklink_count'])])
        summary_data.append(['馃毆 鍚庨棬妫€娴?, summary['backdoor_count'], make_status(summary['backdoor_count'])])
        summary_data.append(['鈿狅笍 杩濊妫€娴?, summary['violativelink_count'], make_status(summary['violativelink_count'])])
        summary_data.append(['馃挃 姝婚摼妫€娴?, summary['diedlink_count'], '鈥?])

        summary_table = Table(summary_data, colWidths=[4*cm, 3*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#fff0f0') if summary['blacklink_count'] > 0 else colors.HexColor('#f0fff0')),
            ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#fff0f0') if summary['backdoor_count'] > 0 else colors.HexColor('#f0fff0')),
            ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#fff8e0') if summary['violativelink_count'] > 0 else colors.HexColor('#f0fff0')),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.5*cm))

        # Detail sections
        def add_section(title, items, color):
            if not items:
                return
            story.append(Paragraph(title, styles['Heading2']))
            rows = [['闂鍦板潃', '璇︽儏']]
            for item in items[:20]:  # Cap at 20
                detail = item.get('blacklinkres') or item.get('backdoorres') or item.get('violativelinkres') or [str(item.get('status_code',''))]
                rows.append([item['url'][:60], ', '.join(detail)[:80]])
            t = Table(rows, colWidths=[6*cm, 9*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(color)),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#dddddd')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 4),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9f9f9')]),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))

        add_section('馃敆 榛戦摼璇︽儏', summary['blacklink_list'], '#d32f2f')
        add_section('馃毆 鍚庨棬璇︽儏', summary['backdoor_list'], '#c62828')
        add_section('鈿狅笍 杩濊璇︽儏', summary['violativelink_list'], '#f57c00')
        add_section('馃挃 姝婚摼璇︽儏', summary['diedlink_list'], '#616161')

        doc.build(story)
        buffer.seek(0)
        filename = f'orion_report_{task_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.pdf'
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    return jsonify({'status': 'error', 'message': 'Unsupported format. Use: json, csv, pdf'}), 400


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?# Stats
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
@app.route('/api/stats', methods=['GET'])
def get_stats():
    total = len(TASKS)
    success = sum(1 for t in TASKS.values() if t['status'] == 'success')
    error = sum(1 for t in TASKS.values() if t['status'] == 'error')
    running = sum(1 for t in TASKS.values() if t['status'] in ('pending', 'running'))
    return jsonify({'total': total, 'success': success, 'error': error, 'running': running})


@app.route('/api/ai-analyze', methods=['POST'])
def ai_analyze():
    """AI analysis of scan results using local Ollama"""
    try:
        import urllib.request
        data = request.json or {}
        result = data.get('result', {})
        bl = len(result.get('blacklink_list', []))
        bd = len(result.get('backdoor_list', []))
        vl = len(result.get('violativelink_list', []))
        dl = len(result.get('diedlink_list', []))
        url = result.get('taskurl', 'unknown')
        total = bl + bd + vl

        # Simple rule-based analysis (always works)
        if total == 0:
            risk = '浣庡嵄'
            analysis = f'瀵?{url} 鐨勬壂鎻忔湭鍙戠幇榛戦摼銆佸悗闂ㄦ垨杩濊鍐呭锛岀綉绔欑洰鍓嶅畨鍏ㄧ姸鍐佃壇濂姐€傚缓璁畾鏈熷鏌ャ€?
            suggestions = ['缁х画淇濇寔褰撳墠瀹夊叏绛栫暐', '寤鸿姣忓懆杩涜涓€娆¤嚜鍔ㄥ寲鎵弿']
        elif total >= 5 or bd > 0:
            risk = '楂樺嵄'
            analysis = f'瀵?{url} 鐨勬壂鎻忓彂鐜拌緝楂橀闄╋紝鍏?{total} 涓闄╅」锛堥粦閾?{bl}銆佸悗闂?{bd}銆佽繚瑙?{vl}锛夛紝寤鸿绔嬪嵆澶勭悊銆?
            suggestions = ['鍚庨棬鏂囦欢绔嬪嵆娓呴櫎骞舵帓鏌ユ湇鍔″櫒鍏ヤ镜鐥曡抗', '榛戦摼鍐呭娓呴櫎鍚庢帓鏌ヨ榛戦€斿緞', '寤鸿鏇存敼鏈嶅姟鍣ㄥ瘑鐮佸苟妫€鏌SH閰嶇疆']
            if bd > 0:
                suggestions.insert(0, '銆愮揣鎬ャ€戝彂鐜板悗闂紒寤鸿绔嬪嵆鏂綉鎺掓煡')
        else:
            risk = '涓嵄'
            analysis = f'瀵?{url} 鐨勬壂鎻忓彂鐜?{total} 涓闄╅」锛屽缓璁牳瀹炲苟澶勭悊銆?
            suggestions = ['鏍稿疄榛戦摼鍐呭鏄惁灞炰簬姝ｅ父澶栭摼', '妫€鏌ユ槸鍚﹀瓨鍦ㄩ殣钘忕殑鍚庨棬鏂囦欢', '寤鸿鍔犲己鍐呭瀹℃牳鏈哄埗']

        # Try Ollama if available
        ollama_url = 'http://localhost:11434/api/generate'
        prompt = f'''浣犳槸涓€鍚嶇綉缁滃畨鍏ㄤ笓瀹躲€傝鍒嗘瀽浠ヤ笅缃戠珯瀹夊叏鎵弿缁撴灉锛屽垽鏂槸鍚﹀瓨鍦ㄧ湡瀹炵殑濞佽儊锛屽苟缁欏嚭绠€娲佺殑澶勭疆寤鸿銆?
鎵弿缁撴灉锛?- 鐩爣绔欑偣锛歿url}
- 榛戦摼鏁伴噺锛歿bl}
- 鍚庨棬鏁伴噺锛歿bd}
- 杩濊鍐呭鏁伴噺锛歿vl}
- 姝婚摼鏁伴噺锛歿dl}

璇蜂互JSON鏍煎紡鍥炲锛堝彧杩斿洖JSON锛夛細
{{"risk_level": "楂樺嵄/涓嵄/浣庡嵄", "analysis": "鍒嗘瀽璇存槑锛?0瀛椾互鍐咃級", "suggestions": ["寤鸿1", "寤鸿2"]}}'''

        try:
            req = urllib.request.Request(
                ollama_url,
                data=json.dumps({'model': 'qwen3.5:4b', 'prompt': prompt, 'stream': False}).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                ollama_data = json.loads(resp.read())
                text = ollama_data.get('response', '').strip()
                import re
                m = re.search(r'\{[\s\S]+\}', text)
                if m:
                    ai_result = json.loads(m.group())
                    return jsonify({'source': 'ollama', 'ollama_ai': True, **ai_result})
        except Exception as ollama_err:
            pass

        return jsonify({
            'source': 'rule_based',
            'ollama_ai': False,
            'risk_level': risk,
            'analysis': analysis,
            'suggestions': suggestions,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rules', methods=['GET'])
def get_rules():
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, 'ORM'))
        sys.path.insert(0, BASE_DIR)
        from db_rules import get_blacklink_rules, get_backdoor_rules, get_violativelink_rules, get_backdoor_paths, rulesnum
        num = rulesnum()
        return jsonify({
            'blacklink_rules': get_blacklink_rules(),
            'backdoor_rules': get_backdoor_rules(),
            'violativelink_rules': get_violativelink_rules(),
            'backdoor_paths': get_backdoor_paths(),
            'rules_count': num
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'Orion API',
        'version': '2.0',
        'scheduler_available': SCHEDULER_AVAILABLE,
        'reportlab_available': REPORTLAB_AVAILABLE,
    })


# 鈹€鈹€ Init scheduler 鈹€鈹€
if SCHEDULER_AVAILABLE:
    _setup_scheduler()
    print('[*] Scheduler started')

if __name__ == '__main__':
    print('[*] Orion API Server v2.0 starting on http://0.0.0.0:5188')
    app.run(host='0.0.0.0', port=5188, debug=False, threaded=True)
