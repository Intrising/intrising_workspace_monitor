# 專案結構說明

本文檔說明 GitHub Monitor 專案的文件結構和組織方式。

## 📁 文件結構

```
github_monitor/
├── .dockerignore           # Docker 構建排除文件
├── .env.example            # 環境變數範例文件
├── .gitignore             # Git 忽略文件
├── Dockerfile             # Docker 多階段構建文件
├── Makefile               # 便捷命令集合
├── README.md              # 主要文檔
├── QUICKSTART.md          # 快速開始指南
├── DEPLOYMENT.md          # 企業級部署指南
├── PROJECT_STRUCTURE.md   # 專案結構說明（本文件）
├── config.yaml            # 監控配置文件
├── deploy.sh              # 部署管理腳本
├── docker-compose.yml     # Docker Compose 基礎配置
├── docker-compose.dev.yml # 開發環境配置
├── docker-compose.prod.yml# 生產環境配置
├── healthcheck.py         # 健康檢查腳本
├── pr_monitor.py          # 主程式
├── requirements.txt       # Python 依賴
└── logs/                  # 日誌目錄（運行時創建）
```

## 📄 核心文件說明

### 配置文件

#### `.env.example`
環境變數範例文件，包含所有必需的配置項：
- GitHub API Token
- Slack Webhook URL
- 應用設置（日誌級別、檢查間隔等）

**使用方式**：
```bash
cp .env.example .env
vim .env  # 填入實際配置
```

#### `config.yaml`
監控規則配置文件，定義：
- 要監控的儲存庫列表
- 檢查間隔
- 警報條件（開啟時間、審查者、衝突、CI 狀態）
- 通知設置
- 日誌配置

**關鍵配置項**：
```yaml
monitor:
  repositories:      # 監控的儲存庫
  alerts:           # 警報條件
notifications:      # 通知設置
logging:           # 日誌配置
```

### 應用程式

#### `pr_monitor.py`
主程式文件，包含：
- `PRMonitor` 類：核心監控邏輯
- GitHub API 整合
- Slack 通知功能
- 定時任務調度
- 日誌系統

**主要功能**：
- `check_pr_issues()`: 檢查 PR 問題
- `send_slack_notification()`: 發送 Slack 通知
- `monitor_repository()`: 監控單個儲存庫
- `run_check()`: 執行完整檢查循環

#### `healthcheck.py`
健康檢查腳本，用於：
- 檢查進程運行狀態
- 驗證日誌活動
- 測試 GitHub API 連接
- 檢查 API 配額

**使用方式**：
```bash
python healthcheck.py
# 或在容器中
docker exec github-monitor python healthcheck.py
```

### Docker 相關

#### `Dockerfile`
多階段構建配置：
- **階段 1 (builder)**: 編譯和依賴安裝
- **階段 2 (runtime)**: 最小化運行環境

**優化特性**：
- 分層快取優化
- 最小化映像大小
- 非 root 用戶運行
- 安全加固

#### `docker-compose.yml`
基礎 Docker Compose 配置：
- 容器定義
- 資源限制
- 健康檢查
- 卷掛載
- 網絡配置

#### `docker-compose.dev.yml`
開發環境覆蓋配置：
- DEBUG 日誌級別
- 源代碼掛載（熱重載）
- 較低資源限制
- 無安全限制

#### `docker-compose.prod.yml`
生產環境覆蓋配置：
- 嚴格資源限制
- 高可用設置
- 滾動更新策略
- 日誌整合

### 部署工具

#### `deploy.sh`
Bash 部署腳本，提供：
- 前置檢查
- 映像構建
- 服務管理（啟動、停止、重啟）
- 日誌查看
- 狀態監控
- 備份和清理

**命令示例**：
```bash
./deploy.sh check      # 檢查環境
./deploy.sh build      # 構建映像
./deploy.sh start prod # 啟動生產環境
./deploy.sh logs       # 查看日誌
```

#### `Makefile`
Make 任務定義，簡化常用操作：
- 服務生命週期管理
- 開發工具（測試、檢查、格式化）
- 維護任務（備份、清理）

**命令示例**：
```bash
make help          # 顯示所有命令
make deploy        # 一鍵部署
make logs          # 查看日誌
make status        # 查看狀態
```

### 文檔

#### `README.md`
主要文檔，包含：
- 功能介紹
- 快速開始
- 詳細配置
- 部署指南
- 運維管理
- 故障排查
- 安全最佳實踐

#### `QUICKSTART.md`
5 分鐘快速開始指南：
- 最小化配置步驟
- 常見問題快速解決
- 基本使用命令

#### `DEPLOYMENT.md`
企業級部署文檔：
- 生產環境部署
- 高可用配置（Docker Swarm、Kubernetes）
- 雲端部署（AWS、GCP、Azure）
- CI/CD 整合
- 監控和告警

## 🔧 開發工作流

### 本地開發

```bash
# 1. 設置開發環境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
vim .env

# 3. 本地運行
python pr_monitor.py

# 4. 測試 Docker
make start-dev
make logs
```

### Docker 開發

```bash
# 構建
make build

# 啟動開發環境
make start-dev

# 查看日誌
make logs

# 進入容器調試
make shell
```

### 代碼修改流程

```bash
# 1. 修改代碼
vim pr_monitor.py

# 2. 測試（如果有測試文件）
pytest tests/

# 3. 重建並重啟
make restart-dev

# 4. 驗證
make logs
make health
```

## 📦 依賴管理

### Python 依賴 (`requirements.txt`)

```
requests        # HTTP 請求
PyGithub        # GitHub API 客戶端
python-dotenv   # 環境變數管理
pyyaml          # YAML 配置解析
schedule        # 任務調度
slack-sdk       # Slack 整合
```

### 添加新依賴

```bash
# 1. 安裝新包
pip install package-name

# 2. 更新 requirements.txt
pip freeze > requirements.txt

# 3. 重建 Docker 映像
make build
```

## 🔒 安全文件

### 敏感文件（不應提交到 Git）

- `.env` - 包含密鑰和 token
- `logs/` - 可能包含敏感日誌
- `backups/` - 配置備份

### 已受保護（在 `.gitignore` 中）

```gitignore
.env
.env.*
*.log
logs/
backups/
__pycache__/
*.pyc
.DS_Store
```

## 📊 運行時目錄

### `logs/`
日誌文件存儲目錄：
- 自動創建
- 通過 Docker 卷持久化
- 可配置輪轉策略

### `backups/`
配置備份目錄：
- 使用 `make backup` 創建
- 按日期組織
- 包含 `.env` 和 `config.yaml`

## 🚀 部署變體

### 最小部署
```
├── .env
├── config.yaml
├── docker-compose.yml
└── Dockerfile
```

### 開發部署
```
├── .env
├── config.yaml
├── docker-compose.yml
├── docker-compose.dev.yml
├── Dockerfile
└── pr_monitor.py (掛載)
```

### 生產部署
```
├── .env (加密存儲)
├── config.yaml
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── deploy.sh
├── Makefile
└── 監控整合
```

## 📈 擴展點

### 添加新的通知渠道

1. 在 `pr_monitor.py` 中添加新方法
2. 在 `config.yaml` 中添加配置
3. 在 `.env.example` 中添加必需變數

### 添加新的檢查規則

1. 在 `check_pr_issues()` 中添加邏輯
2. 在 `config.yaml` 的 `alerts` 中添加配置
3. 更新文檔

### 添加 Web 界面

1. 添加 Flask/FastAPI 依賴
2. 創建 API 端點
3. 在 Dockerfile 中暴露端口
4. 更新 docker-compose.yml

## 🛠️ 維護任務

### 定期檢查

```bash
# 每日
make status
make health

# 每週
make backup
docker system prune -f

# 每月
make update
檢查依賴更新
```

### 更新依賴

```bash
# 檢查過期包
pip list --outdated

# 更新特定包
pip install --upgrade package-name

# 重建映像
make build
```

### 清理空間

```bash
# 清理未使用的 Docker 資源
docker system prune -a --volumes

# 清理日誌
rm -rf logs/*

# 清理舊備份
find backups/ -mtime +30 -delete
```

## 📞 支持

遇到問題？

1. 查看 `README.md` 故障排查章節
2. 執行 `make health` 診斷
3. 查看日誌 `make logs`
4. 提交 GitHub Issue

---

**維護者**: DevOps Team
**最後更新**: 2024-10-15
