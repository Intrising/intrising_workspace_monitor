# GitHub Webhook 配置指南

Webhook 接收服務已成功啟動並測試完成！現在您可以在 GitHub 倉庫中配置 webhook。

## ✅ 當前狀態

- **服務狀態**: ✅ 運行中 (健康)
- **監聽地址**: `0.0.0.0:8080`
- **Webhook Secret**: `ji3vu;3xk4` (已從 .env 載入)
- **簽名驗證**: ✅ 已啟用並測試通過
- **測試結果**: ✅ Ping 和 Pull Request 事件均正常接收

## 📝 在 GitHub 配置 Webhook

### 步驟 1: 進入倉庫設置

1. 前往您的 GitHub 倉庫
2. 點擊 **Settings** (設置)
3. 在左側菜單中選擇 **Webhooks**
4. 點擊 **Add webhook** (添加 webhook)

### 步驟 2: 配置 Webhook

填入以下信息：

#### Payload URL
```
http://YOUR_SERVER_IP:8080/webhook
```

**重要**:
- 將 `YOUR_SERVER_IP` 替換為您服務器的實際 IP 地址或域名
- 如果在本地測試，可以使用 `ngrok` 或其他隧道工具
- 端口必須是 `8080`（與 .env 中的 WEBHOOK_PORT 一致）

#### Content type
選擇：
```
application/json
```

#### Secret
填入：
```
ji3vu;3xk4
```

**注意**: 這必須與 `.env` 文件中的 `WEBHOOK_SECRET` 完全一致！

#### SSL verification
建議選擇：
```
Enable SSL verification
```

如果使用自簽名證書或測試環境，可以選擇 "Disable"。

#### Which events would you like to trigger this webhook?

選擇：
```
Let me select individual events
```

然後勾選：
- ✅ **Pull requests** (必須)

可選的其他事件：
- [ ] Pull request reviews
- [ ] Pull request review comments
- [ ] Issues

#### Active

確保勾選：
```
☑ Active
```

### 步驟 3: 保存並測試

1. 點擊 **Add webhook** (綠色按鈕)
2. GitHub 會自動發送一個 `ping` 事件來測試連接
3. 查看 webhook 頁面底部的 "Recent Deliveries"
4. 應該看到一個 ✅ 綠色勾勾，表示 ping 成功

## 🔍 驗證 Webhook 是否正常工作

### 方法 1: 查看 GitHub Webhook 狀態

1. 在 GitHub webhook 設置頁面
2. 點擊剛創建的 webhook
3. 滾動到 "Recent Deliveries" 部分
4. 應該看到：
   - ✅ 綠色勾勾（成功）
   - Response code: `200`
   - Response body: `{"status":"success","event":"ping",...}`

### 方法 2: 查看服務器日誌

運行以下命令查看接收到的 webhook：

```bash
docker compose -f docker-compose.webhook-simple.yml logs -f webhook-receiver
```

您應該看到類似以下的輸出：

```
================================================================================
📨 收到 GitHub Webhook!
================================================================================
⏰ 時間: 2025-10-15 14:28:57
📦 Delivery ID: 12345678-1234-1234-1234-123456789abc
🏷️  事件類型: ping
🔐 簽名: sha256=3eb4370e876a5...
✅ 簽名驗證通過

📋 事件詳情:
--------------------------------------------------------------------------------
💬 Ping 消息: GitHub webhook is working!
🏢 倉庫: your-org/your-repo
================================================================================
✅ Webhook 處理成功
```

### 方法 3: 創建測試 PR

創建一個測試 Pull Request 來驗證完整流程：

```bash
# 在您的倉庫中
git checkout -b test-webhook-$(date +%s)
echo "# Test Webhook" > test-webhook.md
git add test-webhook.md
git commit -m "test: webhook integration"
git push origin HEAD

# 在 GitHub 上創建 PR
```

然後：
1. 查看服務器日誌，應該看到 `pull_request` 事件
2. 在 GitHub webhook 設置中，"Recent Deliveries" 應該有新的條目

## 🔧 故障排查

### 問題 1: GitHub 顯示連接失敗

**症狀**: GitHub webhook 狀態顯示紅色 ❌

**可能原因**:
- 服務器防火墻阻止了端口 8080
- 服務器 IP 地址填寫錯誤
- 服務未運行

**解決方案**:

```bash
# 1. 檢查服務是否運行
docker compose -f docker-compose.webhook-simple.yml ps

# 2. 測試本地連接
curl http://localhost:8080/health

# 3. 開放防火墻端口 (Ubuntu/Debian)
sudo ufw allow 8080/tcp

# 4. 開放防火墻端口 (CentOS/RHEL)
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload

# 5. 從外部測試連接
curl http://YOUR_SERVER_IP:8080/health
```

### 問題 2: 簽名驗證失敗

**症狀**: 服務器日誌顯示 "❌ 簽名驗證失敗!"

**原因**: GitHub webhook secret 與 .env 中的 WEBHOOK_SECRET 不一致

**解決方案**:

```bash
# 1. 檢查 .env 文件
cat .env | grep WEBHOOK_SECRET

# 2. 確認值為: ji3vu;3xk4

# 3. 如果修改了 .env，重啟服務
docker compose -f docker-compose.webhook-simple.yml restart

# 4. 在 GitHub webhook 設置中更新 Secret
```

### 問題 3: 使用本地開發環境

**問題**: GitHub 無法訪問 localhost 或內網 IP

**解決方案**: 使用 ngrok 創建公網隧道

```bash
# 1. 安裝 ngrok
# 下載: https://ngrok.com/download

# 2. 啟動隧道
ngrok http 8080

# 3. 使用 ngrok 提供的 URL
# 例如: https://abc123.ngrok.io/webhook
```

## 📊 監控和日誌

### 實時查看日誌

```bash
docker compose -f docker-compose.webhook-simple.yml logs -f webhook-receiver
```

### 查看最近 50 條日誌

```bash
docker compose -f docker-compose.webhook-simple.yml logs --tail 50 webhook-receiver
```

### 停止服務

```bash
docker compose -f docker-compose.webhook-simple.yml down
```

### 重啟服務

```bash
docker compose -f docker-compose.webhook-simple.yml restart
```

## 🚀 下一步

一旦 webhook 配置成功並能接收 GitHub 事件，下一步是：

1. **實現 PR 自動審查功能**
   - 目前只是接收 webhook 並記錄
   - 需要集成 Claude Code CLI 來實際審查 PR

2. **配置郵件通知**
   - msmtp 已經配置完成
   - 需要確保能發送郵件到 khkh@intrising.com.tw

3. **測試完整流程**
   - 創建真實的 PR
   - 驗證自動審查是否觸發
   - 確認郵件通知發送成功

## ⚠️ 重要提醒

目前運行的是 **測試服務器** (`test_webhook.py`)，它只會：
- ✅ 接收和驗證 webhook
- ✅ 顯示事件信息
- ❌ **不會**實際審查 PR

要啟用 PR 自動審查功能，需要：
1. 解決 Claude Code CLI 的安裝問題
2. 使用 `pr_reviewer.py` 替代 `test_webhook.py`
3. 確保 GITHUB_TOKEN 配置正確

---

**配置完成！🎉**

如有任何問題，請查看：
- `WEBHOOK_TEST.md` - 測試指南
- `README.md` - 項目總覽
- 服務器日誌 - 詳細錯誤信息
