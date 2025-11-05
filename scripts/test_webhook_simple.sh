#!/bin/bash
# 简单的 webhook 测试脚本 - 不需要 Python Flask

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

WEBHOOK_URL="${1:-http://localhost:8080/webhook}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-}"

echo -e "${BLUE}=========================================="
echo "🧪 GitHub Webhook 快速测试工具"
echo -e "==========================================${NC}"
echo ""
echo -e "目标 URL: ${YELLOW}$WEBHOOK_URL${NC}"
echo -e "Secret: ${WEBHOOK_SECRET:+${GREEN}已设置${NC}}${WEBHOOK_SECRET:-${RED}未设置${NC}}"
echo ""

# 函数：计算签名
calculate_signature() {
    local payload="$1"
    if [ -n "$WEBHOOK_SECRET" ]; then
        echo -n "$payload" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //'
    fi
}

# 测试 1: 健康检查
echo -e "${BLUE}📡 测试 1: 健康检查${NC}"
echo "------------------------------------------"
HEALTH_URL="${WEBHOOK_URL%/webhook}/health"
echo "GET $HEALTH_URL"
if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务器响应正常${NC}"
    curl -s "$HEALTH_URL" | python3 -m json.tool 2>/dev/null || curl -s "$HEALTH_URL"
else
    echo -e "${RED}❌ 服务器无响应！${NC}"
    echo "请确保测试服务器正在运行："
    echo "  python3 test_webhook.py"
    echo "  或"
    echo "  docker-compose -f docker-compose.webhook-test.yml up"
    exit 1
fi
echo ""

# 测试 2: Ping 事件
echo -e "${BLUE}📡 测试 2: 发送 Ping 事件${NC}"
echo "------------------------------------------"

PING_PAYLOAD='{
  "zen": "测试 webhook 连接成功！",
  "hook_id": 123456,
  "repository": {
    "full_name": "Intrising/test-repo",
    "html_url": "https://github.com/Intrising/test-repo"
  }
}'

if [ -n "$WEBHOOK_SECRET" ]; then
    SIGNATURE=$(calculate_signature "$PING_PAYLOAD")
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: ping" \
        -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
        -H "X-GitHub-Delivery: test-delivery-ping-$(date +%s)" \
        -d "$PING_PAYLOAD")
else
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: ping" \
        -H "X-GitHub-Delivery: test-delivery-ping-$(date +%s)" \
        -d "$PING_PAYLOAD")
fi

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Ping 事件发送成功 (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ 请求失败 (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# 测试 3: Pull Request 事件
echo -e "${BLUE}📡 测试 3: 发送 Pull Request 事件${NC}"
echo "------------------------------------------"

PR_PAYLOAD='{
  "action": "opened",
  "number": 999,
  "pull_request": {
    "number": 999,
    "title": "🧪 测试 PR - Webhook 功能验证",
    "user": {
      "login": "test-developer"
    },
    "html_url": "https://github.com/Intrising/test-repo/pull/999",
    "head": {
      "ref": "test-webhook-feature"
    },
    "base": {
      "ref": "main",
      "repo": {
        "full_name": "Intrising/test-repo"
      }
    },
    "created_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "draft": false
  },
  "repository": {
    "full_name": "Intrising/test-repo",
    "html_url": "https://github.com/Intrising/test-repo"
  }
}'

if [ -n "$WEBHOOK_SECRET" ]; then
    SIGNATURE=$(calculate_signature "$PR_PAYLOAD")
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: pull_request" \
        -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
        -H "X-GitHub-Delivery: test-delivery-pr-$(date +%s)" \
        -d "$PR_PAYLOAD")
else
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: pull_request" \
        -H "X-GitHub-Delivery: test-delivery-pr-$(date +%s)" \
        -d "$PR_PAYLOAD")
fi

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Pull Request 事件发送成功 (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ 请求失败 (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# 总结
echo -e "${BLUE}=========================================="
echo "✅ 测试完成！"
echo -e "==========================================${NC}"
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo "   1. 检查测试服务器终端查看接收到的详细信息"
echo "   2. 如果所有测试通过，webhook 配置正确"
echo "   3. 接下来可以在 GitHub 仓库中配置真实的 webhook"
echo ""
echo -e "${YELLOW}📚 下一步：${NC}"
echo "   - 在 GitHub 仓库设置 webhook"
echo "   - Payload URL: http://your-server-ip:8080/webhook"
echo "   - Content type: application/json"
echo "   - Secret: 你的 WEBHOOK_SECRET"
echo "   - 选择 Pull requests 事件"
