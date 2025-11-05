# Claude CLI 在 Docker 中的認證設置指南

本指南說明如何在 Docker 容器內認證 Claude Code CLI，以便用於 PR 自動審查。

## 🎯 方案概述

使用 Docker volume 持久化 Claude 認證配置，這樣您只需要認證一次，之後容器重啟仍然保持登錄狀態。

## 📋 前置要求

- Docker 和 Docker Compose 已安裝
- Claude Code 帳號（在 https://claude.ai 註冊）
- `.env` 文件已配置好 GITHUB_TOKEN 和 WEBHOOK_SECRET

## 🚀 步驟 1: 構建並啟動容器

```bash
# 構建 Docker 映像（包含 Claude CLI）
docker compose -f docker-compose.reviewer-cli.yml build

# 啟動容器
docker compose -f docker-compose.reviewer-cli.yml up -d
```

## 🔐 步驟 2: 在容器內認證 Claude

### 方法 A: 互動式認證（推薦）

```bash
# 進入容器
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli bash

# 在容器內執行 Claude 認證
claude auth login

# 按照提示操作：
# 1. 會顯示一個 URL 和驗證碼
# 2. 在瀏覽器中打開該 URL
# 3. 登錄您的 Claude 帳號
# 4. 輸入顯示的驗證碼
# 5. 完成認證

# 驗證認證狀態
claude auth status

# 測試 Claude CLI
claude chat --message "Hello, are you working?"

# 退出容器
exit
```

### 方法 B: 使用認證 Token

如果您已經在主機上認證過 Claude：

```bash
# 在主機上獲取認證配置
cat ~/.config/claude/auth.json

# 複製認證配置到容器
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli bash -c \
  'mkdir -p ~/.config/claude && cat > ~/.config/claude/auth.json' < ~/.config/claude/auth.json
```

## ✅ 步驟 3: 驗證設置

### 測試 Claude CLI

```bash
# 在容器內測試
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli bash -c \
  "claude chat --non-interactive --message 'Hello, this is a test'"
```

如果返回 Claude 的回覆，表示認證成功！

### 測試 Webhook 服務

```bash
# 檢查容器狀態
docker compose -f docker-compose.reviewer-cli.yml ps

# 查看日誌
docker compose -f docker-compose.reviewer-cli.yml logs -f pr-reviewer-cli

# 測試健康檢查
curl http://localhost:8080/health
```

## 📝 步驟 4: 測試 PR 審查

### 方法 1: 使用測試腳本

```bash
# 發送模擬的 PR webhook
./test_webhook_simple.sh http://localhost:8080/webhook/
```

### 方法 2: 創建真實的 PR

1. 在您的 GitHub 倉庫創建一個測試分支
2. 提交一些變更
3. 創建 Pull Request
4. 查看容器日誌，應該看到 Claude 開始審查

```bash
# 實時查看日誌
docker compose -f docker-compose.reviewer-cli.yml logs -f pr-reviewer-cli
```

## 🔍 故障排查

### 問題 1: Claude 認證失敗

**症狀**: `claude auth login` 無法完成

**解決方案**:
```bash
# 確保容器有網絡連接
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli curl -I https://api.anthropic.com

# 檢查 Claude CLI 版本
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli claude --version

# 清除舊的認證並重試
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli rm -rf ~/.config/claude
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli claude auth login
```

### 問題 2: 認證後容器重啟失效

**原因**: Volume 掛載問題

**解決方案**:
```bash
# 檢查 volume
docker volume ls | grep claude

# 檢查 volume 內容
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli ls -la ~/.config/claude/

# 如果空的，重新認證
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli claude auth login
```

### 問題 3: PR 審查沒有觸發

**檢查清單**:

```bash
# 1. 檢查容器是否運行
docker compose -f docker-compose.reviewer-cli.yml ps

# 2. 檢查環境變數
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli printenv | grep -E 'GITHUB_TOKEN|WEBHOOK_SECRET|CLAUDE'

# 3. 檢查 Claude 認證
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli claude auth status

# 4. 查看詳細日誌
docker compose -f docker-compose.reviewer-cli.yml logs --tail 100 pr-reviewer-cli

# 5. 手動測試 webhook
curl -X POST http://localhost:8080/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d '{"action":"opened","number":1,"pull_request":{"number":1}}'
```

### 問題 4: Claude CLI 執行超時

**原因**: Claude CLI 首次執行可能需要較長時間

**解決方案**:
在 `pr_reviewer.py` 中增加超時時間：

```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=600,  # 增加到 10 分鐘
    encoding='utf-8'
)
```

## 🔄 日常操作

### 停止服務

```bash
docker compose -f docker-compose.reviewer-cli.yml down
```

### 重啟服務

```bash
docker compose -f docker-compose.reviewer-cli.yml restart
```

### 查看日誌

```bash
# 實時日誌
docker compose -f docker-compose.reviewer-cli.yml logs -f

# 最近 100 行
docker compose -f docker-compose.reviewer-cli.yml logs --tail 100
```

### 更新代碼

```bash
# 重建映像
docker compose -f docker-compose.reviewer-cli.yml build --no-cache

# 重啟容器
docker compose -f docker-compose.reviewer-cli.yml up -d
```

## 🎯 持久化認證配置

認證配置保存在 Docker volume `claude-config` 中，即使容器被刪除，認證狀態也會保留。

### 備份認證配置

```bash
# 匯出認證配置
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli \
  cat ~/.config/claude/auth.json > claude-auth-backup.json

# 保存到安全位置
chmod 600 claude-auth-backup.json
```

### 恢復認證配置

```bash
# 從備份恢復
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli bash -c \
  'mkdir -p ~/.config/claude && cat > ~/.config/claude/auth.json' < claude-auth-backup.json
```

## 📊 監控和調試

### 監控 PR 審查活動

```bash
# 持續監控日誌，過濾 PR 相關信息
docker compose -f docker-compose.reviewer-cli.yml logs -f pr-reviewer-cli | grep -E 'PR|Claude|審查'
```

### 進入容器調試

```bash
# 進入容器 shell
docker compose -f docker-compose.reviewer-cli.yml exec pr-reviewer-cli bash

# 在容器內可以執行：
# - claude chat --message "test"
# - python3 -c "import github; print('GitHub OK')"
# - curl http://localhost:8080/health
# - cat /app/pr_reviewer.py
# - env | grep GITHUB
```

## ⚠️ 安全注意事項

1. **不要提交認證配置到 Git**
   - `claude-auth-backup.json` 已加入 `.gitignore`
   - 認證配置包含敏感 token

2. **保護 Volume 數據**
   ```bash
   # 定期備份 volume
   docker run --rm \
     -v github_monitor_claude-config:/source \
     -v $(pwd):/backup \
     alpine tar czf /backup/claude-config-backup.tar.gz -C /source .
   ```

3. **限制容器權限**
   - 容器已使用非 root 用戶 (appuser)
   - 只掛載必要的 volume

## 📚 相關文檔

- [Claude Code CLI 官方文檔](https://docs.claude.com/en/docs/claude-code)
- [GitHub Webhook 配置](./GITHUB_WEBHOOK_CONFIG.md)
- [Webhook 測試指南](./WEBHOOK_TEST.md)
- [PR Reviewer 概述](./README_REVIEWER.md)

---

**設置完成後，您的 PR 自動審查系統就可以正常工作了！🎉**
