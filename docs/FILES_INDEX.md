# 📁 文件索引

本文檔提供專案中所有文件的快速參考索引。

## 📂 文件列表

### 📘 文檔文件（Documentation）

| 文件名 | 大小 | 說明 |
|--------|------|------|
| **README.md** | 13K | 主要文檔，包含完整的使用說明、配置、部署和故障排查 |
| **QUICKSTART.md** | 2.9K | 5 分鐘快速開始指南，適合新用戶 |
| **DEPLOYMENT.md** | 12K | 企業級部署指南，涵蓋多種部署方案 |
| **PROJECT_STRUCTURE.md** | 7.6K | 專案結構詳細說明，包括開發工作流 |
| **FEATURES.md** | 4.5K | 功能特性清單和未來路線圖 |
| **SUMMARY.md** | 7.8K | 專案完成總結和成果展示 |
| **LICENSE** | 1.1K | MIT 開源授權 |

### 🐍 Python 應用程式

| 文件名 | 大小 | 說明 |
|--------|------|------|
| **pr_monitor.py** | 11K | 主監控程式，包含所有核心邏輯 |
| **healthcheck.py** | 3.4K | 健康檢查腳本，用於容器監控 |
| **requirements.txt** | 102B | Python 依賴清單 |

### 🐳 Docker 配置

| 文件名 | 大小 | 說明 |
|--------|------|------|
| **Dockerfile** | 1.8K | 多階段構建配置，優化映像大小 |
| **docker-compose.yml** | 1.4K | 基礎 Docker Compose 配置 |
| **docker-compose.dev.yml** | 993B | 開發環境覆蓋配置 |
| **docker-compose.prod.yml** | 1.7K | 生產環境覆蓋配置 |
| **.dockerignore** | 465B | Docker 構建排除文件 |

### ⚙️ 配置文件

| 文件名 | 大小 | 說明 |
|--------|------|------|
| **config.yaml** | 1.0K | 監控規則和警報配置 |
| **.env.example** | 419B | 環境變數範例文件 |
| **.gitignore** | 519B | Git 忽略規則 |

### 🔧 部署工具

| 文件名 | 大小 | 說明 |
|--------|------|------|
| **deploy.sh** | 5.7K | Bash 部署管理腳本（可執行） |
| **Makefile** | 2.8K | Make 任務定義，簡化常用命令 |

## 📖 閱讀順序建議

### 新用戶
1. **QUICKSTART.md** - 快速開始
2. **README.md** - 完整了解
3. **config.yaml** + **.env.example** - 配置設定

### 部署人員
1. **QUICKSTART.md** - 基礎部署
2. **DEPLOYMENT.md** - 企業部署
3. **deploy.sh** + **Makefile** - 部署工具

### 開發者
1. **PROJECT_STRUCTURE.md** - 專案架構
2. **pr_monitor.py** - 核心代碼
3. **Dockerfile** - 容器配置
4. **FEATURES.md** - 功能規劃

### 運維人員
1. **README.md** § 運維管理
2. **deploy.sh** - 管理腳本
3. **healthcheck.py** - 健康檢查
4. **DEPLOYMENT.md** § 監控告警

## 🎯 核心文件說明

### README.md
**主要文檔**，包含：
- 功能特性介紹
- 系統架構說明
- 快速開始指南（5分鐘）
- 詳細配置說明
- 部署指南
- 運維管理
- 故障排查
- 安全最佳實踐

**何時閱讀**: 需要全面了解專案時

### QUICKSTART.md
**快速開始指南**，包含：
- 環境準備
- GitHub Token 獲取
- Slack Webhook 設置
- 配置步驟
- 啟動服務
- 驗證運行
- 快速故障排查

**何時閱讀**: 第一次使用，想快速部署時

### DEPLOYMENT.md
**企業級部署文檔**，包含：
- 生產環境部署
- 高可用配置（Docker Swarm, Kubernetes）
- 雲端部署（AWS, GCP, Azure）
- CI/CD 整合
- Prometheus + Grafana 監控
- ELK Stack 日誌收集

**何時閱讀**: 需要生產部署或高可用方案時

### PROJECT_STRUCTURE.md
**專案結構文檔**，包含：
- 文件結構說明
- 核心文件介紹
- 開發工作流
- 依賴管理
- 安全文件列表
- 維護任務

**何時閱讀**: 需要了解專案架構或進行開發時

### FEATURES.md
**功能特性清單**，包含：
- 已實現功能（35+）
- 計劃功能（20+）
- 功能路線圖
- 技術棧
- 性能指標
- 安全特性

**何時閱讀**: 需要了解功能範圍或規劃時

### SUMMARY.md
**專案總結文檔**，包含：
- 專案概述
- 交付內容
- 技術架構
- 專案統計
- 使用場景
- 部署選項
- 成果展示

**何時閱讀**: 需要快速了解專案全貌時

## 🛠️ 工具文件說明

### deploy.sh
**Bash 部署腳本**，提供命令：
- `check` - 檢查前置條件
- `build` - 建構 Docker 映像
- `start` - 啟動服務
- `stop` - 停止服務
- `restart` - 重啟服務
- `logs` - 查看日誌
- `status` - 查看狀態
- `shell` - 進入容器
- `update` - 更新服務
- `backup` - 備份配置
- `cleanup` - 清理資源

**使用**: `./deploy.sh <command>`

### Makefile
**Make 任務定義**，提供命令：
- `make help` - 顯示所有命令
- `make deploy` - 一鍵部署
- `make start` - 啟動（生產）
- `make start-dev` - 啟動（開發）
- `make stop` - 停止服務
- `make restart` - 重啟服務
- `make logs` - 查看日誌
- `make status` - 查看狀態
- `make health` - 健康檢查
- `make shell` - 進入容器
- `make backup` - 備份配置
- `make cleanup` - 清理資源

**使用**: `make <command>`

## 📋 配置文件說明

### .env.example
**環境變數範例**，包含：
- `GITHUB_TOKEN` - GitHub API Token
- `SLACK_WEBHOOK_URL` - Slack Webhook URL
- `SLACK_CHANNEL` - Slack 頻道
- `LOG_LEVEL` - 日誌級別
- `CHECK_INTERVAL` - 檢查間隔
- `TZ` - 時區設定

**使用**: 
```bash
cp .env.example .env
vim .env  # 填入實際配置
```

### config.yaml
**監控配置文件**，包含：
- 檢查間隔
- 監控的儲存庫列表
- 警報條件設定
- 通知配置
- 日誌配置

**修改後**: 需重啟服務 (`make restart`)

## 🔍 快速查找

### 需要配置？
→ `.env.example`, `config.yaml`

### 需要部署？
→ `QUICKSTART.md`, `deploy.sh`, `Makefile`

### 需要開發？
→ `PROJECT_STRUCTURE.md`, `pr_monitor.py`

### 需要故障排查？
→ `README.md` § 故障排查, `healthcheck.py`

### 需要企業部署？
→ `DEPLOYMENT.md`

### 需要了解功能？
→ `FEATURES.md`, `README.md`

## 📊 文件統計

- **總文件數**: 20
- **文檔文件**: 7 (42.5K)
- **代碼文件**: 3 (14.5K)
- **配置文件**: 7 (5.5K)
- **工具腳本**: 2 (8.5K)
- **授權文件**: 1 (1.1K)

**總大小**: ~72KB

---

**最後更新**: 2024-10-15
