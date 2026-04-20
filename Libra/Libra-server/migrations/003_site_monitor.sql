-- ═══════════════════════════════════════════════
-- 网站状态监控模块 - 数据库迁移脚本 v3
-- 运行方式: sqlite3 /opt/Libra/Libra.db < migrations/003_site_monitor.sql
-- ═══════════════════════════════════════════════

-- 网站监控目标表
CREATE TABLE IF NOT EXISTS site_monitors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,           -- 监控名称，如"学校主页"
    url             TEXT    NOT NULL,           -- 监控 URL
    host            TEXT    DEFAULT '',          -- 提取的 host
    check_interval  INTEGER DEFAULT 60,         -- 检测间隔（秒），默认60秒
    enabled         INTEGER DEFAULT 1,          -- 1=启用 0=暂停
    timeout_seconds INTEGER DEFAULT 10,         -- 超时秒数
    last_status     TEXT    DEFAULT 'unknown',  -- unknown | online | offline | error
    last_status_code INTEGER DEFAULT 0,         -- HTTP 状态码
    last_rtt_ms     INTEGER DEFAULT 0,          -- 上次响应时间（毫秒）
    last_checked_at TEXT    DEFAULT '',         -- 上次检测时间
    last_error      TEXT    DEFAULT '',          -- 上次错误信息
    ssl_expiry_date TEXT    DEFAULT '',          -- SSL 证书到期日期
    ssl_days_left   INTEGER DEFAULT -1,         -- SSL 剩余天数，-1=未检测
    ssl_valid       INTEGER DEFAULT -1,         -- 1=有效 0=无效 -1=非HTTPS或未检测
    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 监控历史记录
CREATE TABLE IF NOT EXISTS site_monitor_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id      INTEGER NOT NULL,
    status          TEXT    NOT NULL,           -- online | offline | error
    status_code     INTEGER DEFAULT 0,
    rtt_ms          INTEGER DEFAULT 0,          -- 响应时间 ms
    error_msg       TEXT    DEFAULT '',
    ssl_days_left   INTEGER DEFAULT -1,
    checked_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (monitor_id) REFERENCES site_monitors(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_monitors_enabled ON site_monitors(enabled);
CREATE INDEX IF NOT EXISTS idx_monitors_last_status ON site_monitors(last_status);
CREATE INDEX IF NOT EXISTS idx_monitor_history_monitor ON site_monitor_history(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_history_time ON site_monitor_history(checked_at DESC);
