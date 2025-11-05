#!/bin/bash
# 使用 curl 模拟 GitHub webhook 请求

set -e

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

WEBHOOK_URL="${1:-http://localhost:8080/webhook}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-}"

echo "=========================================="
echo "🧪 GitHub Webhook 测试工具"
echo "=========================================="
echo ""
echo "目标 URL: $WEBHOOK_URL"
echo "Secret: ${WEBHOOK_SECRET:+已设置}"
echo ""

# 测试 1: Ping 事件
echo "📡 测试 1: Ping 事件"
echo "------------------------------------------"

PING_PAYLOAD='{
  "zen": "测试 webhook 连接",
  "hook_id": 12345,
  "repository": {
    "full_name": "test-org/test-repo",
    "html_url": "https://github.com/test-org/test-repo"
  }
}'

if [ -n "$WEBHOOK_SECRET" ]; then
    SIGNATURE=$(echo -n "$PING_PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')
    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: ping" \
        -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
        -H "X-GitHub-Delivery: test-delivery-$(date +%s)" \
        -d "$PING_PAYLOAD"
else
    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: ping" \
        -H "X-GitHub-Delivery: test-delivery-$(date +%s)" \
        -d "$PING_PAYLOAD"
fi

echo -e "\n\n"

# 测试 2: Pull Request 事件
echo "📡 测试 2: Pull Request Opened 事件"
echo "------------------------------------------"

PR_PAYLOAD='{
  "action": "opened",
  "number": 123,
  "pull_request": {
    "number": 123,
    "title": "测试 PR - 修复 bug",
    "user": {
      "login": "test-user"
    },
    "html_url": "https://github.com/test-org/test-repo/pull/123",
    "head": {
      "ref": "feature-branch"
    },
    "base": {
      "ref": "main"
    },
    "created_at": "2024-03-15T10:00:00Z",
    "draft": false
  },
  "repository": {
    "full_name": "test-org/test-repo",
    "html_url": "https://github.com/test-org/test-repo"
  }
}'

if [ -n "$WEBHOOK_SECRET" ]; then
    SIGNATURE=$(echo -n "$PR_PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')
    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: pull_request" \
        -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
        -H "X-GitHub-Delivery: test-delivery-$(date +%s)" \
        -d "$PR_PAYLOAD"
else
    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: pull_request" \
        -H "X-GitHub-Delivery: test-delivery-$(date +%s)" \
        -d "$PR_PAYLOAD"
fi

echo -e "\n\n"
echo "✅ 测试完成！"
echo ""
echo "💡 提示："
echo "   - 检查服务器终端查看接收到的 webhook"
echo "   - 如果显示签名验证失败，检查 WEBHOOK_SECRET 是否一致"
