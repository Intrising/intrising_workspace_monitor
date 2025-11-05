# PR Monitor 資料庫持久化設定說明

## 概述

本專案已成功實現資料庫持久化功能，使用 SQLite 資料庫存儲 PR 審查任務記錄。即使 Docker 容器重啟，所有歷史記錄都會被保留。

## 系統架構

### 資料存儲方案
- **資料庫類型**: SQLite
- **資料庫文件路徑**: `/var/lib/github-monitor/tasks.db`
- **持久化方式**: Docker Named Volume (`pr-reviewer-db`)

### 核心組件

1. **database.py** (`src/database.py`)
   - 提供資料庫操作的完整封裝
   - 包含任務的 CRUD 操作（創建、讀取、更新、刪除）
   - 支援任務搜索和統計功能
   - 自動創建資料表和索引

2. **pr_reviewer.py** (已修改)
   - 從內存存儲改為使用資料庫
   - 所有任務狀態更新都會保存到資料庫
   - 提供 RESTful API 查詢任務記錄

3. **Docker Volume** (`pr-reviewer-db`)
   - 持久化存儲資料庫文件
   - 容器重啟後資料不會丟失

## 資料表結構

### review_tasks 表

| 欄位名稱 | 類型 | 說明 |
|---------|------|------|
| task_id | TEXT | 主鍵，格式：`repo_name#pr_number` |
| pr_number | INTEGER | PR 編號 |
| repo | TEXT | 儲存庫名稱 |
| pr_title | TEXT | PR 標題 |
| pr_author | TEXT | PR 作者 |
| pr_url | TEXT | PR 連結 |
| status | TEXT | 任務狀態 (queued/processing/completed/failed) |
| progress | INTEGER | 進度百分比 (0-100) |
| message | TEXT | 狀態訊息 |
| created_at | TEXT | 創建時間 (ISO 8601 格式) |
| updated_at | TEXT | 更新時間 (ISO 8601 格式) |
| completed_at | TEXT | 完成時間 (可為空) |
| error_message | TEXT | 錯誤訊息 (可為空) |
| review_content | TEXT | 審查內容 (可為空) |

### 索引
- `idx_status`: 加速按狀態查詢
- `idx_created_at`: 加速按時間排序
- `idx_repo_pr`: 加速按儲存庫和 PR 編號查詢

## API 端點

### 獲取所有任務
```bash
GET http://localhost:8080/api/tasks
```

回應範例：
```json
{
  "total": 10,
  "stats": {
    "queued": 2,
    "processing": 1,
    "completed": 6,
    "failed": 1
  },
  "tasks": [...]
}
```

### 獲取單個任務
```bash
GET http://localhost:8080/api/task/<task_id>
```

### 網頁監控界面
```bash
http://localhost:8080/
```

## 使用說明

### 啟動服務

```bash
# 停止舊容器（如果存在）
docker compose -f docker-compose.pr-reviewer.yml down

# 重新建置映像
docker compose -f docker-compose.pr-reviewer.yml build

# 啟動服務
docker compose -f docker-compose.pr-reviewer.yml up -d
```

### 查看任務記錄

1. **通過瀏覽器**：訪問 http://localhost:8080/

2. **通過 API**：
```bash
curl http://localhost:8080/api/tasks | python3 -m json.tool
```

### 檢查資料庫

```bash
# 查看資料庫文件
docker exec pr-reviewer ls -la /var/lib/github-monitor/

# 使用 Python 查詢資料庫
docker exec pr-reviewer python3 -c "
import sqlite3
conn = sqlite3.connect('/var/lib/github-monitor/tasks.db')
cursor = conn.cursor()
cursor.execute('SELECT task_id, pr_title, status FROM review_tasks LIMIT 10')
for row in cursor.fetchall():
    print(row)
conn.close()
"
```

### 備份資料庫

```bash
# 複製資料庫文件到主機
docker cp pr-reviewer:/var/lib/github-monitor/tasks.db ./backup-tasks.db

# 或者備份整個 volume
docker run --rm -v github_monitor_pr-reviewer-db:/source -v $(pwd):/backup \
  alpine tar -czf /backup/pr-reviewer-db-backup.tar.gz -C /source .
```

### 恢復資料庫

```bash
# 從備份恢復
docker cp ./backup-tasks.db pr-reviewer:/var/lib/github-monitor/tasks.db
docker compose -f docker-compose.pr-reviewer.yml restart pr-reviewer
```

### 清理舊資料

資料庫模組提供了清理功能：

```python
# 刪除 30 天前的已完成或失敗任務
from database import TaskDatabase
db = TaskDatabase()
deleted_count = db.delete_old_tasks(days=30)
print(f"已刪除 {deleted_count} 個舊任務")
```

## 資料持久化測試

系統已通過以下測試：

1. ✅ 插入測試資料
2. ✅ 重啟容器
3. ✅ 確認資料完整保留
4. ✅ API 正常返回歷史記錄
5. ✅ 網頁界面正常顯示

測試結果：**資料在容器重啟後完全保留，持久化功能正常運作！**

## 注意事項

1. **資料庫位置**: 資料庫文件位於 Docker Volume 中，不要直接刪除 `pr-reviewer-db` volume，否則會丟失所有歷史記錄

2. **備份建議**: 定期備份資料庫文件，特別是在重要更新前

3. **容量管理**: 定期清理舊資料，避免資料庫過大

4. **並發處理**: 資料庫使用了鎖機制，支援多執行緒安全操作

## 環境變數

可以通過環境變數自訂資料庫路徑：

```bash
DATABASE_PATH=/custom/path/tasks.db
```

在 `.env` 檔案或 `docker-compose.yml` 中設定。

## 技術細節

- **連接池**: 使用 context manager 自動管理資料庫連接
- **事務處理**: 所有寫入操作都使用事務，確保資料一致性
- **錯誤處理**: 完整的異常處理和日誌記錄
- **執行緒安全**: 使用 threading.Lock 保證並發安全

## 相關文件

- `src/database.py`: 資料庫操作模組
- `src/pr_reviewer.py`: PR 審查主程式（已整合資料庫）
- `docker/docker-compose.pr-reviewer.yml`: Docker Compose 配置（包含 volume 定義）
- `docker/Dockerfile`: Docker 映像定義（包含資料庫目錄創建）

## 升級說明

如果你從舊版本升級到此版本：

1. 舊版本的內存資料會在升級後消失（這是預期行為）
2. 升級後，所有新的任務記錄都會保存到資料庫
3. 重啟容器後，資料會完整保留

---

**建立日期**: 2025-10-18
**版本**: 1.0.0
**狀態**: ✅ 已測試並正常運作
