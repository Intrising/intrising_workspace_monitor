#!/bin/bash
# 啟動腳本：只運行 Gateway Web 服務（不啟動 PR Monitor）

set -e

echo "Starting GitHub Workspace Monitor Services..."

# 只啟動 Gateway Web 服務
echo "Starting Gateway Web Service on port 8080..."
python gateway.py &
GATEWAY_PID=$!

echo "Gateway started. PR Monitor is disabled."

# 捕捉終止信號
trap "kill $GATEWAY_PID 2>/dev/null; exit 0" SIGTERM SIGINT

# 等待 Gateway 進程
wait $GATEWAY_PID
