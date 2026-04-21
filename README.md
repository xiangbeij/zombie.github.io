# ⚖️ ShieldEye - 网站安全监测平台

> 基于 Python + Go 的网站安全扫描与资产管理系统

---

## 🎯 项目简介

ShieldEye（天秤座）是一款面向教育行业和 HPC 环境的网站安全监测平台，支持批量扫描、定时任务、资产发现、篡改监控、报告导出和 AI 智能分析。

### 核心功能

| 功能 | 说明 |
|------|------|
| 🔍 **批量安全扫描** | 暗链检测、WebShell后门识别、敏感信息泄露、违规内容扫描 |
| ⏰ **定时任务** | 支持 Cron 表达式定时扫描，可按天/周/月周期执行 |
| 🌍 **资产发现** | IP段扫描、域名爬取、SSL证书导入，完整资产管理 |
| 📸 **篡改监控** | 页面快照 + Hash 对比，变化超30%自动告警 |
| 📊 **监控面板** | 威胁聚合统计、扫描趋势图、告警列表 |
| 📄 **报告导出** | 支持 PDF 和 JSON 格式扫描报告 |
| 🤖 **AI 分析** | 集成本地 Ollama 模型，智能分析扫描结果 |
| 🔐 **认证授权** | JWT Token 登录认证 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    用户浏览器                        │
│              Vue 3 + Element Plus UI                │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────────┐  ┌─────────────────────────┐
│    Go API (主服务)         │  │  Flask 资产 API          │
│    Port 5188              │  │  Port 5187               │
│  · 扫描/定时/规则/报告     │  │  · 资产增删改查            │
│  · Worker Pool (20并发)   │  │  · IP段扫描              │
│  · JWT 认证               │  │  · 域名爬取/证书导入       │
│  · SQLite 数据库          │  │  · 篡改告警               │
└──────────────────────────┘  └─────────────────────────┘
               ▲                      ▲
               │                      │
        ┌──────┴──────────────────────┘
        │         Python Libra.py (扫描核心)
        │         配置: Config/
        │         框架: Framework/
        │         模块: Moudle/ + ORM/
        │         工具: Tools/
        └───────────────────────────────────► 目标网站
```

---

## 📁 项目结构

```
Libra/                        # 完整源代码
├── Libra.py                  # 扫描入口（Python）
├── Libra.db                  # SQLite 数据库
├── Libra-server/             # 后端服务
│   ├── go/                   # Go API 源码
│   │   ├── main.go          # 主入口
│   │   ├── handlers.go      # HTTP 处理器
│   │   ├── workers.go       # Worker Pool
│   │   ├── state.go         # 状态管理
│   │   ├── models.go        # 数据模型
│   │   └── db.go            # SQLite 操作
│   ├── libra_assets.py      # Flask 资产API
│   ├── app.py               # Flask 主服务（旧）
│   └── migrations/          # 数据库迁移脚本
├── Libra-web/               # Vue 3 前端
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   │   ├── Dashboard.vue      # 监控面板
│   │   │   ├── Scan.vue           # 发起扫描
│   │   │   ├── BatchScan.vue      # 批量扫描
│   │   │   ├── History.vue        # 扫描历史
│   │   │   ├── Schedule.vue       # 定时任务
│   │   │   ├── Rules.vue          # 规则管理
│   │   │   ├── Assets.vue         # 资产发现
│   │   │   ├── Login.vue          # 登录页面
│   │   │   └── ...
│   │   ├── api/libra.js     # API 封装
│   │   ├── router/          # Vue Router
│   │   └── App.vue          # 根组件
│   └── dist/                 # 构建产物
├── Framework/               # 扫描框架核心
│   ├── Libra_Console.py     # 控制台任务
│   └── task_console.py
├── Moudle/                  # 扫描模块
│   ├── task_crawler.py     # 网页爬虫
│   ├── task_response.py    # 响应分析
│   └── task_rulefind.py    # 规则匹配
├── ORM/                     # 数据库操作
│   └── db_*.py
├── Config/                  # 配置文件
│   ├── config_banner.py
│   ├── config_crawler.py
│   ├── config_db.py
│   └── ...
└── Tools/                   # 工具函数
```

---

## 🚀 快速部署

### 方式一：直接部署（推荐）

```bash
# 1. 安装依赖
pip install -r Libra/requirements.txt

# 2. 安装 Go 1.21+
# 3. 编译 Go API
cd Libra/Libra-server/go
go build -o libra-api-new-linux .
CGO_ENABLED=1 go build -o libra-api-new2-linux .

# 4. 启动 Flask API
python Libra/Libra-server/app_batch.py &

# 5. 启动 Go API
./Libra/Libra-server/go/libra-api-new-linux &

# 6. 启动资产 Flask API
python Libra/Libra-server/libra_assets.py &

# 7. 构建前端
cd Libra/Libra-web
npm install
npm run build

# 8. 启动静态文件服务
python Libra/Libra-server/serve.py
```

### 方式二：Docker 部署

```bash
cd Libra
python deploy_docker2.py
```

---

## 🔌 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/scan` | 发起扫描 |
| GET | `/api/scan/:taskId` | 查询扫描状态 |
| GET | `/api/tasks` | 扫描历史列表 |
| POST | `/api/batch` | 批量扫描 |
| GET | `/api/schedule` | 定时任务列表 |
| POST | `/api/schedule` | 创建定时任务 |
| GET | `/api/report/:taskId` | 下载报告 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/threat-summary` | 威胁统计 |
| GET | `/api/assets/stats` | 资产统计 |
| GET | `/api/assets/alerts` | 篡改告警列表 |

详细 API 文档见 [docs/api.md](docs/api.md)

---

## ⚙️ 配置说明

主要配置文件位于 `Libra/Config/`:

- `config_db.py` - 数据库连接
- `config_crawler.py` - 爬虫参数（超时、代理、Header）
- `config_proxies.py` - 代理池配置
- `config_requests.py` - HTTP 请求配置

---

## 📋 版本信息

- **前端框架:** Vue 3 + Vite + Element Plus + ECharts
- **后端:** Go 1.21 + Python Flask
- **数据库:** SQLite
- **部署环境:** Rocky Linux 9.7 + Docker

---

## 📄 许可证

MIT License

---

*ShieldEye* ⚖️🛡️
