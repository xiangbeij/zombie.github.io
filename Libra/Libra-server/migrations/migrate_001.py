#!/usr/bin/env python3
"""Libra 框架扩展 - 数据库迁移脚本 v1"""
import sqlite3
import os

DB_PATH = '/opt/Libra/Libra.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ═══ 站点资产管理 ═══ #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sites (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        url         TEXT    NOT NULL UNIQUE,
        org         TEXT    DEFAULT '',
        owner       TEXT    DEFAULT '',
        contact     TEXT    DEFAULT '',
        scan_type   TEXT    DEFAULT 'HomePage_Scan',
        schedule    TEXT    DEFAULT '',
        enabled     INTEGER DEFAULT 1,
        ssl_expiry_warn INTEGER DEFAULT 30,
        created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
        updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
    )""")
    print("✓ sites table")

    # ═══ SSL证书记录 ═══ #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ssl_certs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        site_id     INTEGER NOT NULL,
        domain      TEXT    NOT NULL,
        issuer      TEXT    DEFAULT '',
        valid_from  TEXT    DEFAULT '',
        valid_until TEXT    DEFAULT '',
        days_left   INTEGER DEFAULT 0,
        checked_at  TEXT    DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
    )""")
    print("✓ ssl_certs table")

    # ═══ 用户账户 ═══ #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT    NOT NULL UNIQUE,
        password    TEXT    NOT NULL,
        nickname    TEXT    DEFAULT '',
        role        TEXT    DEFAULT 'viewer',
        email       TEXT    DEFAULT '',
        enabled     INTEGER DEFAULT 1,
        created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
        last_login  TEXT    DEFAULT ''
    )""")
    print("✓ users table")

    # ═══ 通知渠道配置 ═══ #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_channels (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_type TEXT   NOT NULL,
        name        TEXT    NOT NULL,
        config      TEXT    DEFAULT '{}',
        enabled     INTEGER DEFAULT 1,
        created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
    )""")
    print("✓ notification_channels table")

    # ═══ 通知规则 ═══ #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_rules (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL,
        channel_id      INTEGER NOT NULL,
        event_type      TEXT    NOT NULL,
        risk_min        TEXT    DEFAULT 'low',
        enabled         INTEGER DEFAULT 1,
        created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE CASCADE
    )""")
    print("✓ notification_rules table")

    # ═══ 通知日志 ═══ #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id  INTEGER,
        event_type  TEXT    NOT NULL,
        title       TEXT    DEFAULT '',
        content     TEXT    DEFAULT '',
        status      TEXT    DEFAULT 'pending',
        response    TEXT    DEFAULT '',
        sent_at     TEXT    DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE SET NULL
    )""")
    print("✓ notification_logs table")

    # ═══ 扫描报告扩展 ═══ #
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id     TEXT    NOT NULL,
        site_url    TEXT    NOT NULL,
        scan_type   TEXT    NOT NULL,
        risk_level  TEXT    DEFAULT 'unknown',
        summary     TEXT    DEFAULT '',
        blacklist_count  INTEGER DEFAULT 0,
        backdoor_count  INTEGER DEFAULT 0,
        violative_count INTEGER DEFAULT 0,
        diedlink_count  INTEGER DEFAULT 0,
        pdf_path    TEXT    DEFAULT '',
        created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
    )""")
    print("✓ reports table")

    # ═══ 默认管理员账户 ═══ #
    # 密码: Qau2026@%1 (bcrypt，需要用应用设置)
    import hashlib
    default_pw_hash = hashlib.sha256(b'Qau2026@%1').hexdigest()
    cur.execute("INSERT OR IGNORE INTO users (username, password, nickname, role) VALUES (?, ?, ?, ?)",
                ('admin', default_pw_hash, '管理员', 'admin'))
    print("✓ default admin user")

    conn.commit()

    # 验证
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n所有表: {tables}")

    cur.execute("SELECT id, username, role FROM users")
    print(f"用户: {cur.fetchall()}")

    conn.close()
    print("\n迁移完成！")

if __name__ == '__main__':
    migrate()
