# Issue Auto-Copier 使用說明

## 功能概述

Issue Auto-Copier 是一個自動化工具，用於監聽特定 repository 的 issues，並根據 label 自動複製到對應的目標 repositories。

## 主要功能

1. **自動監聽 Issues**
   - 監聽來源 repository（如 `Intrising/test-Lantech`）的 issue 事件
   - 支援 `opened` 和 `labeled` 觸發事件

2. **Label 路由**
   - 根據 issue 的 labels 決定複製到哪些 repositories
   - 支援一個 issue 複製到多個 repositories
   - 可自訂 label 到 repository 的映射規則

3. **Issue 引用處理** ⭐ 新功能
   - 自動轉換 issue 引用格式：`#1409` → `Intrising/test-Lantech#1409`
   - 確保在目標 repository 中能正確連結回原始 issue
   - 智能識別，不會誤轉換 URL 中的 anchor（如 `http://example.com#section`）
   - 同時支援 issue body 和評論內容的轉換

4. **圖片處理**
   - 自動下載原 issue 中的圖片
   - 重新上傳到目標 repository
   - 支援 Markdown 和 HTML 格式的圖片

5. **完整複製**
   - 複製 issue 標題和內容
   - 保留所有 labels（可配置）
   - 添加來源引用（可配置）
   - 在原 issue 添加複製通知（可配置）

6. **評論同步**
   - 自動同步來源 issue 的新評論到所有已複製的目標 issues
   - 保留原作者資訊和評論連結
   - 同樣支援 issue 引用轉換

## 配置說明

在 `config.yaml` 中配置：

```yaml
issue_copy:
  # 是否啟用 issue 自動複製功能
  enabled: true

  # 來源 repository（監控這個 repo 的 issues）
  source_repo: "Intrising/test-Lantech"

  # 觸發複製的 issue 動作
  triggers:
    - opened       # Issue 被創建
    - labeled      # Issue 被添加標籤

  # Label 到目標 repository 的映射規則
  label_to_repo:
    "OS3": "Intrising/QA-Switch-OS3OS4"
    "OS4": "Intrising/QA-Switch-OS3OS4"
    "OS5": "Intrising/QA-Switch-OS5"
    "OS2": "Intrising/QA-Switch-OS2"
    "test": "Intrising/test-switch"

  # 是否在新 issue 中標註來源
  add_source_reference: true

  # 是否保留原 issue 的所有 labels
  copy_labels: true

  # 是否下載並重新上傳圖片
  reupload_images: true

  # 是否在原 issue 添加評論（說明已複製到哪裡）
  add_copy_comment: true
```

## GitHub Webhook 設置

### 1. 在來源 repository 設置 webhook

前往 `https://github.com/Intrising/test-Lantech/settings/hooks`

### 2. 添加新的 webhook

- **Payload URL**: `https://your-server.com/webhook`
- **Content type**: `application/json`
- **Secret**: 設置與 `WEBHOOK_SECRET` 環境變數相同的值
- **SSL verification**: 啟用（推薦）

### 3. 選擇觸發事件

只選擇：
- ✅ Issues

取消勾選其他事件（或保留 Pull requests 如果需要 PR 審查功能）

### 4. 啟用 webhook

點擊 "Add webhook" 完成設置

## 使用範例

### 場景 1: 創建帶有 OS3 label 的 issue

1. 在 `Intrising/test-Lantech` 創建新 issue
2. 添加 label: `OS3`
3. 系統自動複製到 `Intrising/QA-Switch-OS3OS4`
4. 圖片自動重新上傳
5. 在原 issue 添加複製通知評論

### 場景 2: 創建帶有多個 labels 的 issue

1. 在 `Intrising/test-Lantech` 創建新 issue
2. 添加 labels: `OS3`, `OS5`, `bug`
3. 系統自動複製到：
   - `Intrising/QA-Switch-OS3OS4`（因為 OS3 label）
   - `Intrising/QA-Switch-OS5`（因為 OS5 label）
4. 所有 labels（`OS3`, `OS5`, `bug`）都會被保留到新 issues

### 場景 3: 後續添加 label

1. 已存在的 issue（沒有匹配的 labels）
2. 添加 label: `OS2`
3. 系統自動複製到 `Intrising/QA-Switch-OS2`

### 場景 4: Issue 引用自動轉換

**原始 Issue 內容** (在 `Intrising/test-Lantech#1428`)：
```markdown
這個問題與 #1409 有關，也可能與 #1234 相關。
參考 Intrising/QA-Viewer#100 的解決方案。
```

**複製到目標 repo 後的內容**：
```markdown
這個問題與 Intrising/test-Lantech#1409 有關，也可能與 Intrising/test-Lantech#1234 相關。
參考 Intrising/QA-Viewer#100 的解決方案。
```

**轉換規則**：
- ✅ `#1409` → `Intrising/test-Lantech#1409`（轉換簡短引用）
- ✅ `Intrising/QA-Viewer#100` → `Intrising/QA-Viewer#100`（保留完整引用）
- ✅ `http://example.com#section` → `http://example.com#section`（不轉換 URL anchor）

## 測試

### 1. 啟動服務

```bash
# 開發環境
python src/pr_reviewer.py

# 或使用 Docker
docker-compose -f docker/docker-compose.pr-reviewer.yml up
```

### 2. 運行測試腳本

```bash
# 測試 issue 複製功能
python scripts/test_issue_copier.py
```

### 3. 手動測試

在 `Intrising/test-Lantech` 創建一個測試 issue：

- **標題**: 測試 Issue 自動複製
- **內容**: 包含一些文字和圖片
- **Labels**: 添加 `OS3` 或其他配置的 labels

然後檢查：
1. 目標 repository 是否創建了新 issue
2. 圖片是否正確顯示
3. Labels 是否保留
4. 原 issue 是否有複製通知評論

## 圖片處理說明

### 支援的圖片格式

- Markdown: `![alt text](image_url)`
- HTML: `<img src="image_url">`

### 圖片上傳方式

系統會將圖片上傳到目標 repository 的 `assets/issue_images/` 目錄中。

**注意**: 這需要目標 repository 有 `main` 或 `master` 分支，且服務有寫入權限。

### 權限要求

GitHub Token 需要以下權限：
- `repo` - 完整的 repository 訪問權限
  - 包含創建 issues
  - 包含上傳文件到 repository

## 故障排除

### 問題: Issue 沒有被複製

**檢查項目**:
1. `config.yaml` 中 `issue_copy.enabled` 是否為 `true`
2. 來源 repository 是否正確
3. Issue 是否有匹配的 labels
4. Webhook 是否正確設置
5. 查看服務日誌

### 問題: 圖片無法上傳

**可能原因**:
1. GitHub Token 權限不足
2. 目標 repository 沒有 `main` 分支
3. 圖片 URL 無法訪問
4. 網絡問題

**解決方案**:
- 確認 Token 有 `repo` 權限
- 檢查目標 repository 的預設分支名稱
- 測試圖片 URL 是否可訪問
- 查看詳細日誌

### 問題: Labels 沒有被複製

**可能原因**:
- 目標 repository 沒有對應的 labels

**解決方案**:
- 在目標 repository 創建所需的 labels
- 系統會自動跳過不存在的 labels

## API 端點

服務提供以下 API 端點來測試和監控：

### 健康檢查

```bash
curl http://localhost:5000/health
```

### Webhook 端點

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -d @test_payload.json
```

## 日誌

服務會記錄詳細的處理日誌：

- Issue 接收和處理
- Label 匹配結果
- 圖片下載和上傳
- Issue 創建結果
- 錯誤和警告

查看日誌：

```bash
# Docker 環境
docker logs pr-reviewer

# 直接運行
# 日誌輸出到 stdout
```

## 安全性考量

1. **Webhook Secret**: 務必設置 `WEBHOOK_SECRET` 環境變數
2. **Token 權限**: 使用最小權限原則，只授予必要的 repository 訪問權限
3. **HTTPS**: 生產環境務必使用 HTTPS
4. **IP 限制**: 考慮限制只接受來自 GitHub 的請求

## 未來改進

可能的改進方向：

1. 支援更複雜的 label 路由規則
2. 支援 issue comments 的同步
3. 支援雙向同步
4. 添加更多的通知渠道（Slack, Email）
5. Web UI 管理介面
6. 統計和分析功能

## 相關文件

- [主要文檔](../README.md)
- [Webhook 設置指南](setup/WEBHOOK_SETUP.md)
- [GitHub Token 設置](setup/GITHUB_TOKEN_SETUP.md)
- [測試指南](testing/WEBHOOK_TEST.md)
