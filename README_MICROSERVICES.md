# Workspace Monitor - 微服務架構

## 🎯 架構概覽

本專案採用微服務架構,將功能拆分為三個獨立服務:

```
                    GitHub Webhooks
                           ↓
                 ┌──────────────────┐
                 │ workspace-monitor│  Port 8080 (公開)
                 │  (API Gateway)   │
                 │                  │
                 │  功能:            │
                 │  • 接收 webhook   │
                 │  • 智能路由       │
                 │  • 統一 Dashboard │
                 │  • 數據聚合       │
                 └────┬────────┬─────┘
                      │        │
            ┌─────────┘        └─────────┐
            ↓                            ↓
    ┌──────────────┐            ┌──────────────┐
    │ pr-reviewer  │            │ issue-copier │
    │  Port 8081   │            │  Port 8082   │
    │  (內部服務)   │            │  (內部服務)   │
    │              │            │              │
    │ 功能:         │            │ 功能:         │
    │ • PR 審查     │            │ • Issue 複製  │
    │ • Codex AI   │            │ • 評論同步    │
    │ • 審查報告    │            │ • Label 路由  │
    └──────────────┘            └──────────────┘
```

## ✨ 主要優勢

### 1. **服務隔離** 🔒
- PR 審查和 Issue 複製獨立運行
- 一個服務故障不影響另一個
- 更容易除錯和維護

### 2. **獨立擴展** 📈
- 根據負載獨立調整每個服務的資源
- PR Reviewer 可以配置更多 CPU (AI 計算密集)
- Issue Copier 可以調整並發數

### 3. **統一管理** 🎛️
- **單一入口**: 所有請求通過 Gateway (Port 8080)
- **統一 Dashboard**: 一個頁面查看所有服務狀態
- **集中認證**: Gateway 統一處理用戶認證

### 4. **更好的監控** 📊
- 每個服務獨立的日誌和健康檢查
- Dashboard 實時顯示各服務狀態
- 便於追蹤問題和性能分析

## 🚀 快速開始

### 前置需求

- Docker & Docker Compose
- GitHub Personal Access Token
- 至少 2GB RAM

### 啟動服務

```bash
# 1. 進入專案目錄
cd intrising_workspace_monitor

# 2. 啟動所有服務
docker compose -f docker-compose.microservices.yml up -d

# 3. 查看服務狀態
docker compose -f docker-compose.microservices.yml ps

# 4. 查看日誌
docker compose -f docker-compose.microservices.yml logs -f
```

### 訪問服務

- **Dashboard**: http://localhost:8080
- **PR 審查**: http://localhost:8080/pr-tasks
- **Issue 複製**: http://localhost:8080/issue-copies

## 📡 API 端點

### Gateway (公開 - Port 8080)

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 統一 Dashboard |
| `/health` | GET | 健康檢查 |
| `/webhook` | POST | GitHub Webhook 入口 |
| `/api/dashboard` | GET | 聚合所有服務數據 |
| `/pr-tasks` | GET | PR 審查頁面 (代理) |
| `/issue-copies` | GET | Issue 複製頁面 (代理) |

### PR Reviewer (內部 - Port 8081)

| 端點 | 方法 | 說明 |
|------|------|------|
| `/health` | GET | 健康檢查 |
| `/webhook` | POST | 處理 PR 事件 |
| `/api/tasks` | GET | 獲取審查任務列表 |
| `/api/tasks/<id>` | GET | 獲取單個任務詳情 |

### Issue Copier (內部 - Port 8082)

| 端點 | 方法 | 說明 |
|------|------|------|
| `/health` | GET | 健康檢查 |
| `/webhook` | POST | 處理 Issue 事件 |
| `/api/issue-copies` | GET | 獲取複製記錄 |
| `/api/comment-syncs` | GET | 獲取評論同步記錄 |

## 🔧 配置

### 環境變數

```bash
# Gateway 配置
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8080
PR_REVIEWER_URL=http://pr-reviewer:8081
ISSUE_COPIER_URL=http://issue-copier:8082

# GitHub 配置
GITHUB_TOKEN=your_token_here
WEBHOOK_SECRET=your_secret_here

# Web UI 認證
WEB_USERNAME=admin
WEB_PASSWORD=your_password_here
```

## 📊 Dashboard 功能

### 實時監控
- ✅ 服務在線狀態
- 📈 任務統計數據
- 🔄 自動刷新 (每 5 秒)

### 數據展示
- **PR Reviewer**
  - 總任務數
  - 處理中任務
  - 已完成任務
  - 失敗任務

- **Issue Copier**
  - 總複製數
  - 成功複製
  - 失敗複製
  - 進行中複製

## 🔍 服務健康檢查

```bash
# 檢查所有服務
docker compose -f docker-compose.microservices.yml ps

# 檢查 Gateway
curl http://localhost:8080/health

# 檢查 PR Reviewer (通過 Gateway)
docker exec workspace-monitor curl http://pr-reviewer:8081/health

# 檢查 Issue Copier (通過 Gateway)
docker exec workspace-monitor curl http://issue-copier:8082/health
```

## 🛠️ 維護操作

### 重啟單個服務

```bash
# 重啟 Gateway
docker compose -f docker-compose.microservices.yml restart workspace-monitor

# 重啟 PR Reviewer
docker compose -f docker-compose.microservices.yml restart pr-reviewer

# 重啟 Issue Copier
docker compose -f docker-compose.microservices.yml restart issue-copier
```

### 查看日誌

```bash
# 所有服務
docker compose -f docker-compose.microservices.yml logs -f

# 單個服務
docker compose -f docker-compose.microservices.yml logs -f workspace-monitor
docker compose -f docker-compose.microservices.yml logs -f pr-reviewer
docker compose -f docker-compose.microservices.yml logs -f issue-copier
```

### 更新服務

```bash
# 1. 拉取最新代碼
git pull

# 2. 重新構建
docker compose -f docker-compose.microservices.yml build

# 3. 重啟服務
docker compose -f docker-compose.microservices.yml up -d
```

## 🔄 從單體架構遷移

如果你正在使用舊的單體架構 (`docker-compose.pr-reviewer.yml`),請參考 [遷移指南](MICROSERVICES_MIGRATION.md)。

### 快速遷移

```bash
# 1. 停止舊服務
docker compose -f docker-compose.pr-reviewer.yml down

# 2. 備份資料庫 (可選)
docker run --rm -v github_pr_monitor_pr-reviewer-db:/data -v $(pwd):/backup \
  busybox tar czf /backup/database-backup.tar.gz /data

# 3. 啟動新服務
docker compose -f docker-compose.microservices.yml up -d

# 4. 驗證
curl http://localhost:8080/health
```

## 📝 服務間通訊

所有服務在同一個 Docker network (`workspace-network`) 中:

- Gateway → PR Reviewer: `http://pr-reviewer:8081`
- Gateway → Issue Copier: `http://issue-copier:8082`
- 使用 HTTP REST API 通訊
- 支持健康檢查和自動重試

## 🔒 安全性

### 網路隔離
- **只有 Gateway 暴露公開端口** (8080)
- PR Reviewer 和 Issue Copier 只在內部網路可訪問
- 降低攻擊面

### 認證
- Gateway 統一處理 HTTP Basic Auth
- 內部服務間通訊不需要認證 (在同一網路)

### Webhook 驗證
- Gateway 驗證 GitHub webhook 簽名
- 只有驗證通過的請求才會路由到內部服務

## 📚 更多資源

- [完整遷移指南](MICROSERVICES_MIGRATION.md)
- [Issue Copier 文檔](docs/ISSUE_COPIER.md)
- [PR Reviewer 文檔](docs/migration/README_REVIEWER.md)
- [故障排查](docs/TROUBLESHOOTING.md)

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License
