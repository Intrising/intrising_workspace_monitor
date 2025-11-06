# Intrising Workspace Monitor

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

企業級 GitHub 自動化工具，支援 PR 自動審查、Issue 自動複製、以及 PR 監控警報通知。

## 📋 目錄

- [功能特性](#功能特性)
- [專案目錄結構](#專案目錄結構)
- [系統架構](#系統架構)
- [Webhook 監聽說明](#webhook-監聽說明)
- [快速開始](#快速開始)
- [詳細配置](#詳細配置)
- [部署指南](#部署指南)
- [運維管理](#運維管理)
- [故障排查](#故障排查)
- [安全最佳實踐](#安全最佳實踐)

## ✨ 功能特性

### 🤖 自動化功能

#### 1. PR 自動審查 (PR Reviewer)
- 使用 Claude AI (Codex CLI) 自動審查 Pull Request
- 觸發時機：PR opened, synchronize, reopened
- 自動發布審查評論到 PR
- 支援自訂審查重點和語言
- 詳細文件：[docs/migration/README_REVIEWER.md](docs/migration/README_REVIEWER.md)

#### 2. Issue 自動複製 (Issue Copier)
- 根據 label 自動複製 issue 到目標 repositories
- 支援多目標複製（一個 issue 可複製到多個 repo）
- 自動添加來源引用和複製記錄
- 支援評論同步功能
- 詳細文件：[docs/ISSUE_COPIER.md](docs/ISSUE_COPIER.md)

#### 3. PR 監控與警報
- 定期檢查指定儲存庫的 Pull Requests
- 多種警報條件：
  - PR 開啟時間過長
  - 缺少審查者
  - 存在合併衝突
  - CI/CD 檢查失敗
- Slack 和 Email 通知整合

### 🏢 企業級特性
- 🐳 **Docker 容器化**：完整的 Docker 支持
- 🔒 **安全加固**：非 root 用戶運行、只讀文件系統
- 📊 **健康檢查**：內建健康檢查機制
- 📝 **結構化日誌**：支持 JSON 格式日誌
- 💾 **資料庫持久化**：SQLite 儲存任務和複製記錄
- 🔄 **資源限制**：CPU 和記憶體使用限制
- 🛡️ **多環境支持**：開發、生產環境分離

## 📁 專案目錄結構

```
intrising_workspace_monitor/
├── src/                          # 核心程式碼
│   ├── pr_reviewer.py           # 統一 Webhook 服務器 + PR 審查（主要服務）
│   ├── pr_reviewer_api.py       # PR Reviewer (Anthropic API 版本)
│   ├── issue_copier.py          # Issue 自動複製模組
│   ├── pr_monitor.py            # PR 監控服務（定時任務）
│   ├── database.py              # 資料庫操作（SQLite）
│   └── healthcheck.py           # 健康檢查腳本
│
├── docker/                       # Docker 相關配置
│   ├── Dockerfile               # 主要 Dockerfile
│   ├── Dockerfile.reviewer      # PR Reviewer 專用 Dockerfile
│   ├── Dockerfile.claude        # Claude CLI 專用 Dockerfile
│   │
│   ├── docker-compose.yml       # 基礎配置
│   ├── docker-compose.dev.yml   # 開發環境配置
│   ├── docker-compose.prod.yml  # 生產環境配置
│   ├── docker-compose.pr-reviewer.yml     # PR Reviewer 服務（推薦）⭐
│   ├── docker-compose.reviewer.yml        # Reviewer 替代配置
│   ├── docker-compose.reviewer-cli.yml    # CLI 版本配置
│   ├── docker-compose.webhook-test.yml    # Webhook 測試服務
│   └── docker-compose.webhook-simple.yml  # 簡化 Webhook 測試
│
├── scripts/                      # 工具腳本
│   ├── test_webhook.py          # Webhook 接收測試（Python）
│   ├── test_webhook_curl.sh     # Webhook 測試（curl）
│   ├── test_webhook_simple.sh   # 簡單 Webhook 測試
│   ├── test_issue_copier.py     # Issue copier 功能測試
│   ├── trigger_issue_copy.py    # 手動觸發 issue 複製
│   ├── test_github_permissions.py  # 測試 GitHub 權限
│   │
│   ├── sync_missing_copy_records.py   # 同步遺失的複製記錄
│   ├── batch_sync_copy_records.py     # 批次同步記錄
│   ├── migrate_db_add_unique_constraint.py  # 資料庫遷移
│   │
│   ├── deploy.sh                # 部署腳本
│   ├── setup_claude_auth.sh     # Codex CLI 認證設定
│   ├── generate_msmtprc.sh      # 生成郵件配置
│   └── test_email.py            # 測試郵件發送
│
├── build/                        # 構建相關
│   ├── Makefile                 # 主要 Makefile
│   └── Makefile.reviewer        # Reviewer 專用 Makefile
│
├── config/                       # 配置範本
│   ├── msmtprc.example          # 郵件配置範例
│   └── .msmtprc.template        # 郵件配置模板
│
├── docs/                         # 文檔
│   ├── QUICKSTART.md            # 快速開始指南
│   ├── FEATURES.md              # 功能詳細說明
│   ├── DEPLOYMENT.md            # 部署指南
│   ├── CONFIGURATION_GUIDE.md   # 配置指南
│   ├── ISSUE_COPIER.md          # Issue Copier 詳細文檔
│   ├── PROJECT_STRUCTURE.md     # 專案結構說明
│   ├── FILES_INDEX.md           # 檔案索引
│   │
│   ├── setup/                   # 設定指南目錄
│   │   ├── GITHUB_WEBHOOK_CONFIG.md  # GitHub Webhook 設定
│   │   ├── GITHUB_TOKEN_SETUP.md     # GitHub Token 設定
│   │   ├── WEBHOOK_SETUP.md          # Webhook 設定
│   │   ├── MSMTP_SETUP.md            # 郵件設定
│   │   ├── CLAUDE_CLI_SETUP.md       # Claude CLI 設定
│   │   └── CLAUDE_CODE_SETUP.md      # Claude Code 設定
│   │
│   ├── testing/                 # 測試文檔
│   │   └── WEBHOOK_TEST.md      # Webhook 測試指南
│   │
│   └── migration/               # 遷移文檔
│       ├── README_REVIEWER.md   # PR Reviewer 遷移文檔
│       └── CODEX_MIGRATION_SUMMARY.md  # Codex 遷移摘要
│
├── .private/                     # 私有配置（.gitignore）
│   ├── .env                     # 環境變數（不提交）
│   └── .msmtprc                 # 郵件配置（不提交）
│
├── config.yaml                   # 主要配置檔 ⭐
├── .env.example                  # 環境變數範例
├── requirements.txt              # Python 依賴
├── check_progress.sh             # 進度檢查腳本
├── DATABASE_SETUP.md             # 資料庫設定說明
├── DOCKER_USAGE.md               # Docker 使用說明
├── LICENSE                       # MIT 授權
└── README.md                     # 專案說明（本檔案）
```

**重要檔案說明**：
- ⭐ `docker/docker-compose.pr-reviewer.yml` - 推薦的部署配置
- ⭐ `config.yaml` - 所有功能的主要配置檔
- `src/pr_reviewer.py` - Webhook 服務器主程式（監聽 8080 端口）
- `.private/.env` - 環境變數（需自行創建，參考 `.env.example`）

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────┐
│         pr-reviewer 容器 (port 8080)                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Flask Webhook Server (src/pr_reviewer.py)          │
│  ├─ POST /webhook ─────────────────┐               │
│  │                                  │               │
│  │  ┌───────────────────────────┐ │               │
│  │  │ X-GitHub-Event 判斷       │ │               │
│  │  └───────────────────────────┘ │               │
│  │            │                     │               │
│  │            ├── pull_request ────┼─▶ PR Reviewer │
│  │            │   (Claude AI 審查) │   (Codex CLI) │
│  │            │                     │               │
│  │            ├── issues ──────────┼─▶ Issue Copier│
│  │            │   (自動複製)       │               │
│  │            │                     │               │
│  │            └── issue_comment ───┼─▶ Comment Sync│
│  │                (評論同步)       │               │
│  └──────────────────────────────────               │
│                                                      │
│  Database: /var/lib/github-monitor/tasks.db        │
│  Logs: /var/log/github-monitor/                    │
└─────────────────────────────────────────────────────┘
```

## 📡 Webhook 監聽說明

### 統一 Webhook 服務器

本專案使用**單一 Webhook 服務器**處理所有 GitHub 事件，位於 `src/pr_reviewer.py`。

**容器資訊**:
- **容器名稱**: `pr-reviewer`
- **映像**: `github-monitor:latest`
- **監聽地址**: `0.0.0.0:5000` (容器內部)
- **對外端口**: `8080`
- **啟動命令**: `python3 pr_reviewer.py`

### Webhook 端點

```bash
POST http://your-server:8080/webhook
POST http://your-server:8080/webhook/
```

### 處理的 GitHub 事件

#### 1. Pull Request 事件 (`pull_request`)
- **程式位置**: `src/pr_reviewer.py:1795-1797`
- **功能**: 使用 Claude AI (Codex CLI) 自動審查 PR
- **觸發動作**: `opened`, `synchronize`, `reopened`
- **處理流程**:
  1. 接收 webhook 事件
  2. 獲取 PR diff 和上下文
  3. 調用 Codex CLI 進行審查
  4. 發布審查評論到 PR

#### 2. Issue 事件 (`issues`)
- **程式位置**: `src/pr_reviewer.py:1800-1805`
- **功能**: 根據 label 自動複製 issue 到目標 repositories
- **觸發動作**: `opened`, `labeled`
- **啟用條件**: `config.yaml` 中 `issue_copy.enabled: true`
- **處理流程**:
  1. 檢查來源 repository 是否匹配
  2. 根據 labels 決定目標 repositories
  3. 複製 issue 內容（包含標題、body、labels）
  4. 在新 issue 添加來源引用
  5. 記錄複製結果到資料庫

#### 3. Issue Comment 事件 (`issue_comment`)
- **程式位置**: `src/pr_reviewer.py:1808-1813`
- **功能**: 同步原 issue 的評論到所有複製的 issues
- **觸發動作**: `created`
- **啟用條件**: `issue_copy.enabled: true`
- **處理流程**:
  1. 查詢資料庫找出此 issue 的所有複製記錄
  2. 將評論同步到所有目標 issues
  3. 如果評論包含圖片/附件，自動添加更新提醒
  4. 記錄同步結果到資料庫

### 其他可用 API 端點

```bash
GET  /                     # Web UI 主頁
GET  /health               # 健康檢查
GET  /api/tasks            # 查詢 PR 審查任務列表
GET  /api/task/<task_id>   # 查詢特定審查任務
GET  /api/pr/<owner>/<repo>/<pr_number>/participants  # 獲取 PR 參與者
GET  /api/user/<username>  # 獲取 GitHub 用戶信息
GET  /api/issue-copies     # 查詢 issue 複製記錄
GET  /api/issue-copies/stats  # issue 複製統計
GET  /api/comment-syncs    # 查詢評論同步記錄
GET  /issue-copies         # issue 複製記錄 UI 頁面
```

### GitHub Webhook 設定

在 GitHub Repository 設定中添加 Webhook：

1. 進入 Repository Settings → Webhooks → Add webhook
2. **Payload URL**: `http://your-server:8080/webhook`
3. **Content type**: `application/json`
4. **Secret**: 設定在 `.env` 的 `WEBHOOK_SECRET`
5. **事件選擇**:
   - Pull requests (PR 審查功能)
   - Issues (Issue 複製功能)
   - Issue comments (評論同步功能)
6. 確認 Active 已勾選

### 驗證 Webhook 運作

```bash
# 檢查容器狀態
docker ps | grep pr-reviewer

# 查看 webhook 日誌
docker logs -f pr-reviewer

# 測試健康檢查（不需要認證）
curl http://localhost:8080/health

# 查看 API 端點（需要認證）
curl -u admin:your_password http://localhost:8080/api/tasks
curl -u admin:your_password http://localhost:8080/api/issue-copies/stats

# 或在瀏覽器中訪問（會彈出登入框）
open http://localhost:8080
```

### Web UI 認證

所有 Web UI 和 API 端點都受到 HTTP Basic Authentication 保護（除了 `/health` 和 `/webhook`）：

**設定認證**：
```bash
# 在 .private/.env 中設置
WEB_USERNAME=admin
WEB_PASSWORD=your_secure_password
```

**訪問方式**：
1. **瀏覽器**：訪問 `http://localhost:8080`，會自動彈出登入框
2. **curl**：使用 `-u username:password` 參數
3. **API 客戶端**：使用 Basic Auth header

**安全建議**：
- ⚠️ 如果不設置 `WEB_PASSWORD`，Web UI 將**不需要認證**（非常不安全）
- ✅ 建議使用強密碼（至少 16 字元，包含大小寫字母、數字、特殊符號）
- ✅ 定期更換密碼
- ✅ 使用 HTTPS（透過反向代理如 Nginx）

**不需要認證的端點**：
- `GET /health` - 健康檢查（供監控系統使用）
- `POST /webhook` - GitHub Webhook（使用 WEBHOOK_SECRET 驗證）

## 🚀 快速開始

### 前置需求

- Docker >= 20.10
- Docker Compose >= 2.0
- GitHub Personal Access Token (需要 `repo` 和 `read:org` 權限)
- Codex CLI 認證 (用於 PR 審查功能)
- Slack Webhook URL（可選，用於通知）

### 5 分鐘快速部署

```bash
# 1. 克隆專案
git clone https://github.com/Intrising/intrising_workspace_monitor.git
cd intrising_workspace_monitor

# 2. 創建環境變數檔案
cp .env.example .private/.env
vim .private/.env  # 填入必要的環境變數

# 必要的環境變數：
# GITHUB_TOKEN=ghp_your_token
# ANTHROPIC_API_KEY=your_anthropic_key  # 如果使用 Anthropic API 版本
# WEBHOOK_SECRET=your_secret  # 用於驗證 GitHub webhook
# SLACK_WEBHOOK_URL=your_slack_webhook  # 可選

# 3. 配置 Codex CLI 認證
./scripts/setup_claude_auth.sh

# 4. 配置郵件通知（可選）
cp config/msmtprc.example .private/.msmtprc
vim .private/.msmtprc
chmod 600 .private/.msmtprc

# 5. 編輯監控配置
vim config.yaml
# - 設置要監控的 repositories
# - 配置 Issue 複製規則
# - 設置 PR 審查選項

# 6. 創建 Docker volumes
docker volume create github_pr_monitor_pr-reviewer-logs
docker volume create github_pr_monitor_pr-reviewer-db

# 7. 啟動服務
cd docker
docker-compose -f docker-compose.pr-reviewer.yml up -d

# 或使用 Makefile（如果在 build/ 目錄下）
make -f build/Makefile.reviewer start
```

就這麼簡單！服務已經啟動並開始運行。

### 驗證部署

```bash
# 查看服務狀態
docker ps | grep pr-reviewer

# 查看實時日誌
docker logs -f pr-reviewer

# 測試健康檢查
curl http://localhost:8080/health

# 查看 Web UI
open http://localhost:8080

# 查看 Issue 複製記錄
curl http://localhost:8080/api/issue-copies/stats
```

## ⚙️ 詳細配置

### 1. 環境變數配置 (.private/.env)

```bash
# GitHub 配置
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_API_URL=https://api.github.com

# Anthropic API (如果使用 pr_reviewer_api.py)
ANTHROPIC_API_KEY=sk-ant-your-api-key

# Codex CLI (用於 pr_reviewer.py)
CODEX_CLI_PATH=codex  # Codex CLI 執行檔路徑

# Webhook 配置
WEBHOOK_SECRET=your_webhook_secret  # GitHub Webhook 密鑰
WEBHOOK_HOST=0.0.0.0               # Webhook 監聽地址
WEBHOOK_PORT=5000                  # 容器內部端口（對外映射為 8080）

# Web UI 認證（Basic Auth）
WEB_USERNAME=admin                 # Web UI 登入用戶名
WEB_PASSWORD=your_secure_password  # Web UI 登入密碼（強烈建議設置）

# Slack 配置（可選）
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#pr-alerts

# 郵件配置（使用 msmtp，可選）
EMAIL_FROM=devops@example.com
MSMTP_CONFIG=/home/prmonitor/.msmtprc

# 資料庫配置
DATABASE_PATH=/var/lib/github-monitor/tasks.db

# 應用設置
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
FLASK_DEBUG=false       # Flask 調試模式
TZ=Asia/Taipei         # 時區
```

#### 獲取 GitHub Token

1. 訪問 GitHub Settings → Developer settings → Personal access tokens
2. 生成新 token (classic)，需要以下權限：
   - `repo` (完整儲存庫訪問)
   - `read:org` (讀取組織資訊)
   - `write:discussion` (如果需要發布評論)

#### 設置 Slack Webhook

1. 訪問 Slack App 管理頁面
2. 創建新的 Incoming Webhook
3. 選擇目標頻道
4. 複製 Webhook URL

#### 設置郵件通知 (msmtp)

**重要**：需要配置 `.msmtprc` 文件來啟用郵件通知。

1. 複製示例配置：
```bash
cp msmtprc.example .msmtprc
```

2. 編輯 `.msmtprc`，設置您的 SMTP 服務器：
```conf
account default
host smtp.gmail.com
port 587
from your-email@gmail.com
user your-email@gmail.com
password your-app-password  # Gmail 需要使用應用專用密碼
```

3. 設置安全權限：
```bash
chmod 600 .msmtprc
```

4. 在 `config.yaml` 中啟用郵件通知：
```yaml
notifications:
  email:
    enabled: true
    recipients:
      - "team@example.com"
```

詳細配置請參考 [docs/setup/MSMTP_SETUP.md](docs/setup/MSMTP_SETUP.md)。

### 2. 監控配置 (config.yaml)

```yaml
# PR 監控配置（定時任務）
monitor:
  check_interval: 300  # 檢查間隔（秒）

  repositories:
    - owner: "Intrising"
      all: true  # 監控整個組織的所有 repositories
      branches: []  # 空列表 = 監控所有分支

  pr_states:
    - open

  alerts:
    open_duration_hours: 24  # PR 開啟超過 24 小時警報
    no_reviewer: true
    has_conflicts: true
    ci_failed: true

# PR 自動審查配置（Webhook 驅動）
review:
  triggers:
    - opened
    - synchronize
    - reopened

  skip_draft: true  # 跳過 draft PR
  auto_label: true  # 自動添加 "auto-reviewed" 標籤

  focus_areas:
    - "代碼質量和可讀性"
    - "潛在的 bug 和錯誤處理"
    - "性能問題和優化建議"
    - "安全漏洞和最佳實踐"
    - "測試覆蓋率"

  language: "zh-TW"

# Issue 自動複製配置（Webhook 驅動）
issue_copy:
  enabled: true
  source_repo: "Intrising/test-Lantech"  # 來源 repository

  triggers:
    - opened
    - labeled

  # Label 到目標 repository 的映射
  label_to_repo:
    "project: viewer-box": "Intrising/QA-Viewer"
    "project: os3": "Intrising/QA-Switch-OS3OS4"
    "project: os4": "Intrising/QA-Switch-OS3OS4"
    "project: os5": "Intrising/QA-Switch-OS5"
    "test": "Intrising/test-switch"

  default_target_repo: "Intrising/test-switch"  # 默認目標

  add_source_reference: true  # 在新 issue 中標註來源
  copy_labels: true           # 複製 labels
  reupload_images: false      # 保留原始圖片 URL
  add_copy_comment: false     # 在原 issue 添加複製通知

# 通知配置
notifications:
  slack:
    enabled: true

  email:
    enabled: true
    recipients:
      - "khkh@intrising.com.tw"
    include_pr_author: true
    user_email_mapping:
      IS-KH: "khkh@intrising.com.tw"
      # ... 其他用戶映射

# 日誌配置
logging:
  level: INFO
  format: json
  file: /var/log/github-monitor/app.log
```

### 3. Docker Compose 配置

專案位於 `docker/` 目錄下，提供多種配置文件：

- `docker-compose.yml` - 基礎配置
- `docker-compose.dev.yml` - 開發環境
- `docker-compose.prod.yml` - 生產環境
- `docker-compose.pr-reviewer.yml` - **PR Reviewer 服務（推薦使用）**
- `docker-compose.reviewer.yml` - Reviewer 替代配置
- `docker-compose.webhook-test.yml` - Webhook 測試服務

**推薦配置**: `docker-compose.pr-reviewer.yml` - 包含完整的 PR 審查和 Issue 複製功能。

## 📦 部署指南

### 推薦部署方式（PR Reviewer + Issue Copier）

```bash
# 1. 確保環境變數和配置都已設定
cd intrising_workspace_monitor

# 2. 創建必要的 Docker volumes
docker volume create github_pr_monitor_pr-reviewer-logs
docker volume create github_pr_monitor_pr-reviewer-db

# 3. 啟動服務
cd docker
docker-compose -f docker-compose.pr-reviewer.yml up -d

# 4. 檢查服務狀態
docker-compose -f docker-compose.pr-reviewer.yml ps

# 5. 查看日誌
docker-compose -f docker-compose.pr-reviewer.yml logs -f
```

**服務包含**:
- PR 自動審查（使用 Codex CLI）
- Issue 自動複製
- 評論同步
- Web UI 和 API 端點

### 使用 Makefile 部署

```bash
# 從 build/ 目錄使用 Makefile
cd build

# 啟動服務
make -f Makefile.reviewer start

# 查看狀態
make -f Makefile.reviewer status

# 查看日誌
make -f Makefile.reviewer logs

# 停止服務
make -f Makefile.reviewer stop

# 重啟服務
make -f Makefile.reviewer restart
```

### 開發環境部署

```bash
# 使用開發配置（更多調試信息）
cd docker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

開發環境特性：
- 調試日誌級別 (DEBUG)
- 源代碼掛載（支持熱重載）
- 無資源限制
- 更詳細的錯誤信息

### Docker Swarm 部署

對於高可用部署，可以使用 Docker Swarm：

```bash
# 初始化 Swarm
docker swarm init

# 部署服務
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml github-monitor

# 擴展服務
docker service scale github-monitor_github-monitor=3

# 查看服務
docker service ls
docker service ps github-monitor_github-monitor
```

### Kubernetes 部署

生成 Kubernetes 清單：

```bash
# 使用 kompose 轉換
kompose convert -f docker-compose.yml -f docker-compose.prod.yml

# 部署到 K8s
kubectl apply -f github-monitor-deployment.yaml
kubectl apply -f github-monitor-service.yaml
```

## 🛠️ 運維管理

### 常用命令

```bash
# 查看所有可用命令
make help

# 服務管理
make start          # 啟動（生產）
make start-dev      # 啟動（開發）
make stop           # 停止
make restart        # 重啟
make status         # 狀態

# 日誌和監控
make logs           # 查看日誌
make health         # 健康檢查
make ps             # 容器列表
make top            # 進程列表

# 維護操作
make update         # 更新服務
make backup         # 備份配置
make cleanup        # 清理資源
make shell          # 進入容器
```

### 日誌管理

```bash
# 實時查看日誌
docker-compose logs -f github-monitor

# 查看最近 100 行日誌
docker-compose logs --tail=100 github-monitor

# 導出日誌
docker-compose logs --no-color github-monitor > github-monitor.log

# 清理日誌
docker-compose down
rm -rf logs/*
docker-compose up -d
```

### 備份和恢復

```bash
# 備份配置
make backup

# 手動備份
mkdir -p backups/$(date +%Y%m%d)
cp .env config.yaml backups/$(date +%Y%m%d)/

# 恢復配置
cp backups/20240315/.env .
cp backups/20240315/config.yaml .
make restart
```

### 更新和升級

```bash
# 方法 1：使用 make
make update

# 方法 2：手動更新
git pull
docker-compose build
docker-compose up -d

# 方法 3：使用腳本
./deploy.sh update prod
```

### 監控和告警

#### 查看資源使用

```bash
# 實時資源監控
docker stats github-monitor

# 查看容器詳情
docker inspect github-monitor
```

#### 整合 Prometheus

在 `docker-compose.yml` 中添加：

```yaml
services:
  github-monitor:
    labels:
      - "prometheus.scrape=true"
      - "prometheus.port=8080"
```

#### 整合 Grafana

使用 Docker 日誌驅動：

```yaml
logging:
  driver: "loki"
  options:
    loki-url: "http://loki:3100/loki/api/v1/push"
```

## 🔍 故障排查

### 常見問題

#### 1. 容器無法啟動

```bash
# 檢查日誌
docker logs pr-reviewer

# 常見原因：
# - .private/.env 文件缺失或配置錯誤
# - GITHUB_TOKEN 無效
# - config.yaml 格式錯誤
# - Codex CLI 認證失敗
# - Docker volumes 未創建

# 解決方法：
# 檢查環境變數
cat .private/.env

# 驗證 GitHub Token
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# 檢查 Codex 認證
docker exec pr-reviewer codex --help

# 重新創建 volumes
docker volume create github_pr_monitor_pr-reviewer-logs
docker volume create github_pr_monitor_pr-reviewer-db

# 重啟服務
cd docker
docker-compose -f docker-compose.pr-reviewer.yml restart
```

#### 2. Webhook 未收到或處理失敗

```bash
# 檢查 webhook 日誌
docker logs -f pr-reviewer | grep webhook

# 測試 webhook 端點
curl http://localhost:8080/health

# 檢查 GitHub webhook 設定
# 在 GitHub Repository Settings → Webhooks 中查看 Recent Deliveries

# 手動測試 webhook（使用測試腳本）
cd scripts
python test_webhook.py
```

#### 3. PR 審查未執行

```bash
# 檢查 Codex CLI 是否可用
docker exec pr-reviewer codex --help

# 查看審查任務狀態
curl http://localhost:8080/api/tasks

# 檢查日誌中的錯誤
docker logs pr-reviewer | grep -i "error\|failed"

# 驗證 config.yaml 中 review 配置
cat config.yaml | grep -A 10 "^review:"
```

#### 4. Issue 未自動複製

```bash
# 檢查 Issue Copier 是否啟用
cat config.yaml | grep -A 2 "^issue_copy:"

# 查看複製記錄
curl http://localhost:8080/api/issue-copies

# 檢查來源 repository 設定
cat config.yaml | grep "source_repo"

# 查看資料庫中的記錄
docker exec pr-reviewer sqlite3 /var/lib/github-monitor/tasks.db \
  "SELECT * FROM issue_copies ORDER BY created_at DESC LIMIT 10;"
```

#### 5. GitHub API 速率限制

```bash
# 檢查剩餘配額
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/rate_limit

# 解決方法：
# - 增加 CHECK_INTERVAL
# - 使用企業級 GitHub Token
# - 減少監控的儲存庫數量
```

#### 6. Slack 通知未收到

```bash
# 測試 Webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message"}' \
  YOUR_SLACK_WEBHOOK_URL

# 檢查配置
docker exec github-monitor env | grep SLACK

# 查看錯誤日誌
docker-compose logs github-monitor | grep -i slack
```

#### 4. 記憶體不足

```bash
# 查看記憶體使用
docker stats github-monitor

# 調整限制（docker-compose.yml）
deploy:
  resources:
    limits:
      memory: 1G  # 增加限制
```

### 調試模式

```bash
# 啟用 DEBUG 日誌
echo "LOG_LEVEL=DEBUG" >> .env
make restart

# 進入容器調試
make shell

# 手動執行檢查
docker exec github-monitor python pr_monitor.py
```

### 健康檢查失敗

```bash
# 執行健康檢查
make health

# 查看詳細信息
docker exec github-monitor python healthcheck.py

# 檢查 Docker 健康狀態
docker inspect --format='{{.State.Health.Status}}' github-monitor
```

## 🔒 安全最佳實踐

### 1. 密鑰管理

**不要將密鑰提交到 Git**

```bash
# 使用 .gitignore
echo ".env" >> .gitignore
echo "*.backup" >> .gitignore

# 使用環境變數或密鑰管理工具
# - Docker Secrets
# - HashiCorp Vault
# - AWS Secrets Manager
```

**使用 Docker Secrets（推薦）**

```bash
# 創建 secret
echo "ghp_your_token" | docker secret create github_token -

# 在 docker-compose.yml 中使用
services:
  github-monitor:
    secrets:
      - github_token
    environment:
      GITHUB_TOKEN_FILE: /run/secrets/github_token

secrets:
  github_token:
    external: true
```

### 2. 容器安全

```yaml
# 最佳實踐配置
services:
  github-monitor:
    # 非 root 用戶
    user: "1000:1000"

    # 只讀文件系統
    read_only: true

    # 安全選項
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined

    # 限制能力
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

### 3. 網絡隔離

```yaml
networks:
  github-monitor-network:
    driver: bridge
    internal: true  # 僅內部通信
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### 4. 定期更新

```bash
# 定期更新基礎映像
docker pull python:3.11-slim

# 重建映像
make build

# 掃描漏洞
docker scan github-monitor:latest
```

### 5. 日誌安全

```bash
# 不要記錄敏感信息
# 配置日誌輪轉
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 📊 性能優化

### 1. 減少 API 調用

```yaml
monitor:
  check_interval: 600  # 增加間隔到 10 分鐘
```

### 2. 使用快取

```python
# 在 pr_monitor.py 中添加快取邏輯
from functools import lru_cache

@lru_cache(maxsize=128)
def get_repository(full_name):
    return self.github.get_repo(full_name)
```

### 3. 並行處理

```python
# 使用多線程處理多個儲存庫
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(self.monitor_repository, repositories)
```

## 📝 開發指南

### 本地開發

```bash
# 安裝依賴
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 運行測試
pytest tests/

# 代碼檢查
pylint pr_monitor.py
black pr_monitor.py

# 本地運行
python pr_monitor.py
```

### 添加新功能

1. 在 `pr_monitor.py` 中添加功能
2. 更新 `config.yaml` 配置選項
3. 更新文檔
4. 添加測試
5. 提交 PR

### 貢獻指南

歡迎貢獻！請：

1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📄 授權

MIT License - 詳見 [LICENSE](LICENSE) 文件

## 🤝 支持

- 🐛 Issues: [GitHub Issues](https://github.com/Intrising/intrising_workspace_monitor/issues)
- 📧 Email: khkh@intrising.com.tw
- 📚 內部文檔：[docs/](docs/) 目錄

## 📚 相關資源

### 專案文檔
- [快速開始指南](docs/QUICKSTART.md)
- [功能說明](docs/FEATURES.md)
- [Issue Copier 詳細文檔](docs/ISSUE_COPIER.md)
- [PR Reviewer 文檔](docs/migration/README_REVIEWER.md)
- [Webhook 設定指南](docs/setup/WEBHOOK_SETUP.md)
- [GitHub Webhook 配置](docs/setup/GITHUB_WEBHOOK_CONFIG.md)

### 外部資源
- [GitHub API 文檔](https://docs.github.com/en/rest)
- [GitHub Webhooks 文檔](https://docs.github.com/en/webhooks)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [Docker 最佳實踐](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Compose 文檔](https://docs.docker.com/compose/)

### 工具腳本
- `scripts/test_webhook.py` - 測試 webhook 接收
- `scripts/test_issue_copier.py` - 測試 issue 複製功能
- `scripts/trigger_issue_copy.py` - 手動觸發 issue 複製
- `scripts/sync_missing_copy_records.py` - 同步遺失的複製記錄
- `scripts/setup_claude_auth.sh` - 設定 Claude/Codex 認證

---

**Made with 🤖 by Intrising Team**
