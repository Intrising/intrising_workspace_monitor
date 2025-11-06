# 微服務架構遷移指南

## 架構概覽

```
GitHub Webhooks
       ↓
┌──────────────────┐
│ workspace-monitor│ :8080 (公開)
│  (API Gateway)   │
│  - 接收 webhook  │
│  - 統一 Web UI   │
│  - 路由分發      │
└────┬────────┬────┘
     │        │
     ↓        ↓
┌────────┐ ┌──────────┐
│pr-review│ │issue-copy│
│  :8081  │ │  :8082   │
│(內部)   │ │ (內部)   │
└─────────┘ └──────────┘
```

## 遷移步驟

### 階段 1: 準備工作 (已完成)

- ✅ 設計微服務架構
- ✅ 創建 Gateway 服務 (`src/gateway.py`)
- ✅ 創建 docker-compose 配置

### 階段 2: 拆分服務 (待完成)

需要創建以下文件:

#### 1. PR Reviewer 服務
```bash
# src/pr_reviewer_service.py
```
- 從 `pr_reviewer.py` 拆分出 PR 審查邏輯
- 提供 HTTP API 接收 webhook
- 暴露任務查詢 API

#### 2. Issue Copier 服務
```bash
# src/issue_copier_service.py
```
- 從 `pr_reviewer.py` 拆分出 Issue 複製邏輯
- 提供 HTTP API 接收 webhook
- 暴露複製記錄查詢 API

#### 3. Dockerfile
```bash
# docker/Dockerfile.pr-reviewer
# docker/Dockerfile.issue-copier
```

### 階段 3: 部署遷移

#### 停止舊服務
```bash
docker stop workspace-monitor
docker rm workspace-monitor
```

#### 啟動新服務
```bash
docker compose -f docker-compose.microservices.yml up -d
```

## 優勢

### 1. 服務隔離
- PR 審查和 Issue 複製獨立運行
- 一個服務故障不影響另一個

### 2. 獨立擴展
- 可以單獨擴展 PR Reviewer (如需要更多 AI 資源)
- Issue Copier 可以獨立調整並發數

### 3. 更好的監控
- 每個服務獨立的 logs 和 metrics
- 統一的 Dashboard 聚合顯示

### 4. 簡化維護
- 各服務可以獨立更新部署
- 降低代碼耦合度

## API 端點設計

### Gateway (Port 8080)

**公開端點:**
- `GET /` - 統一 Dashboard
- `GET /health` - 健康檢查
- `POST /webhook` - GitHub Webhook (路由到各服務)
- `GET /api/dashboard` - 聚合數據
- `GET /pr-tasks` - PR 審查頁面(代理)
- `GET /issue-copies` - Issue 複製頁面(代理)

### PR Reviewer (Port 8081 - 內部)

**內部端點:**
- `GET /health` - 健康檢查
- `POST /webhook` - 接收 PR webhook
- `GET /api/tasks` - 獲取任務列表
- `GET /api/tasks/<id>` - 獲取單個任務

### Issue Copier (Port 8082 - 內部)

**內部端點:**
- `GET /health` - 健康檢查
- `POST /webhook` - 接收 Issue webhook
- `GET /api/issue-copies` - 獲取複製記錄
- `GET /api/comment-syncs` - 獲取評論同步記錄

## 配置變更

### 環境變數

**新增 Gateway 變數:**
```bash
# Gateway 配置
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8080
PR_REVIEWER_URL=http://pr-reviewer:8081
ISSUE_COPIER_URL=http://issue-copier:8082
```

**保留現有變數:**
- `GITHUB_TOKEN`
- `WEBHOOK_SECRET`
- `WEB_USERNAME`
- `WEB_PASSWORD`
- 等等...

## 數據共享

### 共享資料庫
- PR Reviewer 使用: `/var/lib/github-monitor/tasks.db`
- Issue Copier 使用: `/var/lib/github-monitor/tasks.db` (同一個)
- 通過 volume 共享

### 或獨立資料庫 (建議)
- PR Reviewer: `/var/lib/github-monitor/pr_tasks.db`
- Issue Copier: `/var/lib/github-monitor/issue_tasks.db`

## 測試計劃

### 1. 單元測試
```bash
# 測試 Gateway 路由
pytest tests/test_gateway.py

# 測試 PR Reviewer 服務
pytest tests/test_pr_reviewer_service.py

# 測試 Issue Copier 服務
pytest tests/test_issue_copier_service.py
```

### 2. 整合測試
```bash
# 啟動所有服務
docker compose -f docker-compose.microservices.yml up -d

# 測試 webhook 路由
./scripts/test_webhook_routing.sh

# 測試 Web UI
curl http://localhost:8080/
```

### 3. 性能測試
- 併發 webhook 處理
- Gateway 路由延遲
- 服務間通訊開銷

## 回滾計劃

如果遷移出現問題:

```bash
# 停止新服務
docker compose -f docker-compose.microservices.yml down

# 啟動舊服務
docker compose -f docker-compose.pr-reviewer.yml up -d
```

## 下一步

1. **完成服務拆分代碼** (估計 2-3 小時)
2. **創建 Dockerfiles** (30 分鐘)
3. **本地測試** (1 小時)
4. **生產部署** (30 分鐘)
5. **監控和調整** (持續)

## 注意事項

### 1. Webhook 配置
- GitHub webhook URL 保持不變: `https://your-server.com/webhook`
- Gateway 會自動路由到正確的服務

### 2. 數據遷移
- 現有資料庫可以直接使用
- 建議遷移前先備份

### 3. 資源分配
- 總記憶體需求會增加 (3 個容器)
- 建議至少 2GB RAM

### 4. 網路配置
- 所有服務在同一個 Docker network
- 只有 Gateway 暴露公開端口

## 完成時間表

- **今天**: 創建架構設計和 Gateway ✅
- **明天**: 完成服務拆分和測試
- **後天**: 生產環境部署
