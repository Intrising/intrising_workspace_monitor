# GitHub Token 權限設置指南

本指南說明如何創建具有適當權限的 GitHub Personal Access Token (PAT)，以及如何配置郵件通知。

## 🔑 GitHub Token 所需權限

### Classic Token（推薦用於此項目）

前往：https://github.com/settings/tokens

點擊 **Generate new token** → **Generate new token (classic)**

#### 必須的權限（Scopes）：

##### 1. **repo** - 完整的倉庫訪問權限
- ✅ `repo:status` - 訪問提交狀態
- ✅ `repo_deployment` - 訪問部署狀態
- ✅ `public_repo` - 訪問公開倉庫
- ✅ `repo:invite` - 訪問倉庫邀請
- ✅ `security_events` - 訪問安全事件

**為什麼需要**：讀取 PR 信息、獲取 diff、發布評論

##### 2. **write:discussion** - 讀寫討論
- ✅ `read:discussion` - 讀取討論
- ✅ `write:discussion` - 寫入討論

**為什麼需要**：在 PR 中發布審查評論

##### 3. **read:user** - 讀取用戶信息
- ✅ `read:user` - 讀取用戶資料
- ✅ `user:email` - 訪問用戶郵箱地址

**為什麼需要**：獲取 PR 作者和審查者的郵箱地址

##### 4. **read:org**（如果是組織倉庫）
- ✅ `read:org` - 讀取組織信息

**為什麼需要**：訪問組織成員的郵箱

### Fine-grained Token（新版，更安全）

前往：https://github.com/settings/personal-access-tokens/new

#### Repository access:
- 選擇 **All repositories** 或指定特定倉庫

#### Permissions:
- **Pull requests**: Read and write（讀寫 PR）
- **Contents**: Read（讀取代碼）
- **Metadata**: Read（讀取元數據）
- **Members**: Read（讀取成員信息，用於獲取郵箱）

## 📧 獲取 PR 相關人員郵箱

### 方案 1：從 GitHub API 獲取（推薦）

PR 審查系統會自動獲取以下人員的郵箱：

1. **PR 作者**
2. **PR 審查者（Reviewers）**
3. **倉庫管理員/所有者**
4. **受影響代碼的提交者**

#### 實現邏輯

```python
def get_pr_notification_recipients(repo_full_name: str, pr_number: int) -> List[str]:
    """獲取 PR 通知收件人列表"""
    recipients = []

    try:
        repo = github.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        # 1. PR 作者
        author_email = pr.user.email
        if author_email:
            recipients.append(author_email)

        # 2. PR 審查者
        for reviewer in pr.requested_reviewers:
            if reviewer.email:
                recipients.append(reviewer.email)

        # 3. 已經審查過的人
        for review in pr.get_reviews():
            if review.user.email:
                recipients.append(review.user.email)

        # 4. 倉庫管理員（可選）
        # for collaborator in repo.get_collaborators(permission='admin'):
        #     if collaborator.email:
        #         recipients.append(collaborator.email)

        # 去重
        return list(set(recipients))

    except Exception as e:
        logger.error(f"獲取收件人失敗: {e}")
        return []
```

### 方案 2：在 config.yaml 配置郵箱映射

如果 GitHub API 無法獲取郵箱（用戶隱私設置），可以在配置中手動映射：

```yaml
notifications:
  email:
    enabled: true

    # 默認收件人（總是接收）
    default_recipients:
      - "team-lead@intrising.com.tw"
      - "khkh@intrising.com.tw"

    # GitHub 用戶名 → 郵箱映射
    user_email_mapping:
      yulianghsueh: "yuliang@intrising.com.tw"
      john_doe: "john@intrising.com.tw"
      jane_smith: "jane@intrising.com.tw"

    # 根據倉庫配置收件人
    repository_recipients:
      "Intrising/kh_utils":
        - "devops@intrising.com.tw"
        - "khkh@intrising.com.tw"
      "Intrising/another-repo":
        - "team@intrising.com.tw"
```

### 方案 3：從 Git commit 獲取

從 PR 的 commits 中提取提交者郵箱：

```python
def get_committer_emails(pr) -> List[str]:
    """從 commits 獲取提交者郵箱"""
    emails = []

    for commit in pr.get_commits():
        # Git commit 中的作者郵箱
        if commit.commit.author.email:
            emails.append(commit.commit.author.email)

        # Git commit 中的提交者郵箱
        if commit.commit.committer.email:
            emails.append(commit.commit.committer.email)

    return list(set(emails))
```

## 🔧 完整配置示例

### config.yaml

```yaml
# 倉庫監控配置
repositories:
  - owner: "Intrising"
    name: "kh_utils"
    branches:
      - "master"
      - "develop"

# 通知配置
notifications:
  # Slack 通知
  slack:
    enabled: true
    # channel: "#team-switch"  # 從環境變數讀取

  # Email 通知
  email:
    enabled: true

    # 通知策略
    notify_strategy: "smart"  # all / smart / custom
    # - all: 所有人（PR作者 + 審查者 + 默認收件人）
    # - smart: PR作者 + 審查者
    # - custom: 僅使用 default_recipients

    # 默認收件人（總是接收）
    default_recipients:
      - "khkh@intrising.com.tw"
      - "devops@intrising.com.tw"

    # GitHub 用戶名 → 郵箱映射（可選）
    user_email_mapping:
      yulianghsueh: "yuliang@intrising.com.tw"

    # 按倉庫配置（可選）
    repository_recipients:
      "Intrising/kh_utils":
        - "devops@intrising.com.tw"

# PR 自動審查配置
review:
  # 觸發審查的 PR 動作
  triggers:
    - opened       # PR 被創建
    - synchronize  # PR 有新的提交
    - reopened     # PR 被重新開啟

  # 是否跳過 draft PR
  skip_draft: true

  # 是否自動添加 "auto-reviewed" 標籤
  auto_label: true

  # 審查重點關注的方面
  focus_areas:
    - "代碼質量和可讀性"
    - "潛在的 bug 和錯誤處理"
    - "性能問題和優化建議"
    - "安全漏洞和最佳實踐"
    - "測試覆蓋率"
    - "文檔和注釋完整性"

  # 回覆語言
  language: "zh-TW"

  # 審查完成後的通知
  notify_on_review:
    email: true
    slack: true
```

## 📝 創建 Token 步驟

### Step 1: 登錄 GitHub

前往：https://github.com/settings/tokens

### Step 2: 創建新 Token

1. 點擊 **Generate new token** → **Generate new token (classic)**
2. 填寫描述：`PR Monitor - kh_utils`
3. 選擇過期時間：建議 **90 days** 或 **No expiration**（需定期輪換）

### Step 3: 選擇權限

勾選以下 scopes：

```
✅ repo
  ✅ repo:status
  ✅ repo_deployment
  ✅ public_repo
  ✅ repo:invite
  ✅ security_events

✅ write:discussion
  ✅ read:discussion

✅ read:user
  ✅ user:email

✅ read:org (如果是組織倉庫)
```

### Step 4: 生成並複製 Token

1. 點擊 **Generate token**
2. **立即複製** token（只會顯示一次！）
3. 格式：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 5: 配置到 .env

```bash
# 編輯 .env 文件
vim .env

# 填入 Token
GITHUB_TOKEN=ghp_your_actual_token_here
```

### Step 6: 測試 Token

```bash
# 測試 Token 權限
curl -H "Authorization: token ghp_your_actual_token_here" \
  https://api.github.com/user

# 應該返回您的用戶信息
```

## 🧪 測試郵箱獲取

創建測試腳本來驗證能否獲取郵箱：

```python
#!/usr/bin/env python3
"""測試 GitHub API 獲取用戶郵箱"""

import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

github_token = os.getenv("GITHUB_TOKEN")
g = Github(github_token)

# 測試獲取自己的郵箱
user = g.get_user()
print(f"當前用戶: {user.login}")
print(f"郵箱: {user.email}")
print(f"公開郵箱: {user.email or '未公開'}")

# 測試獲取特定用戶的郵箱
test_user = g.get_user("yulianghsueh")
print(f"\n測試用戶: {test_user.login}")
print(f"郵箱: {test_user.email or '未公開'}")

# 測試獲取 PR 信息
repo = g.get_repo("Intrising/kh_utils")
# prs = repo.get_pulls(state='all')
# if prs.totalCount > 0:
#     pr = prs[0]
#     print(f"\nPR: {pr.title}")
#     print(f"作者: {pr.user.login}")
#     print(f"作者郵箱: {pr.user.email or '未公開'}")
```

保存為 `test_github_email.py` 並運行：

```bash
python3 test_github_email.py
```

## ⚠️ 重要提醒

### 1. Token 安全

- ❌ **絕對不要**提交 token 到 Git
- ✅ 使用 `.env` 文件並加入 `.gitignore`
- ✅ 定期輪換 token（建議 90 天）
- ✅ 使用最小權限原則

### 2. 郵箱隱私

- 部分用戶在 GitHub 設置中隱藏了郵箱
- 即使有 `user:email` 權限也可能無法獲取
- **解決方案**：使用 `user_email_mapping` 手動配置

### 3. 郵箱獲取優先級

系統會按以下順序嘗試獲取郵箱：

1. GitHub API 返回的 `user.email`
2. `config.yaml` 中的 `user_email_mapping`
3. Git commit 中的郵箱
4. 使用 `default_recipients`

## 📊 檢查清單

設置完成後，確認以下項目：

- [ ] GitHub Token 已創建並具有所需權限
- [ ] Token 已配置到 `.env` 文件
- [ ] Token 權限測試通過
- [ ] 能夠訪問倉庫和 PR
- [ ] 能夠發布評論（在測試 PR 中驗證）
- [ ] 郵箱獲取策略已配置
- [ ] `config.yaml` 中的郵件收件人已設置
- [ ] msmtp 郵件發送已測試

## 🔗 相關文檔

- [GitHub Token 文檔](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [GitHub API - Users](https://docs.github.com/en/rest/users/users)
- [PyGithub 文檔](https://pygithub.readthedocs.io/)

---

**Token 創建完成後，記得測試並更新 `.env` 文件！**
