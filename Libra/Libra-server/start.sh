#!/bin/bash
# Libra 服务管理脚本
# 路径: /opt/Libra/Libra-server/start.sh

API_PID=$(ps aux | grep 'app_batch.py' | grep -v grep | awk '{print $2}')
if [ -n "$API_PID" ]; then
    echo "Stopping old API (PID: $API_PID)..."
    kill $API_PID 2>/dev/null
    sleep 1
fi

SERVE_PID=$(ps aux | grep 'serve.py' | grep -v grep | awk '{print $2}')
if [ -n "$SERVE_PID" ]; then
    echo "Stopping old server (PID: $SERVE_PID)..."
    kill $SERVE_PID 2>/dev/null
    sleep 1
fi

echo "Starting Libra API on port 5188..."
cd /opt/Libra/Libra-server
nohup python app_batch.py > /opt/Libra/libra_server.log 2>&1 &
sleep 2

echo "Starting Libra All-in-One server on port 5189..."
nohup python serve.py > /opt/Libra/serve.log 2>&1 &
sleep 2

echo ""
echo "=== Libra Services ==="
ss -tlnp | grep -E "5188|5189"
echo ""
curl -s http://localhost:5189/api/health
echo ""
