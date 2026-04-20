#!/bin/bash
# Libra Deploy Script - Run on server via SSH
# Usage: bash deploy.sh

set -e
cd /opt/Libra/Libra-server

echo "[1] Check available languages..."
which node && echo "Node.js: $(node --version)" || echo "Node.js: NOT FOUND"
which python3 && echo "Python: $(python3 --version)" || echo "Python: NOT FOUND"
which go && echo "Go: $(go version | cut -d' ' -f3)" || echo "Go: NOT FOUND"

echo "[2] Kill old Flask processes..."
pkill -f "python3 app_batch" 2>/dev/null || true
sleep 2

echo "[3] Stop serve.py on 5189..."
pkill -f "serve.py" 2>/dev/null || true
ss -tlnp | grep -E ":5188|:5189" || echo "Ports are free"

echo "[4] Deploy Node.js server..."
# Copy Node.js server.js
cp server.js /opt/Libra/Libra-server/server.js

echo "[5] Start Node.js API on 5188..."
cd /opt/Libra/Libra-server
node server.js > /opt/Libra/node_api.log 2>&1 &
echo "Node.js started, PID=$!"
sleep 3

echo "[6] Check port 5188..."
ss -tlnp | grep :5188

echo "[7] Test API..."
curl -s http://localhost:5188/api/health

echo "[8] Start serve.py on 5189..."
cd /opt/Libra/Libra-server
node serve.js > /opt/Libra/serve.log 2>&1 &
echo "serve started, PID=$!"
sleep 2

echo "[9] Final port check..."
ss -tlnp | grep -E ":5188|:5189"

echo "[10] Test scan..."
curl -s -X POST http://localhost:5188/api/scan \
  -H "Content-Type: application/json" \
  -d '{"url":"https://httpbin.org/get","scan_type":"HomePage_Scan"}'

echo ""
echo "=== DONE ==="
