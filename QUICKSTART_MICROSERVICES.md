# 🚀 微服務架構快速開始

## ✅ 部署完成！

你的 Workspace Monitor 已成功遷移到微服務架構！

### 📊 服務架構

```
                    GitHub Webhooks
                           ↓
         ┌─────────────────────────────┐
         │  workspace-monitor (8080)   │ ← 唯一對外端口
         │  (API Gateway)              │
         └──────┬──────────────┬───────┘
                │              │
       ┌────────▼─────┐  ┌────▼─────────┐
       │ pr-reviewer  │  │issue-copier  │
       │   (8081)     │  │   (8082)     │
       │   內部服務    │  │   內部服務    │
       └──────────────┘  └──────────────┘
```

## 🌐 訪問服務

### Dashboard (統一入口)
```
http://localhost:8080
```
用戶名: `admin` (根據你的 WEB_USERNAME 設置)
密碼: (根據你的 WEB_PASSWORD 設置)

### 各功能頁面
- **PR 審查**: http://localhost:8080/pr-tasks
- **Issue 複製**: http://localhost:8080/issue-copies

## 🔍 服務管理

### 查看所有服務狀態
```bash
docker compose -f docker-compose.microservices.yml ps
```

### 查看服務日誌
```bash
# 所有服務
docker compose -f docker-compose.microservices.yml logs -f

# 單個服務
docker compose -f docker-compose.microservices.yml logs -f workspace-monitor
docker compose -f docker-compose.microservices.yml logs -f pr-reviewer
docker compose -f docker-compose.microservices.yml logs -f issue-copier
```

### 重啟服務
```bash
# 重啟所有服務
docker compose -f docker-compose.microservices.yml restart

# 重啟單個服務
docker compose -f docker-compose.microservices.yml restart workspace-monitor
docker compose -f docker-compose.microservices.yml restart pr-reviewer
docker compose -f docker-compose.microservices.yml restart issue-copier
```

### 停止服務
```bash
docker compose -f docker-compose.microservices.yml down
```

### 更新服務
```bash
# 1. 拉取代碼
git pull

# 2. 重新構建
docker compose -f docker-compose.microservices.yml build

# 3. 重啟
docker compose -f docker-compose.microservices.yml up -d
```

## 🔧 健康檢查

### 測試所有服務
```bash
# Gateway
curl http://localhost:8080/health

# PR Reviewer (通過 Gateway 內部訪問)
docker exec workspace-monitor curl http://pr-reviewer:8081/health

# Issue Copier (通過 Gateway 內部訪問)
docker exec workspace-monitor curl http://issue-copier:8082/health
```

## 📡 GitHub Webhook 配置

### Webhook URL (不需要更改)
```
https://your-server.com/webhook
```

Gateway 會自動路由 webhook 到正確的服務:
- `pull_request` 事件 → `pr-reviewer`
- `issues` 事件 → `issue-copier`
- `issue_comment` 事件 → `issue-copier`

## 🎯 Dashboard 功能

訪問 http://localhost:8080 可以看到:

### 實時數據
- ✅ PR Reviewer 服務狀態
- ✅ Issue Copier 服務狀態
- 📊 任務統計 (總數、處理中、完成、失敗)
- 🔄 自動刷新 (每 5 秒)

### 快速導航
- 點擊 "查看詳情" 可以跳轉到各服務的詳細頁面

## 🔒 安全特性

### 網路隔離
- ✅ 只有 Gateway 暴露公開端口 8080
- ✅ PR Reviewer 和 Issue Copier 只在內部網路訪問
- ✅ 降低攻擊面

### 認證
- ✅ Gateway 統一 HTTP Basic Auth
- ✅ 內部服務間不需要認證

## 📊 服務詳情

### workspace-monitor (Gateway)
- **端口**: 8080 (公開)
- **功能**:
  - 接收 GitHub webhooks
  - 智能路由到對應服務
  - 統一 Web Dashboard
  - 數據聚合展示

### pr-reviewer
- **端口**: 8081 (內部)
- **功能**:
  - 處理 Pull Request 審查
  - Codex AI 集成
  - 生成審查報告

### issue-copier
- **端口**: 8082 (內部)
- **功能**:
  - 自動複製 Issues
  - 評論同步
  - Issue 引用轉換

## 🗂️ 數據持久化

每個服務都有獨立的 volume:

```bash
# 查看 volumes
docker volume ls | grep intrising_workspace_monitor

# 備份數據庫
docker run --rm \
  -v github_pr_monitor_pr-reviewer-db:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/pr-db-backup.tar.gz /data

docker run --rm \
  -v intrising_workspace_monitor_issue-copier-db:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/issue-db-backup.tar.gz /data
```

## 🐛 故障排查

### 服務無法啟動
```bash
# 查看日誌
docker compose -f docker-compose.microservices.yml logs workspace-monitor
docker compose -f docker-compose.microservices.yml logs pr-reviewer
docker compose -f docker-compose.microservices.yml logs issue-copier
```

### Dashboard 無法訪問
1. 檢查 Gateway 是否運行: `docker ps | grep workspace-monitor`
2. 檢查端口: `curl http://localhost:8080/health`
3. 檢查日誌: `docker logs workspace-monitor`

### Webhook 不工作
1. 檢查 Gateway 日誌: `docker logs workspace-monitor -f`
2. 測試 webhook: `curl -X POST http://localhost:8080/webhook`
3. 檢查服務間通訊: `docker exec workspace-monitor curl http://pr-reviewer:8081/health`

### 服務健康檢查失敗
```bash
# 重啟不健康的服務
docker compose -f docker-compose.microservices.yml restart pr-reviewer

# 如果持續失敗,重建
docker compose -f docker-compose.microservices.yml build pr-reviewer
docker compose -f docker-compose.microservices.yml up -d pr-reviewer
```

## 📈 性能監控

### 資源使用
```bash
docker stats workspace-monitor pr-reviewer issue-copier
```

### 容器狀態
```bash
docker compose -f docker-compose.microservices.yml ps
```

## 🎉 完成！

你的微服務架構已經運行！主要優勢:

1. ✅ **服務隔離**: 各服務獨立運行
2. ✅ **獨立擴展**: 可單獨調整資源
3. ✅ **統一管理**: 一個 Dashboard 管理所有服務
4. ✅ **更好監控**: 實時查看所有服務狀態

## 📚 更多文檔

- [詳細使用說明](README_MICROSERVICES.md)
- [遷移指南](MICROSERVICES_MIGRATION.md)
- [Issue Copier 文檔](docs/ISSUE_COPIER.md)

## 💡 提示

- Dashboard 會自動刷新,保持頁面開啟即可實時監控
- 所有 GitHub webhook 仍然發送到同一個 URL
- 可以單獨更新某個服務而不影響其他服務

祝使用愉快！ 🚀
