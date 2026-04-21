# API 鎺ュ彛鏂囨。

ORION 鍚庣 API 閲囩敤 RESTful 璁捐锛岃璇佹柟寮忎负 JWT Token銆?
**Base URL:** `http://localhost:5188/api`  
**璧勪骇 API Base URL:** `http://localhost:5187/api`

---

## 璁よ瘉

### 鐧诲綍

```http
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "Qau_2026@%1"
}
```

**鍝嶅簲:**
```json
{
  "code": 0,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "username": "admin"
}
```

> 鈿狅笍 鍚庣画璇锋眰闇€鍦?Header 涓惡甯? `Authorization: Bearer <token>`

---

## 鎵弿鎺ュ彛

### 鍙戣捣鎵弿

```http
POST /api/scan
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://example.edu.cn",
  "scan_type": "HomePage_Scan"
}
```

**scan_type 鍙€夊€?**
- `HomePage_Scan` - 棣栭〉鎵弿
- `Full_Scan` - 鍏ㄧ珯鎵弿
- `Deep_Scan` - 娣卞害鎵弿

**鍝嶅簲:**
```json
{
  "code": 0,
  "task_id": "1713512345678-a1b2c3",
  "message": "鎵弿浠诲姟宸叉彁浜?
}
```

### 鏌ヨ鎵弿鐘舵€?
```http
GET /api/scan/:taskId
Authorization: Bearer <token>
```

**鍝嶅簲:**
```json
{
  "code": 0,
  "task_id": "1713512345678-a1b2c3",
  "status": "running",
  "progress": 65,
  "result": null
}
```

### 鍒犻櫎鎵弿浠诲姟

```http
DELETE /api/scan/:taskId
Authorization: Bearer <token>
```

### 鎵弿鍘嗗彶鍒楄〃

```http
GET /api/tasks?limit=100&offset=0
Authorization: Bearer <token>
```

**鍝嶅簲:**
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

## 鎵归噺鎵弿

### 鍒涘缓鎵归噺鎵弿

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

**鍝嶅簲:**
```json
{
  "code": 0,
  "batch_id": "batch-1713512345678",
  "total": 3,
  "message": "鎵归噺鎵弿宸插垱寤?
}
```

### 鏌ヨ鎵归噺鎵弿鐘舵€?
```http
GET /api/batch/:batchId
Authorization: Bearer <token>
```

---

## 瀹氭椂浠诲姟

### 鍒涘缓瀹氭椂浠诲姟

```http
POST /api/schedule
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "姣忓懆涓€渚嬭鎵弿",
  "url": "https://example.edu.cn",
  "scan_type": "HomePage_Scan",
  "cron": "0 8 * * 1"
}
```

### 瀹氭椂浠诲姟鍒楄〃

```http
GET /api/schedule
Authorization: Bearer <token>
```

### 鎵嬪姩瑙﹀彂瀹氭椂浠诲姟

```http
POST /api/schedule/:jobId/run
Authorization: Bearer <token>
```

---

## 鎶ュ憡

### 涓嬭浇鎶ュ憡

```http
GET /api/report/:taskId?format=pdf
Authorization: Bearer <token>
```

**format 鍙€夊€?** `json`, `pdf`, `html`

---

## 缁熻涓庣洃鎺?
### 濞佽儊缁熻鑱氬悎

```http
GET /api/threat-summary
Authorization: Bearer <token>
```

**鍝嶅簲:**
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

### 鐩戞帶闈㈡澘鏁版嵁

```http
GET /api/dashboard/stats
Authorization: Bearer <token>
```

---

## 璧勪骇鎺ュ彛 (绔彛 5187)

### 璧勪骇鍒楄〃

```http
GET /api/assets?page=1&page_size=20&search=example
Authorization: Bearer <token>
```

### 娣诲姞 IP 娈?
```http
POST /api/assets/ip-ranges
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "鍔炲叕缃戞",
  "ip_range": "192.168.1.0/24",
  "ports": "80,443,8080,5188"
}
```

### 瑙﹀彂 IP 娈垫壂鎻?
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

### 鍩熷悕鐖彇

```http
POST /api/assets/scan/domain
Authorization: Bearer <token>
Content-Type: application/json

{
  "domain": "qau.edu.cn",
  "recursive": true
}
```

### 璇佷功瀵煎叆

```http
POST /api/assets/scan/cert
Authorization: Bearer <token>
Content-Type: application/json

{
  "cert_pem": "-----BEGIN CERTIFICATE-----..."
}
```

### 绡℃敼鍛婅鍒楄〃

```http
GET /api/assets/alerts
Authorization: Bearer <token>
```

---

## 瑙勫垯绠＄悊

### 瑙勫垯鍒楄〃

```http
GET /api/rules
Authorization: Bearer <token>
```

### 瀵煎嚭瑙勫垯

```http
GET /api/rules?format=export
Authorization: Bearer <token>
```

---

## 閿欒鐮?
| 閿欒鐮?| 璇存槑 |
|--------|------|
| 0 | 鎴愬姛 |
| 1001 | 鍙傛暟閿欒 |
| 1002 | 璁よ瘉澶辫触 |
| 1003 | Token 杩囨湡 |
| 2001 | 鎵弿澶辫触 |
| 2002 | 鐩爣涓嶅彲杈?|
| 3001 | 鏁版嵁搴撻敊璇?|
| 3002 | 鏂囦欢绯荤粺閿欒 |

---

*API 鏂囨。鏈€鍚庢洿鏂? 2026-04-20*
