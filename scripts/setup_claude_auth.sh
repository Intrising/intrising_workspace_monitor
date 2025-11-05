#!/bin/bash
# Claude CLI 認證設置腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "🔐 Claude CLI 認證設置"
echo -e "==========================================${NC}"
echo ""

# 檢查 Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安裝${NC}"
    exit 1
fi

# 步驟 1: 構建映像
echo -e "${BLUE}步驟 1/4: 構建 Docker 映像...${NC}"
docker compose -f docker-compose.reviewer-cli.yml build

# 步驟 2: 啟動容器
echo -e "${BLUE}步驟 2/4: 啟動容器...${NC}"
docker compose -f docker-compose.reviewer-cli.yml up -d

# 等待容器啟動
echo "等待容器啟動..."
sleep 5

# 步驟 3: 檢查容器狀態
echo -e "${BLUE}步驟 3/4: 檢查容器狀態...${NC}"
if docker compose -f docker-compose.reviewer-cli.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✅ 容器運行正常${NC}"
else
    echo -e "${RED}❌ 容器啟動失敗${NC}"
    docker compose -f docker-compose.reviewer-cli.yml logs
    exit 1
fi

# 步驟 4: 檢查 Claude CLI
echo -e "${BLUE}步驟 4/4: 檢查 Claude CLI...${NC}"
CLAUDE_VERSION=$(docker compose -f docker-compose.reviewer-cli.yml exec -T pr-reviewer-cli claude --version 2>&1 || echo "未安裝")

if [[ "$CLAUDE_VERSION" == *"Claude Code"* ]]; then
    echo -e "${GREEN}✅ Claude CLI 已安裝: $CLAUDE_VERSION${NC}"
else
    echo -e "${RED}❌ Claude CLI 安裝失敗${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}=========================================="
echo "✅ 設置完成！"
echo -e "==========================================${NC}"
echo ""
echo -e "${YELLOW}📝 下一步：認證 Claude CLI${NC}"
echo ""
echo "請執行以下命令進入容器並認證："
echo ""
echo -e "${GREEN}  docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli bash${NC}"
echo ""
echo "然後在容器內執行："
echo ""
echo -e "${GREEN}  claude auth login${NC}"
echo ""
echo "按照提示完成認證後，執行以下命令驗證："
echo ""
echo -e "${GREEN}  claude auth status${NC}"
echo -e "${GREEN}  claude chat --message 'Hello, test'${NC}"
echo ""
echo "認證完成後，輸入 ${GREEN}exit${NC} 退出容器"
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo "  - 認證配置會持久化保存在 Docker volume 中"
echo "  - 容器重啟後無需重新認證"
echo "  - 查看日誌: docker compose -f docker-compose.reviewer-cli.yml logs -f"
echo ""
