#!/bin/bash
# 重新编译 Libra Go API (CGO=1 启用 sqlite3)
set -e

cd /opt/Libra/Libra-server/go

# 停止旧进程
pkill -f libra-api-new || true

# 编译 Linux 二进制 (CGO=1)
CGO_ENABLED=1 go build -ldflags="-s -w" -o libra-api-new-linux .

echo "编译完成: $(ls -lh libra-api-new-linux)"

# 重启
nohup ./libra-api-new-linux -port :5188 -dir /opt/Libra -workers 10 > /opt/Libra/go-api.log 2>&1 &
echo "已启动 PID: $!"

sleep 2
curl -s http://127.0.0.1:5188/api/health
echo ""
