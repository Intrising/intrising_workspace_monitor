# 🚀 快速開始指南

5 分鐘內啟動你的 GitHub Monitor！

## 步驟 1: 準備環境

確保已安裝：
- Docker (>= 20.10)
- Docker Compose (>= 2.0)

```bash
# 檢查版本
docker --version
docker-compose --version
```

## 步驟 2: 獲取 GitHub Token

1. 登入 GitHub
2. 前往 Settings → Developer settings → Personal access tokens → Tokens (classic)
3. 點擊 "Generate new token (classic)"
4. 選擇權限：
   - ✅ `repo` (完整儲存庫訪問)
   - ✅ `read:org` (讀取組織資訊)
5. 複製生成的 token (格式: `ghp_xxxxxxxxxxxx`)

## 步驟 3: 設置 Slack Webhook（可選）

1. 前往 https://api.slack.com/apps
2. 創建新應用或選擇現有應用
3. 啟用 "Incoming Webhooks"
4. 添加新的 Webhook，選擇目標頻道
5. 複製 Webhook URL (格式: `https://hooks.slack.com/services/...`)

## 步驟 4: 配置應用

```bash
# 1. 初始化專案
make init

# 2. 編輯 .env 文件
vim .env
```

在 `.env` 中填入：
```bash
GITHUB_TOKEN=ghp_your_github_token_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#pr-alerts
```

```bash
# 3. 編輯監控配置
vim config.yaml
```

在 `config.yaml` 中設置要監控的儲存庫：
```yaml
monitor:
  repositories:
    - owner: "your-organization"
      repo: "your-repository"
      branches:
        - main
        - develop
```

## 步驟 5: 啟動服務

```bash
# 一鍵部署
make deploy

# 或者分步驟
make check    # 檢查配置
make build    # 建構映像
make start    # 啟動服務
```

## 步驟 6: 驗證運行

```bash
# 查看服務狀態
make status

# 查看實時日誌
make logs

# 執行健康檢查
make health
```

## 常用命令

```bash
make logs      # 查看日誌
make status    # 查看狀態
make restart   # 重啟服務
make stop      # 停止服務
make shell     # 進入容器
make help      # 查看所有命令
```

## 測試通知

服務啟動後，它會：
1. 每 5 分鐘檢查一次配置的儲存庫
2. 發現問題時發送 Slack 通知
3. 記錄所有活動到日誌

## 故障排查

### 容器無法啟動？

```bash
# 檢查配置
make check

# 查看錯誤日誌
docker-compose logs github-monitor
```

### 沒收到 Slack 通知？

```bash
# 測試 Webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from PR Monitor"}' \
  YOUR_SLACK_WEBHOOK_URL

# 檢查環境變數
docker exec github-monitor env | grep SLACK
```

### GitHub API 錯誤？

```bash
# 檢查 Token 配額
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# 確認 Token 權限
docker exec github-monitor env | grep GITHUB
```

## 下一步

- 📖 閱讀 [完整文檔](README.md)
- 🔧 查看 [部署指南](DEPLOYMENT.md)
- ⚙️ 調整 `config.yaml` 中的警報條件
- 📊 設置監控和告警

## 需要幫助？

- 查看日誌: `make logs`
- 查看狀態: `make status`
- 查看所有命令: `make help`

祝你使用愉快！ 🎉
