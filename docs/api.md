# API 接口文档

ShieldEye 后端 API 采用 RESTful 设计，认证方式为 JWT Token。

**Base URL:** `http://localhost:5188/api`  
**资产 API Base URL:** `http://localhost:5187/api`

---

## 认证

### 登录

```http
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "Qau_2026@%1"
}
```

**响应:**
```json
{
  "code": 0,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "username": "admin"
}
```

> ⚠️ 后续请求需在 Header 中携带: `Authorization: Bearer <token>`

---

## 扫描接口

### 发起扫描

```http
POST /api/scan
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://example.edu.cn",
  "scan_type": "HomePage_Scan"
}
```

**scan_type 可选值:**
- `HomePage_Scan` - 首页扫描
- `Full_Scan` - 全站扫描
- `Deep_Scan` - 深度扫描

**响应:**
```json
{
  "code": 0,
  "task_id": "1713512345678-a1b2c3",
  "message": "扫描任务已提交"
}
```

### 查询扫描状态

```http
GET /api/scan/:taskId
Authorization: Bearer <token>
```

**响应:**
```json
{
  "code": 0,
  "task_id": "1713512345678-a1b2c3",
  "status": "running",
  "progress": 65,
  "result": null
}
```

### 删除扫描任务

```http
DELETE /api/scan/:taskId
Authorization: Bearer <token>
```

### 扫描历史列表

```http
GET /api/tasks?limit=100&offset=0
Authorization: Bearer <token>
```

**响应:**
```json
{
  "code": 0,
  "total": 42,
  "tasks": [
    {
      "id": "1713512345678-a1b2c3",
      "url": "https://example.edu.cn",
      "scan_type": "HomePage_Scan",
      "status": "completed",
      "created_at": "2026-04-20T10:00:00Z",
      "result_count": 3
    }
  ]
}
```

---

## 批量扫描

### 创建批量扫描

```http
POST /api/batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "urls": [
    "https://site1.edu.cn",
    "https://site2.edu.cn",
    "https://site3.edu.cn"
  ],
  "scan_type": "HomePage_Scan"
}
```

**响应:**
```json
{
  "code": 0,
  "batch_id": "batch-1713512345678",
  "total": 3,
  "message": "批量扫描已创建"
}
```

### 查询批量扫描状态

```http
GET /api/batch/:batchId
Authorization: Bearer <token>
```

---

## 定时任务

### 创建定时任务

```http
POST /api/schedule
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "每周一例行扫描",
  "url": "https://example.edu.cn",
  "scan_type": "HomePage_Scan",
  "cron": "0 8 * * 1"
}
```

### 定时任务列表

```http
GET /api/schedule
Authorization: Bearer <token>
```

### 手动触发定时任务

```http
POST /api/schedule/:jobId/run
Authorization: Bearer <token>
```

---

## 报告

### 下载报告

```http
GET /api/report/:taskId?format=pdf
Authorization: Bearer <token>
```

**format 可选值:** `json`, `pdf`, `html`

---

## 统计与监控

### 威胁统计聚合

```http
GET /api/threat-summary
Authorization: Bearer <token>
```

**响应:**
```json
{
  "code": 0,
  "total_threats": 127,
  "new_this_week": 5,
  "by_type": {
    "darklink": 89,
    "backdoor": 23,
    "sensitive": 15
  }
}
```

### 监控面板数据

```http
GET /api/dashboard/stats
Authorization: Bearer <token>
```

---

## 资产接口 (端口 5187)

### 资产列表

```http
GET /api/assets?page=1&page_size=20&search=example
Authorization: Bearer <token>
```

### 添加 IP 段

```http
POST /api/assets/ip-ranges
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "办公网段",
  "ip_range": "192.168.1.0/24",
  "ports": "80,443,8080,5188"
}
```

### 触发 IP 段扫描

```http
POST /api/assets/scan/ip
Authorization: Bearer <token>
Content-Type: application/json

{
  "range_id": 1,
  "ip_range": "192.168.1.0/24",
  "ports": "80,443,8080"
}
```

### 域名爬取

```http
POST /api/assets/scan/domain
Authorization: Bearer <token>
Content-Type: application/json

{
  "domain": "qau.edu.cn",
  "recursive": true
}
```

### 证书导入

```http
POST /api/assets/scan/cert
Authorization: Bearer <token>
Content-Type: application/json

{
  "cert_pem": "-----BEGIN CERTIFICATE-----..."
}
```

### 篡改告警列表

```http
GET /api/assets/alerts
Authorization: Bearer <token>
```

---

## 规则管理

### 规则列表

```http
GET /api/rules
Authorization: Bearer <token>
```

### 导出规则

```http
GET /api/rules?format=export
Authorization: Bearer <token>
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 参数错误 |
| 1002 | 认证失败 |
| 1003 | Token 过期 |
| 2001 | 扫描失败 |
| 2002 | 目标不可达 |
| 3001 | 数据库错误 |
| 3002 | 文件系统错误 |

---

*API 文档最后更新: 2026-04-20*
