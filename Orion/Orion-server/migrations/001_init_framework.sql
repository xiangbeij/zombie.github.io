-- Orion 妗嗘灦鎵╁睍 - 鏁版嵁搴撹縼绉昏剼鏈?v1
-- 杩愯鏂瑰紡: sqlite3 /opt/Orion/orion.db < migrations/001_init_framework.sql

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 绔欑偣璧勪骇绠＄悊
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?CREATE TABLE IF NOT EXISTS sites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,          -- 绔欑偣鍚嶇О锛屽"鏁欏姟澶?
    url         TEXT    NOT NULL UNIQUE,  -- 绔欑偣URL
    org         TEXT    DEFAULT '',        -- 鎵€灞為儴闂?    owner       TEXT    DEFAULT '',        -- 璐熻矗浜?    contact     TEXT    DEFAULT '',        -- 鑱旂郴鏂瑰紡
    scan_type   TEXT    DEFAULT 'HomePage_Scan',  -- 榛樿鎵弿绫诲瀷
    schedule    TEXT    DEFAULT '',        -- 瀹氭椂浠诲姟 cron 琛ㄨ揪寮?    enabled     INTEGER DEFAULT 1,         -- 鏄惁鍚敤鐩戞帶
    ssl_expiry_warn INTEGER DEFAULT 30,   -- SSL璇佷功鍒版湡鎻愬墠N澶╁憡璀?    created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- SSL璇佷功璁板綍
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?CREATE TABLE IF NOT EXISTS ssl_certs (
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

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 鐢ㄦ埛璐︽埛
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?CREATE TABLE IF NOT EXISTS users (
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

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 閫氱煡娓犻亾閰嶇疆
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?CREATE TABLE IF NOT EXISTS notification_channels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_type TEXT   NOT NULL,          -- email / feishu / dingtalk / webhook
    name        TEXT    NOT NULL,          -- 娓犻亾鍚嶇О锛屽"瀹夊叏杩愮淮缇?
    config      TEXT    DEFAULT '{}',       -- JSON閰嶇疆锛坵ebhook URL, token绛夛級
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 閫氱煡瑙勫垯
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?CREATE TABLE IF NOT EXISTS notification_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,      -- 瑙勫垯鍚嶇О
    channel_id      INTEGER NOT NULL,      -- 鍏宠仈娓犻亾
    event_type      TEXT    NOT NULL,      -- scan_complete / high_risk / ssl_expiring / scheduled
    risk_min        TEXT    DEFAULT 'low', -- minimal risk level to trigger: low/medium/high/critical
    enabled         INTEGER DEFAULT 1,
    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE CASCADE
);

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 閫氱煡鏃ュ織
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?CREATE TABLE IF NOT EXISTS notification_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  INTEGER,
    event_type  TEXT    NOT NULL,
    title       TEXT    DEFAULT '',
    content     TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'pending', -- pending / sent / failed
    response    TEXT    DEFAULT '',        -- 绗笁鏂硅繑鍥炰俊鎭?    sent_at     TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE SET NULL
);

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 鎵弿鎶ュ憡锛堟墿灞曪紝鐢ㄤ簬鎶ヨ〃澧炲己锛?-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT    NOT NULL,
    site_url    TEXT    NOT NULL,
    scan_type   TEXT    NOT NULL,
    risk_level  TEXT    DEFAULT 'unknown', -- unknown / low / medium / high / critical
    summary     TEXT    DEFAULT '',        -- AI鎽樿
    blacklist_count  INTEGER DEFAULT 0,
    backdoor_count  INTEGER DEFAULT 0,
    violative_count INTEGER DEFAULT 0,
    diedlink_count  INTEGER DEFAULT 0,
    pdf_path    TEXT    DEFAULT '',
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 榛樿绠＄悊鍛樿处鎴?(admin / Qau2026@%1)
-- 瀵嗙爜闇€鐢卞簲鐢ㄥ惎鍔ㄦ椂鎴栭娆¤闂椂鍒濆鍖?-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?INSERT OR IGNORE INTO users (username, password, nickname, role) VALUES
    ('admin', '$2b$10$placeholder.hash.for.initial.setup', '绠＄悊鍛?, 'admin');

-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 鍒濆鍖栫ず渚嬬珯鐐癸紙濡傛灉琛ㄤ负绌猴級
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- INSERT INTO sites (name, url, org) SELECT '绀轰緥绔欑偣', 'https://example.com', '娴嬭瘯閮ㄩ棬' WHERE NOT EXISTS (SELECT 1 FROM sites);
