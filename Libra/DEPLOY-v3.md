# Libra v3 部署指南 - 网站状态监控 + 资产API修复

## 服务器: 210.44.49.21 | 用户: lqz

---

## 第一步：数据库迁移（运行 SQL）

```bash
ssh lqz@210.44.49.21
sqlite3 /opt/Libra/Libra.db < /dev/stdin << 'EOF'
-- ═══════════════════════════════════════════════
-- 网站状态监控模块 - 数据库迁移脚本 v3
-- ═══════════════════════════════════════════════

-- 网站监控目标表
CREATE TABLE IF NOT EXISTS site_monitors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    url             TEXT    NOT NULL,
    host            TEXT    DEFAULT '',
    check_interval  INTEGER DEFAULT 60,
    enabled         INTEGER DEFAULT 1,
    timeout_seconds INTEGER DEFAULT 10,
    last_status     TEXT    DEFAULT 'unknown',
    last_status_code INTEGER DEFAULT 0,
    last_rtt_ms     INTEGER DEFAULT 0,
    last_checked_at TEXT    DEFAULT '',
    last_error      TEXT    DEFAULT '',
    ssl_expiry_date TEXT    DEFAULT '',
    ssl_days_left   INTEGER DEFAULT -1,
    ssl_valid       INTEGER DEFAULT -1,
    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- 监控历史记录
CREATE TABLE IF NOT EXISTS site_monitor_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id      INTEGER NOT NULL,
    status          TEXT    NOT NULL,
    status_code     INTEGER DEFAULT 0,
    rtt_ms          INTEGER DEFAULT 0,
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
EOF
```

验证表是否创建成功：
```bash
sqlite3 /opt/Libra/Libra.db ".tables" | grep monitor
# 应该看到: site_monitor_history  site_monitors
```

---

## 第二步：重新编译 Go 服务（添加网站监控 API）

在服务器上编译（需要 Go 1.21+）：

```bash
ssh lqz@210.44.49.21
cd /opt/Libra/Libra-server/go

# 检查 Go 版本
go version

# 编译 Linux amd64 二进制（静态编译）
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o libra-api-new-linux .

# 确认二进制生成
ls -la libra-api-new-linux
```

---

## 第三步：重启 Go API 服务

```bash
# 查看当前 Go 服务进程
ps aux | grep libra-api | grep -v grep

# 如果用 systemd 管理：
sudo systemctl restart libra-go
# 或直接重启（看实际启动方式）

# 如果是手动启动的：
pkill libra-api-new-linux
sleep 1
nohup /opt/Libra/Libra-server/go/libra-api-new-linux -port :5188 -dir /opt/Libra > /var/log/libra-go.log 2>&1 &

# 验证服务启动
curl -s http://localhost:5188/api/health | python3 -m json.tool
# 应该看到: {"status": "ok", "service": "ShieldEye API", ...}
```

---

## 第四步：重新构建前端并部署

在本地（Windows）构建 Vue 前端：

```powershell
cd E:\tool\openclaw-data\.openclaw\workspace\Libra\Libra-web

# 安装依赖（如果需要）
npm install

# 构建生产版本
npm run build
```

上传到服务器：

```bash
# 方法1：rsync 直接同步（如果安装了 rsync）
rsync -avz --delete dist/ lqz@210.44.49.21:/opt/Libra/Libra-web/

# 方法2：手动上传
scp -r dist/* lqz@210.44.49.21:/opt/Libra/Libra-web/dist/
```

---

## 第五步：验证新功能

访问 `http://210.44.49.21:5188/` 登录后：

1. **左侧菜单** → "网站监控"（新增）
2. 点击"添加监控" → 输入 URL（如 `https://www.qau.edu.cn`）
3. 点击"🔄 立即检测全部"测试是否正常工作

---

## 修复内容说明

### 1. 资产列表获取失败 ✅
- **问题**：`assetsApi` 使用了错误的 baseURL，生产环境下指向 `/api/assets-proxy`（不存在）
- **修复**：改为直接使用 `http://210.44.49.21:5187/api` 绝对路径，所有 assets API 调用均使用完整 URL

### 2. "发起扫描" → "扫描任务" ✅
- 顶部导航按钮："发起扫描" → "🔍 扫描任务"
- Sites 页面操作按钮："扫描" → "📋 扫描任务"

### 3. 网站状态监控（新增）🌟
- **数据库**：`site_monitors` + `site_monitor_history` 表
- **功能**：实时探测网站可达性 / HTTP 状态码 / 响应时间 / SSL 证书到期
- **API**：`/api/site-monitor` 系列接口
- **前端**：新增 `/monitor` 页面，包含统计卡片 + 实时检测历史

---

## 故障排查

**资产列表仍然失败？**
```bash
# 检查 Python 资产服务是否运行
curl -s http://localhost:5187/api/assets | head -c 200

# 如果没运行，启动它：
cd /opt/Libra/Libra-server
nohup python3 libra_assets.py > /var/log/libra-assets.log 2>&1 &
```

**Go 服务启动失败？**
```bash
# 查看日志
tail -50 /var/log/libra-go.log
# 或
journalctl -u libra-go -n 50
```
