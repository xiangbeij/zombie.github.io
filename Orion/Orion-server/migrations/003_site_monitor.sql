-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?-- 缃戠珯鐘舵€佺洃鎺фā鍧?- 鏁版嵁搴撹縼绉昏剼鏈?v3
-- 杩愯鏂瑰紡: sqlite3 /opt/Orion/orion.db < migrations/003_site_monitor.sql
-- 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
-- 缃戠珯鐩戞帶鐩爣琛?CREATE TABLE IF NOT EXISTS site_monitors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,           -- 鐩戞帶鍚嶇О锛屽"瀛︽牎涓婚〉"
    url             TEXT    NOT NULL,           -- 鐩戞帶 URL
    host            TEXT    DEFAULT '',          -- 鎻愬彇鐨?host
    check_interval  INTEGER DEFAULT 60,         -- 妫€娴嬮棿闅旓紙绉掞級锛岄粯璁?0绉?    enabled         INTEGER DEFAULT 1,          -- 1=鍚敤 0=鏆傚仠
    timeout_seconds INTEGER DEFAULT 10,         -- 瓒呮椂绉掓暟
    last_status     TEXT    DEFAULT 'unknown',  -- unknown | online | offline | error
    last_status_code INTEGER DEFAULT 0,         -- HTTP 鐘舵€佺爜
    last_rtt_ms     INTEGER DEFAULT 0,          -- 涓婃鍝嶅簲鏃堕棿锛堟绉掞級
    last_checked_at TEXT    DEFAULT '',         -- 涓婃妫€娴嬫椂闂?    last_error      TEXT    DEFAULT '',          -- 涓婃閿欒淇℃伅
    ssl_expiry_date TEXT    DEFAULT '',          -- SSL 璇佷功鍒版湡鏃ユ湡
    ssl_days_left   INTEGER DEFAULT -1,         -- SSL 鍓╀綑澶╂暟锛?1=鏈娴?    ssl_valid       INTEGER DEFAULT -1,         -- 1=鏈夋晥 0=鏃犳晥 -1=闈濰TTPS鎴栨湭妫€娴?    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 鐩戞帶鍘嗗彶璁板綍
CREATE TABLE IF NOT EXISTS site_monitor_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id      INTEGER NOT NULL,
    status          TEXT    NOT NULL,           -- online | offline | error
    status_code     INTEGER DEFAULT 0,
    rtt_ms          INTEGER DEFAULT 0,          -- 鍝嶅簲鏃堕棿 ms
    error_msg       TEXT    DEFAULT '',
    ssl_days_left   INTEGER DEFAULT -1,
    checked_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (monitor_id) REFERENCES site_monitors(id) ON DELETE CASCADE
);

-- 鍒涘缓绱㈠紩
CREATE INDEX IF NOT EXISTS idx_monitors_enabled ON site_monitors(enabled);
CREATE INDEX IF NOT EXISTS idx_monitors_last_status ON site_monitors(last_status);
CREATE INDEX IF NOT EXISTS idx_monitor_history_monitor ON site_monitor_history(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_history_time ON site_monitor_history(checked_at DESC);
