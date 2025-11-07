# Issue 評分系統設置說明

## 系統概述

Issue Scorer 是一個基於 Claude AI 的 Issue 品質評分系統，用於自動評估 GitHub Issue 和評論的格式正確性、內容完整性、清晰度和可操作性。

## 評分維度

每個 Issue/Comment 會從以下四個維度進行評分（0-100分）：

1. **📝 格式正確性** - 標題、描述、Markdown 格式是否符合規範
2. **📋 內容完整性** - 是否包含必要資訊（重現步驟、預期結果、實際結果、環境資訊）
3. **🎯 清晰度** - 描述是否清楚明確，語言表達是否專業
4. **⚙️ 可操作性** - 開發人員是否能根據描述重現問題

最後會計算出**總體評分**和提供**改進建議**。

## 目標 Repositories

系統目前配置為監控以下 8 個 repositories：

- `Intrising/QA-Switch-OS5`
- `Intrising/test-cloud`
- `Intrising/QA-Switch-OS6`
- `Intrising/QA-Video-switch`
- `Intrising/QA-Switch-OS3OS4`
- `Intrising/QA-Switch-OS2`
- `Intrising/QA-Viewer`
- `Intrising/test-switch`

## 觸發條件

### Issue 事件
- `opened` - Issue 被創建時
- `edited` - Issue 被編輯時

### Comment 事件
- `created` - 評論被創建時
- `edited` - 評論被編輯時

## 部署說明

### 1. 建立容器

```bash
cd /home/khkh/Documents/github/intrising_workspace_monitor

# 構建 Issue Scorer 映像
docker build -f docker/Dockerfile.issue-scorer -t issue-scorer:latest .

# 啟動所有服務（包括 Issue Scorer）
docker-compose -f docker-compose.microservices.yml up -d
```

### 2. 檢查服務狀態

```bash
# 檢查所有容器
docker-compose -f docker-compose.microservices.yml ps

# 查看 Issue Scorer 日誌
docker logs -f issue-scorer

# 檢查健康狀態
curl http://localhost:8083/health  # 容器內部
```

### 3. 測試評分功能

訪問 Dashboard 查看 Issue Scorer 卡片：
```
http://<gateway-host>:8080/
```

訪問評分詳情頁面：
```
http://<gateway-host>:8080/issue-scores
```

### 4. 配置 GitHub Webhook

在目標 repositories 中設置 webhook：

- **Payload URL**: `http://<gateway-host>:8080/webhook`
- **Content type**: `application/json`
- **Secret**: 使用 `.env` 中的 `WEBHOOK_SECRET`
- **Events**: 選擇 `Issues` 和 `Issue comments`

## API 端點

### Issue Scorer 服務 (port 8083)

- `GET /health` - 健康檢查
- `POST /webhook` - 接收 GitHub webhook
- `GET /api/scores?limit=100&status=completed` - 獲取評分列表
- `GET /api/scores/<score_id>` - 獲取單個評分詳情

### Gateway 代理 (port 8080)

- `GET /api/issue-scorer/scores?limit=50` - 通過 Gateway 訪問評分數據
- `GET /issue-scores` - 評分結果展示頁面

## 資料庫結構

### issue_scores 表

```sql
CREATE TABLE issue_scores (
    score_id TEXT PRIMARY KEY,
    repo_name TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    comment_id INTEGER,
    event_type TEXT NOT NULL,
    content_type TEXT NOT NULL,
    title TEXT,
    body TEXT,
    author TEXT,
    issue_url TEXT,
    format_score INTEGER,
    format_feedback TEXT,
    content_score INTEGER,
    content_feedback TEXT,
    clarity_score INTEGER,
    clarity_feedback TEXT,
    actionability_score INTEGER,
    actionability_feedback TEXT,
    overall_score INTEGER,
    suggestions TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
```

## 配置文件

### config.yaml

```yaml
issue_scoring:
  enabled: true
  target_repos:
    - "Intrising/QA-Switch-OS5"
    - "Intrising/test-cloud"
    - "Intrising/QA-Switch-OS6"
    - "Intrising/QA-Video-switch"
    - "Intrising/QA-Switch-OS3OS4"
    - "Intrising/QA-Switch-OS2"
    - "Intrising/QA-Viewer"
    - "Intrising/test-switch"
  triggers:
    - opened
    - edited
  comment_triggers:
    - created
    - edited
  scoring_criteria:
    - "格式正確性：標題、描述、步驟是否符合規範"
    - "內容完整性：是否包含必要資訊"
    - "清晰度：描述是否清楚明確"
    - "可操作性：開發人員是否能根據描述重現問題"
  auto_comment: true  # 自動在 Issue 中回覆評分結果
  language: "zh-TW"
```

## 工作流程

1. GitHub 發送 issue/comment webhook 到 Gateway
2. Gateway 驗證簽名，路由到 Issue Scorer 服務
3. Issue Scorer 檢查是否符合評分條件（repository、action）
4. 創建評分任務記錄（status: queued）
5. 啟動後台線程執行評分
6. 使用 Claude CLI 分析 Issue/Comment 內容
7. 解析評分結果（JSON格式）
8. 將評分結果發布到 GitHub Issue 作為評論
9. 更新資料庫記錄（status: completed）

## 故障排除

### Issue Scorer 無法啟動

1. 檢查 Claude CLI 是否正確掛載：
   ```bash
   docker exec issue-scorer which claude
   docker exec issue-scorer claude --version
   ```

2. 檢查配置文件是否正確：
   ```bash
   docker exec issue-scorer cat /app/config.yaml
   ```

### 評分失敗

1. 查看服務日誌：
   ```bash
   docker logs issue-scorer --tail 100
   ```

2. 檢查資料庫記錄：
   ```bash
   docker exec workspace-monitor sqlite3 /var/lib/github-monitor/tasks.db \
     "SELECT * FROM issue_scores WHERE status='failed' ORDER BY created_at DESC LIMIT 5;"
   ```

### Webhook 未觸發評分

1. 確認 repository 在 target_repos 列表中
2. 確認 action 在 triggers 或 comment_triggers 中
3. 檢查 Gateway 日誌查看 webhook 路由情況

## 監控指標

在 Dashboard 可以查看：

- **總評分數** - 所有評分任務總數
- **已完成** - 成功完成的評分數
- **平均分數** - 所有已完成評分的平均總分
- **處理中** - 正在評分的任務數

## 未來改進

- [ ] 支持自定義評分標準
- [ ] 支持多語言評分（英文、日文等）
- [ ] 評分歷史趨勢分析
- [ ] 與 PR Review 整合
- [ ] 評分結果導出功能
