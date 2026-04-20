#!/usr/bin/env python3
"""通知 Handler - 多渠道告警（邮件/飞书/钉钉/自定义Webhook）"""
import sys
import sqlite3
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
from datetime import datetime

DB_PATH = '/opt/Libra/Libra.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def send_email(to_email, subject, content, config):
    """发送邮件"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = config.get('from', '')
        msg['To'] = to_email

        html_part = MIMEText(content, 'html', 'utf-8')
        msg.attach(html_part)

        server = smtplib.SMTP_SSL(config.get('host', 'smtp.gmail.com'),
                                  int(config.get('port', 465)))
        server.login(config.get('user', ''), config.get('pass', ''))
        server.sendmail(msg['From'], [to_email], msg.as_string())
        server.quit()
        return {'ok': True, 'msg': 'Email sent'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def send_feishu_webhook(webhook_url, content, config):
    """发送飞书群消息"""
    try:
        headers = {'Content-Type': 'application/json'}
        # 飞书富文本消息格式
        payload = {
            'msg_type': 'text',
            'content': {'text': content}
        }
        # 支持加签模式
        if config.get('secret'):
            import time, hmac, base64, hashlib
            timestamp = str(int(time.time()))
            sign_str = timestamp + '\n' + config['secret']
            sign = base64.b64encode(hmac.new(sign_str.encode(), digestmod=hashlib.sha256).digest()).decode()
            payload = {
                'msg_type': 'text',
                'content': {'text': content + f"\n\n-- Libra 安全扫描'"}
            }
            # 加签需要换签证 API，这里简化为直接 webhook
        data = json.dumps(payload).encode()
        req = urllib.request.Request(webhook_url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get('code') == 0 or result.get('StatusCode') == 0:
                return {'ok': True, 'msg': 'Feishu sent'}
            return {'ok': False, 'error': result}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def send_webhook(webhook_url, content, config):
    """发送通用 Webhook"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            'text': content,
            'timestamp': datetime.now().isoformat(),
        }
        # 支持 secret 签名
        if config.get('secret'):
            import hmac, hashlib, base64, time
            timestamp = str(int(time.time()))
            string_to_sign = timestamp + '\n' + config['secret']
            sign = base64.b64encode(
                hmac.new(config['secret'].encode(), string_to_sign.encode(),
                         digestmod=hashlib.sha256).digest()
            ).decode()
            payload['sign'] = sign
            payload['timestamp'] = timestamp

        data = json.dumps(payload).encode()
        req = urllib.request.Request(webhook_url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {'ok': True, 'response': resp.read().decode()[:200]}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def send_notification(channel_id, event_type, title, content, extra_data=None):
    """根据渠道配置发送通知"""
    conn = get_db()
    cur = conn.cursor()

    # 获取渠道配置
    cur.execute("SELECT * FROM notification_channels WHERE id=? AND enabled=1", (channel_id,))
    channel = cur.fetchone()
    if not channel:
        conn.close()
        return {'ok': False, 'error': 'Channel not found or disabled'}

    ch_type = channel['channel_type']
    config = json.loads(channel['config'] or '{}')
    status = 'failed'
    response_text = ''

    if ch_type == 'email':
        result = send_email(config.get('to', ''), title, content, config)
        status = 'sent' if result.get('ok') else 'failed'
        response_text = json.dumps(result, ensure_ascii=False)

    elif ch_type == 'feishu':
        result = send_feishu_webhook(config.get('webhook_url', ''), f"{title}\n\n{content}", config)
        status = 'sent' if result.get('ok') else 'failed'
        response_text = json.dumps(result, ensure_ascii=False)

    elif ch_type == 'webhook':
        result = send_webhook(config.get('webhook_url', ''), f"{title}\n\n{content}", config)
        status = 'sent' if result.get('ok') else 'failed'
        response_text = json.dumps(result, ensure_ascii=False)

    elif ch_type == 'dingtalk':
        result = send_webhook(config.get('webhook_url', ''),
                              f"**{title}**\n\n{content}", config)
        status = 'sent' if result.get('ok') else 'failed'
        response_text = json.dumps(result, ensure_ascii=False)

    # 记录日志
    cur.execute("""
        INSERT INTO notification_logs (channel_id, event_type, title, content, status, response)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (channel_id, event_type, title, content, status, response_text[:500]))
    conn.commit()
    log_id = cur.lastrowid
    conn.close()

    return {'ok': status == 'sent', 'status': status, 'log_id': log_id}

def list_channels():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notification_channels ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def create_channel(data):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notification_channels (channel_type, name, config, enabled)
        VALUES (?, ?, ?, ?)
    """, (data['channel_type'], data['name'],
          json.dumps(data.get('config', {}), ensure_ascii=False),
          data.get('enabled', 1)))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return dict({'id': new_id}, **data)

def update_channel(channel_id, data):
    conn = get_db()
    cur = conn.cursor()
    if 'config' in data:
        data['config'] = json.dumps(data['config'], ensure_ascii=False)
    fields = ['channel_type','name','config','enabled']
    vals = [data.get(f, '') for f in fields]
    vals.append(channel_id)
    cur.execute(f"UPDATE notification_channels SET {','.join(f+'=?' for f in fields)} WHERE id=?", vals)
    conn.commit()
    conn.close()
    return {'ok': True}

def delete_channel(channel_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM notification_channels WHERE id=?", (channel_id,))
    conn.commit()
    conn.close()
    return {'ok': True}

def list_logs(limit=50):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT l.*, c.name as channel_name, c.channel_type
        FROM notification_logs l
        LEFT JOIN notification_channels c ON l.channel_id = c.id
        ORDER BY l.sent_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No action specified'}))
        return

    action = sys.argv[1]

    if action == 'channels':
        print(json.dumps(list_channels(), ensure_ascii=False))

    elif action == 'create-channel':
        payload = json.loads(sys.stdin.read())
        print(json.dumps(create_channel(payload), ensure_ascii=False))

    elif action == 'update-channel' and len(sys.argv) >= 3:
        payload = json.loads(sys.stdin.read())
        print(json.dumps(update_channel(int(sys.argv[2]), payload), ensure_ascii=False))

    elif action == 'delete-channel' and len(sys.argv) >= 3:
        print(json.dumps(delete_channel(int(sys.argv[2])), ensure_ascii=False))

    elif action == 'logs':
        print(json.dumps(list_logs(50), ensure_ascii=False))

    elif action == 'send' and len(sys.argv) >= 5:
        # python handler.py send <channel_id> <event_type> <title>
        channel_id = int(sys.argv[2])
        event_type = sys.argv[3]
        title = sys.argv[4]
        # content from stdin
        content = sys.stdin.read() if not sys.stdin.isatty() else ''
        result = send_notification(channel_id, event_type, title, content)
        print(json.dumps(result, ensure_ascii=False))

    else:
        print(json.dumps({'error': f'Unknown action: {action}'}))

if __name__ == '__main__':
    main()
