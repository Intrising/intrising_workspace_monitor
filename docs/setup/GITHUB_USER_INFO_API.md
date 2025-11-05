# GitHub 用戶資訊與 PR 參與者 API

本文檔說明如何使用新增的 API endpoints 來獲取 GitHub 用戶資訊和 PR 參與者。

## 🔑 所需 Token 權限

### 最小權限設置
```
☑ repo - 完整倉庫權限（必需）
☑ read:org - 讀取組織資訊（如果是組織倉庫）
☑ read:user - 讀取用戶基本資訊（必需）
```

### 創建 Token
1. 前往: https://github.com/settings/tokens
2. 點擊 "Generate new token (classic)"
3. 設置名稱: "PR Auto Reviewer - Full Access"
4. 選擇權限:
   - **repo** (完整勾選)
   - **read:org** (組織倉庫必需)
   - **read:user** (獲取用戶資訊必需)
5. 生成並複製 token
6. 更新 `.env` 文件:
   ```bash
   GITHUB_TOKEN=ghp_your_new_token_here
   ```

## 📡 API Endpoints

### 1. 獲取用戶資訊

**Endpoint**: `GET /api/user/<username>`

**範例**:
```bash
curl http://localhost:8080/api/user/octocat
```

**回應**:
```json
{
  "status": "success",
  "user": {
    "id": 583231,
    "login": "octocat",
    "name": "The Octocat",
    "email": "octocat@github.com",
    "company": "@github",
    "location": "San Francisco",
    "bio": null,
    "public_repos": 8,
    "followers": 10000,
    "created_at": "2011-01-25T18:44:36"
  }
}
```

### 2. 獲取 PR 參與者資訊

**Endpoint**: `GET /api/pr/<repo_owner>/<repo_name>/<pr_number>/participants`

**範例**:
```bash
curl http://localhost:8080/api/pr/Intrising/my-repo/123/participants
```

**回應**:
```json
{
  "status": "success",
  "repo": "Intrising/my-repo",
  "pr_number": 123,
  "participants": {
    "author": {
      "id": 12345,
      "login": "john_doe",
      "name": "John Doe",
      "email": "john@example.com",
      "company": "My Company",
      "location": "Taiwan",
      "bio": "Developer",
      "public_repos": 50,
      "followers": 100,
      "created_at": "2015-01-01T00:00:00"
    },
    "reviewers": [
      {
        "id": 67890,
        "login": "reviewer1",
        "name": "Reviewer One",
        "email": null,
        ...
      }
    ],
    "assignees": [...],
    "commenters": [...]
  }
}
```

## ⚠️ Email 隱私限制

### 重要說明
- **GitHub API 無法獲取用戶的私人 email**
- 只能獲取用戶**公開設置**的 email
- 大多數用戶會選擇隱藏 email 地址

### Email 可見性設置
用戶可以在以下位置控制 email 可見性：
1. 前往 https://github.com/settings/emails
2. 取消勾選 "Keep my email addresses private"

### 獲取 Email 的替代方案

如果需要聯繫 PR 參與者，建議：

1. **通過 GitHub Commit Email**:
   ```python
   # 從 PR 的 commits 獲取作者 email
   commits = pr.get_commits()
   for commit in commits:
       email = commit.commit.author.email
       print(f"Commit Email: {email}")
   ```

2. **通過組織成員 API** (需要組織管理員權限):
   ```python
   # 如果是組織成員，可以獲取更多資訊
   org = g.get_organization("Intrising")
   member = org.get_member(username)
   ```

3. **在 PR 中 @ 提及用戶**:
   ```python
   comment = f"@{username} 請查看審查意見"
   pr.create_issue_comment(comment)
   ```

## 🧪 測試

### 使用提供的測試腳本

```bash
# 1. 確保 GITHUB_TOKEN 已設置
cat .env | grep GITHUB_TOKEN

# 2. 運行測試腳本
python3 /tmp/test_user_info.py
```

### 直接測試 API

```bash
# 1. 啟動服務
docker compose -f docker-compose.reviewer-cli.yml up -d

# 2. 測試獲取用戶資訊
curl http://localhost:8080/api/user/octocat | jq

# 3. 測試獲取 PR 參與者（替換為真實的倉庫和 PR）
curl http://localhost:8080/api/pr/owner/repo/1/participants | jq
```

## 📊 可獲取的用戶資訊

| 欄位 | 說明 | 總是可用 |
|------|------|---------|
| `id` | 用戶 ID | ✅ |
| `login` | 用戶名稱 | ✅ |
| `name` | 顯示名稱 | ✅ |
| `email` | Email 地址 | ❌ (需公開) |
| `company` | 公司 | ⚠️ (如果設置) |
| `location` | 位置 | ⚠️ (如果設置) |
| `bio` | 個人簡介 | ⚠️ (如果設置) |
| `public_repos` | 公開倉庫數 | ✅ |
| `followers` | 追蹤者數 | ✅ |
| `created_at` | 帳號建立時間 | ✅ |

## 💡 使用範例

### 範例 1: 在審查後通知參與者

```python
# 獲取 PR 參與者
participants = reviewer.get_pr_participants(repo_full_name, pr_number)

# 構建通知訊息
mentions = []
if participants['author']:
    mentions.append(f"@{participants['author']['login']}")

for reviewer in participants['reviewers']:
    mentions.append(f"@{reviewer['login']}")

# 發送通知
comment = f"{' '.join(mentions)} 代碼審查已完成，請查看"
pr.create_issue_comment(comment)
```

### 範例 2: 記錄參與者資訊

```python
# 記錄所有參與者的 ID 和 email
participants = reviewer.get_pr_participants(repo_full_name, pr_number)

for role, users in participants.items():
    if isinstance(users, list):
        for user in users:
            print(f"{role}: {user['login']} (ID: {user['id']}, Email: {user.get('email', 'N/A')})")
    elif isinstance(users, dict):
        print(f"{role}: {users['login']} (ID: {users['id']}, Email: {users.get('email', 'N/A')})")
```

## 🔒 權限注意事項

### 對於私有倉庫
- Token 必須有 `repo` (完整權限)
- 無法訪問沒有權限的私有倉庫

### 對於組織倉庫
- 建議添加 `read:org` 權限
- 可以獲取組織成員資訊

### 安全建議
- Token 應該保存在 `.env` 文件中
- `.env` 已加入 `.gitignore`
- 定期輪換 Token
- 使用最小必要權限原則

## 📚 相關文檔

- [GitHub API - Users](https://docs.github.com/en/rest/users)
- [GitHub API - Pull Requests](https://docs.github.com/en/rest/pulls)
- [PyGithub 文檔](https://pygithub.readthedocs.io/)
