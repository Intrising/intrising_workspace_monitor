# GitHub Monitor - 企業級 Docker 部署指南

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

企業級 GitHub Pull Request 監控工具，支持自動檢測 PR 問題並通過 Slack 發送警報通知。

## 📋 目錄

- [功能特性](#功能特性)
- [系統架構](#系統架構)
- [快速開始](#快速開始)
- [詳細配置](#詳細配置)
- [部署指南](#部署指南)
- [運維管理](#運維管理)
- [故障排查](#故障排查)
- [安全最佳實踐](#安全最佳實踐)

## ✨ 功能特性

### 核心功能
- ✅ **自動 PR 監控**：定期檢查指定儲存庫的 Pull Requests
- ✅ **多種警報條件**：
  - PR 開啟時間過長
  - 缺少審查者
  - 存在合併衝突
  - CI/CD 檢查失敗
- ✅ **Slack 整合**：實時推送問題通知到 Slack
- ✅ **郵件通知**：使用 msmtp 發送郵件警報
- ✅ **多儲存庫支持**：同時監控多個 GitHub 儲存庫
- ✅ **分支過濾**：只監控指定的分支

### 企業級特性
- 🐳 **Docker 容器化**：完整的 Docker 支持
- 🔒 **安全加固**：非 root 用戶運行、只讀文件系統
- 📊 **健康檢查**：內建健康檢查機制
- 📝 **結構化日誌**：支持 JSON 格式日誌
- 🔄 **資源限制**：CPU 和記憶體使用限制
- 🛡️ **多環境支持**：開發、生產環境分離

## 🏗️ 系統架構

```
┌─────────────────────────────────────────┐
│         GitHub Monitor               │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐      ┌──────────────┐   │
│  │ Monitor  │─────▶│ GitHub API   │   │
│  │ Service  │      └──────────────┘   │
│  └────┬─────┘                          │
│       │                                 │
│       ├─────▶ ┌──────────────┐        │
│       │       │ Issue Check  │        │
│       │       └──────────────┘        │
│       │                                 │
│       └─────▶ ┌──────────────┐        │
│               │ Slack Alert  │        │
│               └──────────────┘        │
│                                         │
└─────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌──────────┐        ┌──────────┐
   │  Logs    │        │  Slack   │
   └──────────┘        └──────────┘
```

## 🚀 快速開始

### 前置需求

- Docker >= 20.10
- Docker Compose >= 2.0
- GitHub Personal Access Token
- Slack Webhook URL（可選）

### 5 分鐘快速部署

```bash
# 1. 克隆專案
git clone <repository-url>
cd github_monitor

# 2. 初始化配置
make init

# 3. 編輯環境變數
cp .env.example .env
vim .env  # 填入 GITHUB_TOKEN 和 SLACK_WEBHOOK_URL

# 4. 配置郵件通知（可選）
cp msmtprc.example .msmtprc
vim .msmtprc  # 設置 SMTP 服務器和認證信息
chmod 600 .msmtprc  # 設置安全權限

# 5. 編輯監控配置
vim config.yaml  # 設置要監控的儲存庫和通知接收者

# 6. 一鍵部署
make deploy
```

就這麼簡單！服務已經啟動並開始監控。

### 驗證部署

```bash
# 查看服務狀態
make status

# 查看實時日誌
make logs

# 執行健康檢查
make health
```

## ⚙️ 詳細配置

### 1. 環境變數配置 (.env)

```bash
# GitHub 配置
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_API_URL=https://api.github.com

# Slack 配置
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#pr-alerts

# 郵件配置（使用 msmtp）
EMAIL_FROM=devops@example.com
MSMTP_CONFIG=/home/appuser/.msmtprc

# 應用設置
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
CHECK_INTERVAL=300      # 檢查間隔（秒）
TZ=Asia/Taipei         # 時區
```

#### 獲取 GitHub Token

1. 訪問 GitHub Settings → Developer settings → Personal access tokens
2. 生成新 token，需要以下權限：
   - `repo` (完整儲存庫訪問)
   - `read:org` (讀取組織資訊)

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

詳細配置請參考 [MSMTP_SETUP.md](MSMTP_SETUP.md)。

### 2. 監控配置 (config.yaml)

```yaml
monitor:
  # 檢查間隔（秒）
  check_interval: 300

  # 監控的儲存庫
  repositories:
    - owner: "your-org"
      repo: "your-repo"
      branches:
        - main
        - develop

  # 警報條件
  alerts:
    open_duration_hours: 24    # PR 開啟超過 24 小時警報
    no_reviewer: true          # 無審查者警報
    has_conflicts: true        # 合併衝突警報
    ci_failed: true           # CI 失敗警報

notifications:
  slack:
    enabled: true

logging:
  level: INFO
  format: json
  file: /var/log/github-monitor/app.log
```

### 3. Docker Compose 配置

專案提供三種配置文件：

- `docker-compose.yml` - 基礎配置
- `docker-compose.dev.yml` - 開發環境
- `docker-compose.prod.yml` - 生產環境

## 📦 部署指南

### 開發環境部署

```bash
# 使用 Makefile
make start-dev

# 或使用 deploy.sh
./deploy.sh start dev

# 或使用 docker-compose
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

開發環境特性：
- 調試日誌級別 (DEBUG)
- 更短的檢查間隔 (60秒)
- 源代碼掛載（支持熱重載）
- 無資源限制

### 生產環境部署

```bash
# 使用 Makefile（推薦）
make deploy

# 或使用 deploy.sh
./deploy.sh check
./deploy.sh build
./deploy.sh start prod

# 或使用 docker-compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

生產環境特性：
- 嚴格的資源限制
- 高可用配置
- 自動重啟策略
- 滾動更新支持

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
docker-compose logs github-monitor

# 常見原因：
# - .env 文件缺失或配置錯誤
# - GitHub Token 無效
# - config.yaml 格式錯誤

# 解決方法：
make check          # 檢查配置
vim .env           # 修正環境變數
make restart       # 重啟服務
```

#### 2. GitHub API 速率限制

```bash
# 檢查剩餘配額
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/rate_limit

# 解決方法：
# - 增加 CHECK_INTERVAL
# - 使用企業級 GitHub Token
# - 減少監控的儲存庫數量
```

#### 3. Slack 通知未收到

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

- 📧 Email: your-team@example.com
- 💬 Slack: #github-monitor-support
- 🐛 Issues: GitHub Issues

## 📚 相關資源

- [GitHub API 文檔](https://docs.github.com/en/rest)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [Docker 最佳實踐](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Compose 文檔](https://docs.docker.com/compose/)

---

**Made with ❤️ for DevOps Teams**
