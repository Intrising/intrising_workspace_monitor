#!/bin/bash
# 測試 Web UI 認證功能

echo "================================"
echo "Web UI 認證測試"
echo "================================"
echo ""

# 從 .env 讀取配置
if [ -f "../.private/.env" ]; then
    source ../.private/.env
elif [ -f ".private/.env" ]; then
    source .private/.env
fi

HOST=${WEBHOOK_HOST:-localhost}
PORT=${WEBHOOK_PORT:-8080}
USERNAME=${WEB_USERNAME:-admin}
PASSWORD=${WEB_PASSWORD}

BASE_URL="http://${HOST}:${PORT}"

echo "測試目標: ${BASE_URL}"
echo "用戶名: ${USERNAME}"
echo ""

# 測試 1: Health endpoint（不需要認證）
echo "測試 1: 健康檢查端點（不需要認證）"
echo "GET /health"
response=$(curl -s -w "\n%{http_code}" ${BASE_URL}/health)
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" == "200" ]; then
    echo "✅ 通過 - HTTP $http_code"
    echo "   回應: $body"
else
    echo "❌ 失敗 - HTTP $http_code"
fi
echo ""

# 測試 2: 首頁（需要認證 - 無認證）
echo "測試 2: 首頁（無認證）"
echo "GET /"
http_code=$(curl -s -o /dev/null -w "%{http_code}" ${BASE_URL}/)

if [ "$http_code" == "401" ]; then
    echo "✅ 通過 - HTTP $http_code（正確拒絕）"
elif [ "$http_code" == "200" ]; then
    echo "⚠️  警告 - HTTP $http_code（未設置密碼，允許訪問）"
else
    echo "❌ 失敗 - HTTP $http_code"
fi
echo ""

# 測試 3: 首頁（需要認證 - 錯誤密碼）
echo "測試 3: 首頁（錯誤密碼）"
echo "GET / (wrong password)"
http_code=$(curl -s -o /dev/null -w "%{http_code}" -u ${USERNAME}:wrong_password ${BASE_URL}/)

if [ "$http_code" == "401" ]; then
    echo "✅ 通過 - HTTP $http_code（正確拒絕）"
elif [ "$http_code" == "200" ]; then
    echo "⚠️  警告 - HTTP $http_code（未設置密碼或密碼錯誤但仍允許訪問）"
else
    echo "❌ 失敗 - HTTP $http_code"
fi
echo ""

# 測試 4: 首頁（需要認證 - 正確密碼）
if [ ! -z "$PASSWORD" ]; then
    echo "測試 4: 首頁（正確密碼）"
    echo "GET / (with auth)"
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -u ${USERNAME}:${PASSWORD} ${BASE_URL}/)

    if [ "$http_code" == "200" ]; then
        echo "✅ 通過 - HTTP $http_code"
    else
        echo "❌ 失敗 - HTTP $http_code"
    fi
    echo ""
else
    echo "⚠️  跳過測試 4: WEB_PASSWORD 未設置"
    echo ""
fi

# 測試 5: API 端點（需要認證）
if [ ! -z "$PASSWORD" ]; then
    echo "測試 5: API 端點（需要認證）"
    echo "GET /api/tasks"
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -u ${USERNAME}:${PASSWORD} ${BASE_URL}/api/tasks)

    if [ "$http_code" == "200" ]; then
        echo "✅ 通過 - HTTP $http_code"
    else
        echo "❌ 失敗 - HTTP $http_code"
    fi
    echo ""
else
    echo "⚠️  跳過測試 5: WEB_PASSWORD 未設置"
    echo ""
fi

echo "================================"
echo "測試完成"
echo "================================"
echo ""

if [ -z "$PASSWORD" ]; then
    echo "⚠️  安全警告："
    echo "   WEB_PASSWORD 未設置，Web UI 不需要認證！"
    echo "   請在 .private/.env 中設置 WEB_PASSWORD"
    echo ""
fi
