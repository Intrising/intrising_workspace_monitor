# Docker Compose 使用指南

所有 Docker Compose 配置已更新為從專案根目錄 `~/Documents/github/intrising_workspace_monitor` 啟動。

## 啟動方式

### 從專案根目錄啟動

```bash
cd ~/Documents/github/intrising_workspace_monitor

# 使用不同的配置檔案
docker compose -f docker/docker-compose.pr-reviewer.yml up -d
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.dev.yml up -d
docker compose -f docker/docker-compose.reviewer.yml up -d
docker compose -f docker/docker-compose.webhook-simple.yml up -d
docker compose -f docker/docker-compose.webhook-test.yml up -d
docker compose -f docker/docker-compose.reviewer-cli.yml up -d
```

## 配置檔案說明

| 檔案 | 用途 | 服務 |
|------|------|------|
| `docker/docker-compose.pr-reviewer.yml` | PR 審查服務（使用 Codex） | pr-reviewer |
| `docker/docker-compose.yml` | 基礎 GitHub 監控服務 | github-monitor |
| `docker/docker-compose.dev.yml` | 開發環境配置 | github-monitor-dev |
| `docker/docker-compose.prod.yml` | 生產環境配置（覆蓋） | github-monitor |
| `docker/docker-compose.reviewer.yml` | PR 審查服務（獨立版本） | pr-reviewer |
| `docker/docker-compose.webhook-simple.yml` | Webhook 測試接收器 | webhook-receiver |
| `docker/docker-compose.webhook-test.yml` | Webhook 測試服務 | webhook-test |
| `docker/docker-compose.reviewer-cli.yml` | PR 審查服務（使用 Claude CLI） | pr-reviewer-cli |

## 常用命令

### 啟動服務
```bash
cd ~/Documents/github/intrising_workspace_monitor
docker compose -f docker/docker-compose.pr-reviewer.yml up -d
```

### 查看日誌
```bash
docker compose -f docker/docker-compose.pr-reviewer.yml logs -f
```

### 停止服務
```bash
docker compose -f docker/docker-compose.pr-reviewer.yml down
```

### 重啟服務
```bash
docker compose -f docker/docker-compose.pr-reviewer.yml restart
```

### 重新構建並啟動
```bash
docker compose -f docker/docker-compose.pr-reviewer.yml up -d --build
```

## 組合使用

開發環境可以組合基礎配置和開發配置：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

生產環境可以組合基礎配置和生產配置：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

## 注意事項

1. **所有命令都必須在專案根目錄執行**：`~/Documents/github/intrising_workspace_monitor`
2. 配置檔案中的相對路徑已更新為相對於專案根目錄（使用 `..` 從 docker/ 目錄向上）
3. 環境變數檔案應放在 `.private/.env` 或根目錄的 `.env`
4. 日誌會儲存在各自的 volume 中
5. 某些服務需要外部 volume（如 `github_pr_monitor_pr-reviewer-logs`）

## 環境變數

確保你已經配置好以下環境變數檔案：

- `.private/.env` - PR reviewer 服務使用
- `.env` - 其他服務使用

必要的環境變數包括：
- `GITHUB_TOKEN` - GitHub Personal Access Token
- `WEBHOOK_PORT` - Webhook 端口（預設 8080）
- `SLACK_WEBHOOK_URL` - Slack 通知 URL（如果使用）

## 故障排查

如果遇到問題，可以：

1. 檢查日誌：
   ```bash
   docker compose -f docker/docker-compose.pr-reviewer.yml logs -f
   ```

2. 檢查容器狀態：
   ```bash
   docker ps -a
   ```

3. 進入容器檢查：
   ```bash
   docker exec -it pr-reviewer sh
   ```

4. 清理並重新啟動：
   ```bash
   docker compose -f docker/docker-compose.pr-reviewer.yml down
   docker compose -f docker/docker-compose.pr-reviewer.yml up -d --build
   ```
