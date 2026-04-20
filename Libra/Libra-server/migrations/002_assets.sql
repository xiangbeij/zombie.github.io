-- ═══════════════════════════════════════════════
-- 资产发现模块 - 数据库迁移脚本 v2
-- 运行方式: sqlite3 /opt/Libra/Libra.db < migrations/002_assets.sql
-- ═══════════════════════════════════════════════

-- IP 地址段管理
CREATE TABLE IF NOT EXISTS ip_ranges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cidr        TEXT    NOT NULL UNIQUE,    -- '210.44.49.0/24'
    description TEXT    DEFAULT '',
    tags        TEXT    DEFAULT '',         -- '校内,核心资产'
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 证书导入记录
CREATE TABLE IF NOT EXISTS cert_assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_sha1       TEXT    NOT NULL UNIQUE, -- 证书 SHA1 指纹
    cert_subject    TEXT    DEFAULT '',       -- 证书主体 CN
    cert_issuer     TEXT    DEFAULT '',
    cert_not_before TEXT    DEFAULT '',
    cert_not_after  TEXT    DEFAULT '',
    san_count       INTEGER DEFAULT 0,        -- 证书绑定的域名数量
    domains         TEXT    DEFAULT '[]',     -- JSON数组: 所有SAN域名
    raw_cert        TEXT    DEFAULT '',       -- PEM 编码的证书
    imported_at     TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 资产主表（统一管理域名/IP/证书关联的资产）
CREATE TABLE IF NOT EXISTS assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type      TEXT    NOT NULL,         -- 'domain' | 'ip' | 'cert'
    value           TEXT    NOT NULL,         -- 域名 / IP地址 / 证书SHA1
    port            INTEGER DEFAULT 0,         -- 0 表示通用 / 80 / 443
    scheme          TEXT    DEFAULT 'https',   -- http / https
    title           TEXT    DEFAULT '',        -- 网站标题
    server_fingerprint TEXT DEFAULT '',        -- Web服务器指纹 (nginx/apache等)
    status_code     INTEGER DEFAULT 0,         -- HTTP 状态码
    content_hash    TEXT    DEFAULT '',        -- 页面内容hash (篡改检测用)
    cert_id         INTEGER,                  -- 关联 cert_assets.id
    ip_range_id     INTEGER,                   -- 关联 ip_ranges.id (如果是IP段扫描发现的)
    tags            TEXT    DEFAULT '',       -- 标签: '校内','云服务','核心'
    status          TEXT    DEFAULT 'active', -- 'active' | 'inactive' | 'unknown'
    first_seen      TEXT    DEFAULT (datetime('now', 'localtime')),
    last_seen       TEXT    DEFAULT (datetime('now', 'localtime')),
    note            TEXT    DEFAULT '',       -- 备注
    UNIQUE(value, port, scheme)
);

-- 资产快照（用于篡改检测）
CREATE TABLE IF NOT EXISTS asset_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id        INTEGER NOT NULL,
    url             TEXT    NOT NULL,
    title           TEXT    DEFAULT '',
    keywords        TEXT    DEFAULT '',        -- 页面关键词 (meta keywords)
    description     TEXT    DEFAULT '',        -- meta description
    content_hash    TEXT    NOT NULL,          -- 页面内容hash
    screenshot_path TEXT    DEFAULT '',        -- 截图文件路径
    diff_ratio      REAL    DEFAULT 0,         -- 与上次快照的差异率 0.0~1.0
    scanned_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 篡改告警记录
CREATE TABLE IF NOT EXISTS tamper_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id        INTEGER NOT NULL,
    snapshot_id     INTEGER NOT NULL,          -- 发现篡改时的快照ID
    alert_type      TEXT    NOT NULL,          -- 'content_changed' | 'title_changed' | 'new_blacklink' | '暗链'
    alert_detail    TEXT    DEFAULT '',         -- 告警详情 JSON
    confirmed       INTEGER DEFAULT 0,         -- 0=未确认 1=已确认误报 2=已确认真实篡改
    confirmed_at    TEXT    DEFAULT '',
    confirmed_by    TEXT    DEFAULT '',
    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES asset_snapshots(id) ON DELETE SET NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets(tags);
CREATE INDEX IF NOT EXISTS idx_snapshots_asset ON asset_snapshots(asset_id);
CREATE INDEX IF NOT EXISTS idx_alerts_asset ON tamper_alerts(asset_id);
CREATE INDEX IF NOT EXISTS idx_cert_assets_sha1 ON cert_assets(cert_sha1);
