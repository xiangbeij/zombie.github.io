# 部署指南

本文档详细说明如何在 Linux 服务器上部署 ShieldEye 安全监测平台。

## 环境要求

- **操作系统:** Rocky Linux 9.7 / CentOS 7+ / Ubuntu 20.04+
- **CPU:** 2 核+
- **内存:** 4GB+
- **Go:** 1.21+
- **Python:** 3.8+
- **Node.js:** 16+ (用于构建前端)

## 一、安装系统依赖

```bash
# Rocky Linux 9
sudo dnf install -y golang python3 python3-pip git

# 安装 Node.js 16
curl -fsSL https://rpm.nodesource.com/setup_16.x | sudo bash -
sudo dnf install -y nodejs

# Ubuntu
sudo apt update
sudo apt install -y golang python3-pip nodejs npm git
```

## 二、部署后端服务

### 2.1 创建目录

```bash
sudo mkdir -p /opt/Libra
sudo chown $USER:$USER /opt/Libra
```

### 2.2 上传代码

```bash
# 方法1: Git 克隆
git clone https://github.com/xiangbeij/zombie.github.io.git /tmp/libra
cp -r /tmp/libra/Libra/* /opt/Libra/

# 方法2: SCP 上传
scp -r ./Libra root@your-server:/opt/
```

### 2.3 安装 Python 依赖

```bash
cd /opt/Libra
pip3 install -r requirements.txt

# 关键依赖:
# - Flask>=2.0
# - Requests>=2.28
# - APScheduler>=3.10
# - WeasyPrint>=66.0  (PDF报告)
```

### 2.4 编译 Go API

```bash
cd /opt/Libra/Libra-server/go

# 编译主API (使用 CGO 获得完整 sqlite3 支持)
CGO_ENABLED=1 go build -o libra-api-new2-linux .

# 编译资产扫描器
CGO_ENABLED=1 go build -o libra-assets-linux .
```

### 2.5 初始化数据库

```bash
cd /opt/Libra
python3 check_init.py      # 检查初始化状态
python3 check_db.py        # 验证数据库
```

### 2.6 启动服务

```bash
# 启动 Flask API (端口 5188)
cd /opt/Libra/Libra-server
nohup python3 app_batch.py > /var/log/libra_api.log 2>&1 &
echo $! > /tmp/libra_api.pid

# 启动 Go API (端口 5188, 替换 Flask)
nohup ./go/libra-api-new2-linux > /var/log/libra_go.log 2>&1 &
echo $! > /tmp/libra_go.pid

# 启动资产 Flask API (端口 5187)
nohup python3 libra_assets.py > /var/log/libra_assets.log 2>&1 &
echo $! > /tmp/libra_assets.pid

# 启动静态文件服务 (端口 5189)
nohup python3 serve.py > /var/log/libra_web.log 2>&1 &
echo $! > /tmp/libra_web.pid
```

### 2.7 验证服务

```bash
# 检查端口
ss -tlnp | grep -E '5187|5188|5189'

# 测试 API
curl http://localhost:5188/api/health
curl http://localhost:5187/health
```

## 三、部署前端

### 3.1 构建前端

```bash
cd /opt/Libra/Libra-web
npm install
npm run build
```

### 3.2 配置 Nginx (可选，用于生产环境)

```nginx
server {
    listen 80;
    server_name your-domain.edu.cn;

    # 前端静态文件
    location / {
        root /opt/Libra/Libra-web/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api {
        proxy_pass http://127.0.0.1:5188;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 四、服务管理

### 4.1 启动所有服务

```bash
# 使用项目自带脚本
python3 /opt/Libra/start_libra.py

# 或手动
bash /opt/Libra/deploy.sh
```

### 4.2 重启服务

```bash
python3 /opt/Libra/restart_libra.py
```

### 4.3 查看状态

```bash
python3 /opt/Libra/check_status.py
```

## 五、Docker 部署（可选）

```bash
cd /opt/Libra
python3 build_docker.py    # 构建镜像
python3 deploy_docker2.py   # 部署容器
```

## 六、常见问题

### Q: API 返回空数据
A: 检查 SQLite 数据库权限，确保 Go 二进制使用 `CGO_ENABLED=1` 编译。

### Q: 前端无法访问
A: 确认 5189 端口已开放，静态文件服务正常运行。

### Q: 扫描任务堆积
A: Worker Pool 默认20并发，队列容量2000。检查任务积压情况：
```bash
curl http://localhost:5188/api/stats
```

### Q: PDF 报告无法生成
A: 安装 WeasyPrint 依赖：
```bash
pip3 install WeasyPrint>=66.0
# 还需要系统级依赖（参考 WeasyPrint 文档）
```

## 七、安全配置

### 7.1 修改默认密码

首次部署后请立即修改 `admin` 账户密码。

### 7.2 防火墙配置

```bash
# 仅开放必要端口
firewall-cmd --permanent --add-port=5188/tcp  # API
firewall-cmd --permanent --add-port=5187/tcp  # 资产API
firewall-cmd --permanent --add-port=5189/tcp  # Web UI
firewall-cmd --reload
```

### 7.3 禁止端口21/80

> ⚠️ 注意：系统已配置跳过 FTP(21) 和 SCOW HPC 的 Web(80)，请勿在生产环境开放这些端口。

---

*部署文档最后更新: 2026-04-20*
