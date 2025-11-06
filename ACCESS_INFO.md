# 🔐 訪問資訊

## Dashboard 訪問

**URL**: http://localhost:8080

**認證資訊**:
- 用戶名: `admin`
- 密碼: `intrising2024`

## 📊 功能頁面

登入後可以訪問：

1. **Dashboard** - http://localhost:8080/
   - 統一監控所有服務
   - 實時數據刷新
   - 服務健康狀態

2. **PR 審查** - http://localhost:8080/pr-tasks
   - PR 審查任務列表
   - 任務詳情查看

3. **Issue 複製** - http://localhost:8080/issue-copies
   - Issue 複製記錄
   - 評論同步記錄

## 🔍 API 端點

### Gateway (需要認證)

```bash
# Dashboard 數據
curl -u admin:intrising2024 http://localhost:8080/api/dashboard

# 健康檢查 (不需要認證)
curl http://localhost:8080/health
```

### 內部服務 (通過 Docker 訪問)

```bash
# PR Reviewer
docker exec workspace-monitor curl http://pr-reviewer:8081/health
docker exec workspace-monitor curl http://pr-reviewer:8081/api/tasks

# Issue Copier
docker exec workspace-monitor curl http://issue-copier:8082/health
docker exec workspace-monitor curl http://issue-copier:8082/api/issue-copies
```

## 🌐 瀏覽器訪問

1. 開啟瀏覽器
2. 訪問 http://localhost:8080
3. 輸入用戶名: `admin`
4. 輸入密碼: `intrising2024`
5. 享受統一 Dashboard！

## 🔒 安全提示

- 密碼存儲在 `.private/.env` 文件中
- 可通過修改 `WEB_PASSWORD` 環境變數更改密碼
- 建議在生產環境使用更強的密碼

## 📝 修改密碼

1. 編輯 `.private/.env`:
   ```bash
   WEB_PASSWORD=your_new_password
   ```

2. 重啟 Gateway:
   ```bash
   docker compose -f docker-compose.microservices.yml restart workspace-monitor
   ```

## ✅ 驗證服務

所有服務都應該是 healthy 狀態：

```bash
docker compose -f docker-compose.microservices.yml ps
```

預期輸出：
```
NAME                STATUS
workspace-monitor   Up (healthy)
pr-reviewer         Up (healthy)
issue-copier        Up (healthy)
```
