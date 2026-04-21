-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 璧勪骇鍙戠幇妯″潡 - 鏁版嵁搴撹縼绉昏剼鏈?v2
-- 杩愯鏂瑰紡: sqlite3 /opt/Orion/orion.db < migrations/002_assets.sql
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
-- IP 鍦板潃娈电鐞?CREATE TABLE IF NOT EXISTS ip_ranges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cidr        TEXT    NOT NULL UNIQUE,    -- '210.44.49.0/24'
    description TEXT    DEFAULT '',
    tags        TEXT    DEFAULT '',         -- '鏍″唴,鏍稿績璧勪骇'
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 璇佷功瀵煎叆璁板綍
CREATE TABLE IF NOT EXISTS cert_assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_sha1       TEXT    NOT NULL UNIQUE, -- 璇佷功 SHA1 鎸囩汗
    cert_subject    TEXT    DEFAULT '',       -- 璇佷功涓讳綋 CN
    cert_issuer     TEXT    DEFAULT '',
    cert_not_before TEXT    DEFAULT '',
    cert_not_after  TEXT    DEFAULT '',
    san_count       INTEGER DEFAULT 0,        -- 璇佷功缁戝畾鐨勫煙鍚嶆暟閲?    domains         TEXT    DEFAULT '[]',     -- JSON鏁扮粍: 鎵€鏈塖AN鍩熷悕
    raw_cert        TEXT    DEFAULT '',       -- PEM 缂栫爜鐨勮瘉涔?    imported_at     TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 璧勪骇涓昏〃锛堢粺涓€绠＄悊鍩熷悕/IP/璇佷功鍏宠仈鐨勮祫浜э級
CREATE TABLE IF NOT EXISTS assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type      TEXT    NOT NULL,         -- 'domain' | 'ip' | 'cert'
    value           TEXT    NOT NULL,         -- 鍩熷悕 / IP鍦板潃 / 璇佷功SHA1
    port            INTEGER DEFAULT 0,         -- 0 琛ㄧず閫氱敤 / 80 / 443
    scheme          TEXT    DEFAULT 'https',   -- http / https
    title           TEXT    DEFAULT '',        -- 缃戠珯鏍囬
    server_fingerprint TEXT DEFAULT '',        -- Web鏈嶅姟鍣ㄦ寚绾?(nginx/apache绛?
    status_code     INTEGER DEFAULT 0,         -- HTTP 鐘舵€佺爜
    content_hash    TEXT    DEFAULT '',        -- 椤甸潰鍐呭hash (绡℃敼妫€娴嬬敤)
    cert_id         INTEGER,                  -- 鍏宠仈 cert_assets.id
    ip_range_id     INTEGER,                   -- 鍏宠仈 ip_ranges.id (濡傛灉鏄疘P娈垫壂鎻忓彂鐜扮殑)
    tags            TEXT    DEFAULT '',       -- 鏍囩: '鏍″唴','浜戞湇鍔?,'鏍稿績'
    status          TEXT    DEFAULT 'active', -- 'active' | 'inactive' | 'unknown'
    first_seen      TEXT    DEFAULT (datetime('now', 'localtime')),
    last_seen       TEXT    DEFAULT (datetime('now', 'localtime')),
    note            TEXT    DEFAULT '',       -- 澶囨敞
    UNIQUE(value, port, scheme)
);

-- 璧勪骇蹇収锛堢敤浜庣鏀规娴嬶級
CREATE TABLE IF NOT EXISTS asset_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id        INTEGER NOT NULL,
    url             TEXT    NOT NULL,
    title           TEXT    DEFAULT '',
    keywords        TEXT    DEFAULT '',        -- 椤甸潰鍏抽敭璇?(meta keywords)
    description     TEXT    DEFAULT '',        -- meta description
    content_hash    TEXT    NOT NULL,          -- 椤甸潰鍐呭hash
    screenshot_path TEXT    DEFAULT '',        -- 鎴浘鏂囦欢璺緞
    diff_ratio      REAL    DEFAULT 0,         -- 涓庝笂娆″揩鐓х殑宸紓鐜?0.0~1.0
    scanned_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 绡℃敼鍛婅璁板綍
CREATE TABLE IF NOT EXISTS tamper_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id        INTEGER NOT NULL,
    snapshot_id     INTEGER NOT NULL,          -- 鍙戠幇绡℃敼鏃剁殑蹇収ID
    alert_type      TEXT    NOT NULL,          -- 'content_changed' | 'title_changed' | 'new_blacklink' | '鏆楅摼'
    alert_detail    TEXT    DEFAULT '',         -- 鍛婅璇︽儏 JSON
    confirmed       INTEGER DEFAULT 0,         -- 0=鏈‘璁?1=宸茬‘璁よ鎶?2=宸茬‘璁ょ湡瀹炵鏀?    confirmed_at    TEXT    DEFAULT '',
    confirmed_by    TEXT    DEFAULT '',
    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES asset_snapshots(id) ON DELETE SET NULL
);

-- 鍒涘缓绱㈠紩
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets(tags);
CREATE INDEX IF NOT EXISTS idx_snapshots_asset ON asset_snapshots(asset_id);
CREATE INDEX IF NOT EXISTS idx_alerts_asset ON tamper_alerts(asset_id);
CREATE INDEX IF NOT EXISTS idx_cert_assets_sha1 ON cert_assets(cert_sha1);
