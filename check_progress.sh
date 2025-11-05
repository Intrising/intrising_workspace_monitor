#!/bin/bash
# PR 審查進度查詢腳本

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="http://localhost:8080"

echo "=========================================="
echo "     PR Auto-Reviewer 進度查詢"
echo "=========================================="
echo ""

# 檢查服務是否運行
if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
    echo -e "${RED}錯誤: 服務未運行或無法連接${NC}"
    echo "請確認服務已啟動: docker ps | grep pr-reviewer"
    exit 1
fi

# 獲取任務統計
RESPONSE=$(curl -s "${API_URL}/api/tasks")

if [ $? -ne 0 ]; then
    echo -e "${RED}錯誤: 無法獲取任務資訊${NC}"
    exit 1
fi

# 使用 jq 解析 JSON
TOTAL=$(echo "$RESPONSE" | jq -r '.total')
QUEUED=$(echo "$RESPONSE" | jq -r '.stats.queued')
PROCESSING=$(echo "$RESPONSE" | jq -r '.stats.processing')
COMPLETED=$(echo "$RESPONSE" | jq -r '.stats.completed')
FAILED=$(echo "$RESPONSE" | jq -r '.stats.failed')

# 顯示統計資訊
echo -e "${BLUE}📊 任務統計${NC}"
echo "─────────────────────────────────────────"
echo -e "總任務數: ${TOTAL}"
echo -e "${YELLOW}⏳ 等待中: ${QUEUED}${NC}"
echo -e "${BLUE}🔄 處理中: ${PROCESSING}${NC}"
echo -e "${GREEN}✅ 已完成: ${COMPLETED}${NC}"
echo -e "${RED}❌ 失敗: ${FAILED}${NC}"
echo ""

# 顯示任務列表
echo -e "${BLUE}📋 任務詳情${NC}"
echo "─────────────────────────────────────────"

echo "$RESPONSE" | jq -r '.tasks[] |
    "\(.status |
        if . == "queued" then "⏳"
        elif . == "processing" then "🔄"
        elif . == "completed" then "✅"
        else "❌" end) [\(.progress)%] \(.pr_id) - \(.pr_title // "無標題")
    \(.message)"' | head -20

TASK_COUNT=$(echo "$RESPONSE" | jq -r '.tasks | length')
if [ "$TASK_COUNT" -gt 20 ]; then
    echo ""
    echo "... 還有 $((TASK_COUNT - 20)) 個任務未顯示"
fi

echo ""
echo "─────────────────────────────────────────"
echo "提示: 使用 'watch -n 2 ./check_progress.sh' 可實時監控"
echo "      或訪問 ${API_URL} 查看網頁版"
