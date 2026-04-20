#!/usr/bin/env python3
"""用户管理 Handler - 用户 CRUD + 登录认证"""
import sys
import sqlite3
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta

DB_PATH = '/opt/Libra/Libra.db'
TOKEN_TTL_HOURS = 72  # token 有效期

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """简单 SHA256 hash（生产环境建议换 bcrypt）"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """验证密码"""
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def make_token(user_id, username, role):
    """生成简单 token（生产环境建议用 JWT）"""
    raw = f"{user_id}:{username}:{role}:{time.time()}:{secrets.token_hex(16)}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    return token

def list_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, nickname, role, email, enabled, created_at, last_login FROM users ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, nickname, role, email, enabled, created_at, last_login FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(data):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, password, nickname, role, email)
            VALUES (?, ?, ?, ?, ?)
        """, (data['username'], hash_password(data['password']), data.get('nickname',''),
              data.get('role','viewer'), data.get('email','')))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return get_user(new_id)
    except sqlite3.IntegrityError:
        conn.close()
        return {'error': '用户名已存在'}

def update_user(user_id, data):
    conn = get_db()
    cur = conn.cursor()
    if 'password' in data:
        data['password'] = hash_password(data['password'])
    fields = []
    vals = []
    for k in ['username','password','nickname','role','email','enabled']:
        if k in data:
            fields.append(f"{k}=?")
            vals.append(data[k])
    if fields:
        vals.append(user_id)
        cur.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return get_user(user_id)

def delete_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=? AND username != 'admin'", (user_id,))  # 保护管理员
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

def login(username, password):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND enabled=1", (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {'error': '用户不存在或已禁用'}

    user = dict(row)
    if not verify_password(password, user['password']):
        return {'error': '密码错误'}

    # 生成 token
    token = make_token(user['id'], user['username'], user['role'])

    # 更新最后登录时间
    conn2 = get_db()
    cur2 = conn2.cursor()
    cur2.execute("UPDATE users SET last_login=datetime('now','localtime') WHERE id=?", (user['id'],))
    conn2.commit()
    conn2.close()

    return {
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'],
            'role': user['role'],
            'email': user.get('email','')
        }
    }

def verify_token(token):
    """Token 验证占位（生产环境用 JWT）"""
    # 简化：token 就是 hash，存 Active_tokens 表
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.nickname, u.role
        FROM active_tokens t
        JOIN users u ON t.user_id = u.id
        WHERE t.token=? AND t.expires_at > datetime('now','localtime')
    """, (token,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No action specified'}))
        return

    action = sys.argv[1]

    if action == 'list':
        print(json.dumps(list_users(), ensure_ascii=False))

    elif action == 'get' and len(sys.argv) >= 3:
        print(json.dumps(get_user(int(sys.argv[2])), ensure_ascii=False))

    elif action == 'create':
        payload = json.loads(sys.stdin.read())
        result = create_user(payload)
        if 'error' in result:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False))

    elif action == 'update' and len(sys.argv) >= 3:
        payload = json.loads(sys.stdin.read())
        print(json.dumps(update_user(int(sys.argv[2]), payload), ensure_ascii=False))

    elif action == 'delete' and len(sys.argv) >= 3:
        deleted = delete_user(int(sys.argv[2]))
        print(json.dumps({'ok': deleted}))

    elif action == 'login':
        payload = json.loads(sys.stdin.read())
        result = login(payload.get('username',''), payload.get('password',''))
        print(json.dumps(result, ensure_ascii=False))

    else:
        print(json.dumps({'error': f'Unknown action: {action}'}))

if __name__ == '__main__':
    main()
