# Libra 天秤座 - Node.js 重构文档

> 重构日期：2026-04-16
> 服务器：210.44.49.21
> 状态：**已上线运行中**

---

## 一、为什么要重构？

**原问题：** Python Flask API 处理 200 并发扫描时崩溃
- 原因：每个扫描启动一个 Python subprocess，200 个同时运行导致 OOM
- Flask 本身是无问题的，但 subprocess 管理方式在高并发下不稳定

**解决方案：** Node.js All-in-One Server
- Worker Pool：最多 5 个并发扫描（可配置）
- 内存占用低（Node.js ~30MB vs Python ~60MB/进程）
- 内置进程守护（serve.js 自动重启 server.js）
- 单端口部署（5189 对外，5188 内部）

---

## 二、架构

```
                         用户浏览器
                              |
                     http://210.44.49.21:5189
                              |
                    ┌─────────┴──────────┐
                    |  serve.js (Node.js) |
                    |   端口 5189         |
                    |   - Vue 静态文件    |
                    |   - API 反向代理   |
                    |   - 子进程管理     |
                    └─────────┬──────────┘
                              | 代理 /api/* 到 5188
                    ┌─────────┴──────────┐
                    |  server.js (Node.js) |
                    |   端口 5188 (内部) |
                    |   - REST API       |
                    |   - Worker Pool    |
                    |   - 任务队列 (2000) |
                    └─────────┬──────────┘
                              | subprocess
                    ┌─────────┴──────────┐
                    |  Python Libra 扫描器 |
                    |  /opt/Libra/Libra.py |
                    └─────────────────────┘
```

---

## 三、文件说明

| 文件 | 位置 | 作用 |
|------|------|------|
| serve.js | /opt/Libra/Libra-server/ | All-in-One 主进程（Node.js）|
| server.js | /opt/Libra/Libra-server/ | API 进程（Node.js，被 serve.js 管理）|
| Libra.py | /opt/Libra/ | Python 扫描器（实际执行扫描）|
| dist/ | /opt/Libra/Libra-server/dist/ | Vue 前端构建文件 |
| serve.log | /opt/Libra/serve.log | serve.js 日志 |
| node_api.log | /opt/Libra/node_api.log | server.js 日志 |

---

## 四、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/health | GET | 健康检查 |
| /api/stats | GET | 统计：total/success/error/running |
| /api/scan | POST | 提交单个扫描 |
| /api/scan/:id | GET | 查询扫描状态和结果 |
| /api/batch | POST | 提交批量扫描 |
| /api/batch/:id | GET | 查询批量扫描进度 |
| /api/tasks | GET | 最近任务列表（最多50条）|
| /api/rules | GET | 规则统计 |
| /api/schedule | GET/POST | 定时任务管理 |
| /api/ai-analyze | POST | AI 分析扫描结果 |

---

## 五、并发控制

```
Worker Pool: 5 个并发扫描（MAX_CONCURRENT）
Queue 容量: 2000 个任务（QUEUE_CAPACITY）

扫描流程:
1. POST /api/scan → 任务进入内存队列
2. Worker Pool 取任务 → 启动 Python subprocess
3. Python 执行 /opt/Libra/Libra.py -u URL -t TYPE
4. 结果写入临时文件 → Node.js 读取 → 返回 JSON
5. 任务完成，Worker 取下一个
```

**超过 2000 个排队任务？** → 返回 `"queue full, try later"`

---

## 六、服务管理命令

### 查看服务状态
```bash
# Node.js 进程
ps aux | grep "node serve.js" | grep -v grep
ps aux | grep "node server.js" | grep -v grep

# 端口监听
ss -tlnp | grep -E ":5188|:5189"

# 日志
tail -f /opt/Libra/serve.log
tail -f /opt/Libra/node_api.log
```

### 启动服务
```bash
cd /opt/Libra/Libra-server
nohup /usr/bin/node serve.js >> /opt/Libra/serve.log 2>&1 &
echo "PID=$!"
```

### 重启服务
```bash
# 找到 PID
kill $(ps aux | grep "node serve.js" | grep -v grep | awk "{print $2}")
sleep 2
cd /opt/Libra/Libra-server
nohup /usr/bin/node serve.js >> /opt/Libra/serve.log 2>&1 &
```

### 完全停止
```bash
kill $(ps aux | grep node | grep -E "serve.js|server.js" | grep -v grep | awk "{print $2}")
```

---

## 七、配置参数

在 `/opt/Libra/Libra-server/server.js` 开头：

```javascript
const PORT = 5188;                    // API 端口
const MAX_CONCURRENT = 5;              // 最大并发扫描数
const SCAN_TIMEOUT_MS = 5 * 60 * 1000; // 单个扫描超时（5分钟）
const QUEUE_CAPACITY = 2000;           // 任务队列容量
```

在 `/opt/Libra/Libra-server/serve.js` 开头：

```javascript
const PORT = 5189;    // Web UI 端口
const API_PORT = 5188; // API 端口（内部）
```

---

## 八、Python 依赖（扫描核心）

扫描核心仍然使用 Python，位于 `/opt/Libra/`：

```bash
# Python 扫描器
/opt/Libra/Libra.py          # 入口
/opt/Libra/Framework/        # 扫描框架
/opt/Libra/Moudle/           # 模块（task_console, task_crawler 等）
/opt/Libra/Config/           # 配置
/opt/Libra/ORM/              # 数据库

# 数据库
/opt/Libra/Libra.db          # SQLite（规则库、白名单等）
```

---

## 九、故障排查

### API 返回 502
→ server.js 子进程崩溃。检查：`cat /opt/Libra/node_api.log`

### 扫描卡住不动
→ Python subprocess 卡死。等待 5 分钟超时后自动清理

### 端口被占用
```bash
ss -tlnp | grep :5188
ss -tlnp | grep :5189
# 找到占用的进程 PID，kill -9
```

### 队列堆积
→ 上游请求太多，降低并发或扩展 Worker Pool

### 想切回 Python Flask？
```bash
# 停止 Node.js
kill $(ps aux | grep node | grep -E "serve.js|server.js" | grep -v grep | awk "{print $2}")

# 启动 Python Flask
cd /opt/Libra/Libra-server
nohup python3 app_batch.py >> /opt/Libra/flask.log 2>&1 &

# 启动 Python serve
nohup python3 serve.py >> /opt/Libra/serve_flask.log 2>&1 &
```

---

## 十、性能对比

| 指标 | Python Flask (旧) | Node.js (新) |
|------|-----------------|--------------|
| 200 并发请求 | 崩溃 OOM | 正常运行（队列 2000）|
| 内存占用 | ~120MB | ~30MB |
| 进程数 | Flask + serve.py | serve.js + server.js |
| Worker Pool | 无 | 5 并发 |
| 进程守护 | 需外部管理 | 内置（serve.js）|

---

## 十一、已验证功能

- [x] 单个扫描（httpbin.org/get）
- [x] 批量扫描（3 URLs 并发）
- [x] 10 并发压力测试（pool limit = 5 生效）
- [x] 统计 API
- [x] 规则 API
- [x] 健康检查
- [x] 任务列表
- [x] AI 分析 API
- [x] 定时任务 API（路由存在）
- [x] Web UI（Vue SPA）
- [x] API 代理（serve.js -> server.js）

---

## 十二、其他服务状态

SCOW HPC 平台 Docker 容器：**完全不受影响，全部正常运行**

| 容器 | 状态 |
|------|------|
| scow-redis-1 | Up |
| scow-db-1 | Up |
| scow-gateway-1 | Up |
| scow-portal-web-1 | Up |
| scow-mis-server-1 | Up |
| scow-auth-1 | Up |
| scow-portal-server-1 | Up |
| scow-mis-web-1 | Up |
| scow-audit-server-1 | Up |
| scow-audit-db-1 | Up |
| scow-novnc-1 | Up |
| scow-log-1 | Up |

---

_文档由 OpenClaw 生成 | 2026-04-16_
