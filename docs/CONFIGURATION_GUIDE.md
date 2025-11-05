# 配置指南

## 監控儲存庫配置

### 方式 1: 監控單個儲存庫

```yaml
monitor:
  repositories:
    - owner: "organization-name"
      repo: "repository-name"
      branches:
        - main
        - develop
```

### 方式 2: 監控整個組織的所有儲存庫 ⭐

```yaml
monitor:
  repositories:
    - owner: "Intrising"
      all: true  # 自動獲取並監控組織下所有儲存庫
      branches:
        - main
        - master
        - develop
```

**優點**：
- ✅ 自動發現新儲存庫
- ✅ 無需手動維護儲存庫列表
- ✅ 適合監控整個組織

**注意事項**：
- 需要 GitHub Token 有讀取組織儲存庫的權限
- 首次運行會獲取完整的儲存庫列表
- 儲存庫數量較多時，檢查時間會較長

### 方式 3: 混合配置

```yaml
monitor:
  repositories:
    # 監控整個組織
    - owner: "Intrising"
      all: true
      branches:
        - main

    # 同時監控其他單個儲存庫
    - owner: "another-org"
      repo: "important-repo"
      branches:
        - main
        - staging
        - production
```

## 分支過濾

### 監控所有分支

```yaml
repositories:
  - owner: "Intrising"
    all: true
    branches: []  # 空列表 = 監控所有分支
```

### 只監控特定分支

```yaml
repositories:
  - owner: "Intrising"
    all: true
    branches:
      - main
      - master
      - develop
```

## 完整配置範例

### 當前配置（Intrising 組織）

```yaml
# GitHub Monitor Configuration
monitor:
  # 檢查間隔（秒）
  check_interval: 300  # 5分鐘

  # 監控 Intrising 組織下的所有儲存庫
  repositories:
    - owner: "Intrising"
      all: true
      branches:
        - main
        - master
        - develop

  # PR 狀態過濾
  pr_states:
    - open

  # 警報條件
  alerts:
    open_duration_hours: 24    # PR 開啟超過 24 小時
    no_reviewer: true          # 沒有審查者
    has_conflicts: true        # 有合併衝突
    ci_failed: true           # CI 檢查失敗

# 通知設定
notifications:
  slack:
    enabled: true

# 日誌設定
logging:
  level: INFO
  format: json
  file: /var/log/github-monitor/app.log
```

## 環境變數配置

確保 `.env` 文件包含：

```bash
# GitHub 配置
GITHUB_TOKEN=ghp_your_github_personal_access_token

# Slack 配置
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#pr-alerts

# 應用設置
LOG_LEVEL=INFO
CHECK_INTERVAL=300
TZ=Asia/Taipei
```

## GitHub Token 權限需求

監控組織儲存庫需要以下權限：

- ✅ `repo` - 完整儲存庫訪問
- ✅ `read:org` - 讀取組織資訊
- ✅ `read:user` - 讀取用戶資訊

### 如何生成 Token

1. 前往 GitHub Settings → Developer settings → Personal access tokens
2. 點擊 "Generate new token (classic)"
3. 選擇所需權限
4. 複製生成的 token
5. 添加到 `.env` 文件

## 測試配置

```bash
# 1. 檢查配置
make check

# 2. 啟動服務（開發模式）
make start-dev

# 3. 查看日誌（確認是否成功獲取儲存庫列表）
make logs

# 預期日誌輸出：
# "組織 Intrising 下找到 X 個儲存庫"
# "檢查儲存庫: Intrising/repo-name"
```

## 效能考量

### 檢查間隔建議

| 儲存庫數量 | 建議間隔 |
|-----------|---------|
| 1-10      | 300秒 (5分鐘) |
| 11-50     | 600秒 (10分鐘) |
| 51-100    | 900秒 (15分鐘) |
| 100+      | 1800秒 (30分鐘) |

### GitHub API 速率限制

- **免費帳號**: 5,000 請求/小時
- **企業帳號**: 15,000 請求/小時

每次檢查大約消耗：
- 1 次獲取組織儲存庫列表
- N 次獲取每個儲存庫的 PR（N = 儲存庫數量）
- 每個 PR 約 2-3 次 API 請求

**估算**：監控 50 個儲存庫，每次檢查約消耗 150-200 次請求。

## 常見問題

### Q: 如何排除特定儲存庫？

A: 目前不支持排除，但可以手動列出要監控的儲存庫：

```yaml
repositories:
  - owner: "Intrising"
    repo: "repo-1"
  - owner: "Intrising"
    repo: "repo-2"
```

### Q: 新增的儲存庫會自動監控嗎？

A: 是的！使用 `all: true` 時，每次檢查都會重新獲取組織儲存庫列表。

### Q: 如何只監控公開儲存庫？

A: 需要修改程式碼過濾，或使用沒有私有倉庫權限的 Token。

### Q: 監控大量儲存庫會影響性能嗎？

A: 會的。建議：
- 增加檢查間隔
- 使用分支過濾減少 PR 數量
- 考慮部署多個實例分散負載

## 進階配置

### 使用多個組織

```yaml
repositories:
  - owner: "Intrising"
    all: true
    branches:
      - main

  - owner: "another-org"
    all: true
    branches:
      - master
```

### 混合監控策略

```yaml
repositories:
  # 監控整個 Intrising 組織
  - owner: "Intrising"
    all: true
    branches:
      - main
      - master

  # 監控合作夥伴的特定專案
  - owner: "partner-org"
    repo: "important-project"
    branches:
      - main
      - staging
      - production
```

---

**配置完成後記得重啟服務**：
```bash
make restart
make logs  # 確認配置生效
```
