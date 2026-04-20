#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import os
import sys
import uuid
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 任务存储（生产环境建议换 Redis）
TASKS = {}
TASK_RESULTS = {}

LIBRA_PATH = os.path.join(os.path.dirname(__file__), '..', 'Libra.py')
LIBRA_DIR = os.path.join(os.path.dirname(__file__), '..')


@app.route('/api/scan', methods=['POST'])
def start_scan():
    """发起扫描任务"""
    data = request.json
    url = data.get('url', '').strip()
    scan_type = data.get('scan_type', 'HomePage_Scan')

    if not url:
        return jsonify({'status': 'error', 'message': 'URL is required'}), 400

    if scan_type not in ['HomePage_Scan', 'SecondPage_Scan', 'AllSite_Scan', 'CustomPage_Scan']:
        return jsonify({'status': 'error', 'message': 'Invalid scan_type'}), 400

    task_id = str(uuid.uuid4())[:8]

    TASKS[task_id] = {
        'id': task_id,
        'url': url,
        'scan_type': scan_type,
        'status': 'running',
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    # 后台执行，不阻塞
    def run_scan():
        try:
            result = subprocess.run(
                [sys.executable, LIBRA_PATH, '-u', url, '-t', scan_type],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=LIBRA_DIR,
                encoding='utf-8',
                errors='replace'
            )

            # 尝试从 stdout 解析 JSON
            output = result.stdout
            for line in reversed(output.splitlines()):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        scan_data = json.loads(line)
                        TASK_RESULTS[task_id] = scan_data
                        TASKS[task_id]['status'] = 'success'
                        TASKS[task_id]['progress'] = 100
                        return
                    except:
                        pass

            # 解析失败，存错误信息
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['error'] = result.stderr[:500] if result.stderr else 'Unknown error'
        except subprocess.TimeoutExpired:
            TASKS[task_id]['status'] = 'timeout'
            TASKS[task_id]['error'] = 'Scan timeout (>10min)'
        except Exception as e:
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['error'] = str(e)

    import threading
    t = threading.Thread(target=run_scan, daemon=True)
    t.start()

    return jsonify({
        'status': 'accepted',
        'task_id': task_id,
        'message': f'Scan started: {scan_type} -> {url}'
    })


@app.route('/api/scan/<task_id>', methods=['GET'])
def get_scan_status(task_id):
    """查询扫描状态"""
    task = TASKS.get(task_id)
    if not task:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404

    result = TASK_RESULTS.get(task_id, {})
    return jsonify({
        **task,
        'result': result
    })


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """列出所有任务"""
    tasks_list = []
    for tid, task in reversed(list(TASKS.items())):
        task_item = {**task}
        if tid in TASK_RESULTS:
            task_item['result'] = TASK_RESULTS[tid]
        tasks_list.append(task_item)
    return jsonify({'tasks': tasks_list})


@app.route('/api/scan/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    if task_id in TASKS:
        del TASKS[task_id]
    if task_id in TASK_RESULTS:
        del TASK_RESULTS[task_id]
    return jsonify({'status': 'deleted'})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """统计概览"""
    total = len(TASKS)
    success = sum(1 for t in TASKS.values() if t['status'] == 'success')
    error = sum(1 for t in TASKS.values() if t['status'] == 'error')
    running = sum(1 for t in TASKS.values() if t['status'] == 'running')

    return jsonify({
        'total': total,
        'success': success,
        'error': error,
        'running': running
    })


@app.route('/api/rules', methods=['GET'])
def get_rules():
    """获取检测规则（从数据库读取）"""
    try:
        sys.path.insert(0, os.path.join(LIBRA_DIR, 'ORM'))
        from db_rules import get_blacklink_rules, get_backdoor_rules, \
            get_violativelink_rules, get_backdoor_paths, rulesnum

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
    return jsonify({'status': 'ok', 'service': 'Libra API'})


if __name__ == '__main__':
    print('[*] Libra API Server starting on http://0.0.0.0:5188')
    app.run(host='0.0.0.0', port=5188, debug=False, threaded=True)
