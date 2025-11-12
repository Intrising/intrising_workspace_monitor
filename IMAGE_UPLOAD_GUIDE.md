# 📸 自動圖片上傳功能指南

## 概述

系統現在支援自動將圖片上傳到 GitHub repository 的 `assets` 分支，完全自動化處理圖片附件，不再需要手動標記 @IS-LilithChang。

## 功能特點

### ✅ 自動化場景

1. **Issue 複製時的附件處理**
   - 當從 test-Lantech 複製 Issue 時
   - 自動下載原 Issue 中的所有圖片
   - 重新上傳到目標 repository 的 `assets` 分支
   - 更新 Issue body 中的圖片連結

2. **PR 審查時的截圖**（未來功能）
   - Claude 審查 PR 時自動上傳相關截圖
   - 架構圖、流程圖等自動管理

3. **Webhook 自動處理**（未來功能）
   - 監聽 issue_comment 事件
   - 自動處理評論中的圖片附件

### 📁 儲存結構

圖片儲存在各個 repository 的 `assets` 分支中：

```
QA-Switch-OS5/
└── assets (分支)
    └── images/
        ├── screenshot_123.png
        ├── diagram_456.jpg
        └── ...
```

### 🔗 URL 格式

上傳後的圖片使用 GitHub 的 raw URL：

```
https://github.com/Intrising/QA-Switch-OS5/blob/assets/images/screenshot_123.png?raw=true
```

這種格式的優點：
- ✅ 在 private repository 中也能正常顯示（需要登入）
- ✅ 不會過期
- ✅ 版本控制管理
- ✅ 可以手動管理和清理

## 使用方式

### Issue 複製（自動）

當您在 test-Lantech 建立帶有圖片的 Issue 時：

1. 系統自動偵測目標 repository（根據 labels）
2. 複製 Issue 到目標 repo
3. **自動下載並重新上傳所有圖片**
4. 更新 Issue body 中的圖片連結

無需任何手動操作！

### 配置選項

在 `config.yaml` 中：

```yaml
issue_copy:
  reupload_images: true  # 啟用自動圖片上傳
```

設為 `false` 會保留原始圖片 URL（不重新上傳）。

## 技術實作

### GitHubAssetUploader 模組

核心上傳器位於 `src/github_asset_uploader.py`：

```python
from github_asset_uploader import GitHubAssetUploader

# 初始化
uploader = GitHubAssetUploader(github_token, logger)

# 自動處理文本中的所有圖片
processed_text = uploader.process_text_images(
    repo_full_name="Intrising/QA-Switch-OS5",
    text=issue_body,
    issue_number=123
)
```

### 支援的圖片格式

- Markdown: `![alt](url)`
- HTML: `<img src="url">`
- 常見格式: PNG, JPG, GIF, WebP, SVG

### 智能過濾

系統會自動跳過已經在 GitHub 上的圖片：
- `github.com` 的圖片不會重複上傳
- `githubusercontent.com` 的圖片保持原樣

## 與原腳本的對比

### 原手動腳本

```bash
#!/bin/bash
# 需要手動執行
# 需要指定 repo、issue、圖片路徑
GITHUB_TOKEN="..."
OWNER="Intrising"
REPO="drone-test"
ISSUE_NUMBER="252"
IMAGE_PATH="/tmp/image.png"
```

**缺點：**
- ❌ 需要手動執行
- ❌ 需要標記 @IS-LilithChang
- ❌ 一次只能上傳一張圖片
- ❌ 需要指定很多參數

### 新自動化系統

```python
# 完全自動執行
# 在 Issue 複製時自動觸發
# 自動處理所有圖片
processed_body = process_images_in_body(
    body, source_repo, target_repo, issue_number
)
```

**優點：**
- ✅ 完全自動化
- ✅ 不需要手動標記
- ✅ 批次處理所有圖片
- ✅ 智能過濾和錯誤處理

## 故障排除

### 檢查功能是否啟用

```bash
docker logs issue-copier | grep "圖片上傳功能"
```

應該看到：`圖片上傳功能: 啟用 (上傳到 assets 分支)`

### 檢查上傳日誌

```bash
docker logs issue-copier | grep -E "下載圖片|上傳圖片|處理圖片"
```

### 手動驗證 assets 分支

```bash
# 檢查 assets 分支是否存在
gh api repos/Intrising/QA-Switch-OS5/branches/assets

# 查看 assets 分支的內容
gh api repos/Intrising/QA-Switch-OS5/contents/images?ref=assets
```

## 未來增強

- [ ] PR 審查時自動上傳截圖
- [ ] Webhook 自動處理評論中的圖片
- [ ] 圖片壓縮和優化
- [ ] 自動清理未使用的圖片
- [ ] 支援更多檔案類型（PDF、影片等）

## 相關檔案

- `src/github_asset_uploader.py` - 核心上傳器
- `src/issue_copier.py` - Issue 複製器（已整合）
- `docker-compose.microservices.yml` - 容器配置
- `config.yaml` - 系統配置

---

**完全自動化，無需人工介入！** 🎉
