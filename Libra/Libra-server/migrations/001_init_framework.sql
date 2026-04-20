-- Libra 框架扩展 - 数据库迁移脚本 v1
-- 运行方式: sqlite3 /opt/Libra/Libra.db < migrations/001_init_framework.sql

-- ═══════════════════════════════════════════════
-- 站点资产管理
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,          -- 站点名称，如"教务处"
    url         TEXT    NOT NULL UNIQUE,  -- 站点URL
    org         TEXT    DEFAULT '',        -- 所属部门
    owner       TEXT    DEFAULT '',        -- 负责人
    contact     TEXT    DEFAULT '',        -- 联系方式
    scan_type   TEXT    DEFAULT 'HomePage_Scan',  -- 默认扫描类型
    schedule    TEXT    DEFAULT '',        -- 定时任务 cron 表达式
    enabled     INTEGER DEFAULT 1,         -- 是否启用监控
    ssl_expiry_warn INTEGER DEFAULT 30,   -- SSL证书到期提前N天告警
    created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- ═══════════════════════════════════════════════
-- SSL证书记录
-- ═══════════════════════════════════════════════
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
);

-- ═══════════════════════════════════════════════
-- 用户账户
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,          -- bcrypt hash
    nickname    TEXT    DEFAULT '',
    role        TEXT    DEFAULT 'viewer',   -- admin / operator / viewer
    email       TEXT    DEFAULT '',
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
    last_login  TEXT    DEFAULT ''
);

-- ═══════════════════════════════════════════════
-- 通知渠道配置
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS notification_channels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_type TEXT   NOT NULL,          -- email / feishu / dingtalk / webhook
    name        TEXT    NOT NULL,          -- 渠道名称，如"安全运维群"
    config      TEXT    DEFAULT '{}',       -- JSON配置（webhook URL, token等）
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- ═══════════════════════════════════════════════
-- 通知规则
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS notification_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,      -- 规则名称
    channel_id      INTEGER NOT NULL,      -- 关联渠道
    event_type      TEXT    NOT NULL,      -- scan_complete / high_risk / ssl_expiring / scheduled
    risk_min        TEXT    DEFAULT 'low', -- minimal risk level to trigger: low/medium/high/critical
    enabled         INTEGER DEFAULT 1,
    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE CASCADE
);

-- ═══════════════════════════════════════════════
-- 通知日志
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS notification_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  INTEGER,
    event_type  TEXT    NOT NULL,
    title       TEXT    DEFAULT '',
    content     TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'pending', -- pending / sent / failed
    response    TEXT    DEFAULT '',        -- 第三方返回信息
    sent_at     TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE SET NULL
);

-- ═══════════════════════════════════════════════
-- 扫描报告（扩展，用于报表增强）
-- ═══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT    NOT NULL,
    site_url    TEXT    NOT NULL,
    scan_type   TEXT    NOT NULL,
    risk_level  TEXT    DEFAULT 'unknown', -- unknown / low / medium / high / critical
    summary     TEXT    DEFAULT '',        -- AI摘要
    blacklist_count  INTEGER DEFAULT 0,
    backdoor_count  INTEGER DEFAULT 0,
    violative_count INTEGER DEFAULT 0,
    diedlink_count  INTEGER DEFAULT 0,
    pdf_path    TEXT    DEFAULT '',
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- ═══════════════════════════════════════════════
-- 默认管理员账户 (admin / Qau2026@%1)
-- 密码需由应用启动时或首次访问时初始化
-- ═══════════════════════════════════════════════
INSERT OR IGNORE INTO users (username, password, nickname, role) VALUES
    ('admin', '$2b$10$placeholder.hash.for.initial.setup', '管理员', 'admin');

-- ═══════════════════════════════════════════════
-- 初始化示例站点（如果表为空）
-- ═══════════════════════════════════════════════
-- INSERT INTO sites (name, url, org) SELECT '示例站点', 'https://example.com', '测试部门' WHERE NOT EXISTS (SELECT 1 FROM sites);
