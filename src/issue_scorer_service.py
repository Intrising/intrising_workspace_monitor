#!/usr/bin/env python3
"""
Issue Scorer 微服務
專門處理 Issue 品質評分（格式、內容、建議）
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Optional
from flask import Flask, request, jsonify
from github import Github
from dotenv import load_dotenv
import yaml
import subprocess
import tempfile
import time
import threading

# 導入共享模組
from database import TaskDatabase


class IssueScorerService:
    """Issue Scorer 微服務"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化服務"""
        load_dotenv()

        # 載入配置
        self.config = self._load_config(config_path)

        # 設置日誌
        self._setup_logging()

        # GitHub 客戶端
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN 環境變數未設置")

        self.github = Github(github_token)

        # 資料庫
        db_path = os.getenv("DB_PATH", "/var/lib/github-monitor/tasks.db")
        self.db = TaskDatabase(db_path)

        # 評分配置
        self.scoring_config = self.config.get('issue_scoring', {})

        self.logger.info("Issue Scorer 服務初始化完成")

    def _load_config(self, config_path: str) -> dict:
        """載入配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"無法載入配置: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """設置日誌"""
        log_level = os.getenv("LOG_LEVEL", "INFO")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        self.logger = logging.getLogger("IssueScorer")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(handler)

    def _detect_issue_type(self, title: str, body: str) -> str:
        """偵測 issue 類型"""
        title_lower = title.lower()
        body_lower = body.lower() if body else ""

        # 根據標題前綴判斷
        if "[task]" in title_lower or "task" in title_lower:
            return "task"
        elif "[request" in title_lower or "request for features" in title_lower:
            return "request"
        elif "[test]" in title_lower or "測試結果" in title_lower or "test result" in title_lower:
            return "test"
        elif "[bug]" in title_lower or "bug report" in title_lower:
            return "bug"

        # 根據內容結構判斷
        if "## todo" in body_lower or "- [ ]" in body_lower:
            return "task"
        elif "## specification" in body_lower or "## reference" in body_lower:
            return "request"
        elif ("test case" in body_lower or "測試案例" in body_lower or
              ("## issue overview" in body_lower and "## test result" in body_lower) or
              ("## issue overview" in body_lower and "## test environment" in body_lower)):
            return "test"

        # 默認為 bug report
        return "bug"

    def _perform_claude_scoring(self, repo_name: str, issue_number: int,
                                content_type: str, title: str, body: str,
                                author: str,
                                comment_id: Optional[int] = None,
                                issue_labels: list = None) -> Dict:
        """使用 Claude CLI 執行 issue/comment 評分（包含作者歷史）"""
        try:
            self.logger.info(f"開始使用 Claude 評分 {repo_name}#{issue_number} ({content_type}) by {author}")

            # 獲取作者歷史統計
            author_history = self.db.get_author_issue_history(author, limit=10)
            author_stats = author_history['stats']

            # 構建作者歷史資訊區塊
            author_history_text = ""
            if author_stats['total_issues'] > 0:
                trend_text = {
                    'improving': '📈 進步中（最近表現優於過去）',
                    'declining': '📉 需加強（最近表現不如過去）',
                    'stable': '➡️ 穩定'
                }.get(author_stats['trend'], '')

                author_history_text = f"""

## 📊 作者歷史表現

**作者**: {author}
- **過去 Issue/Comment 總數**: {author_stats['total_issues']} 個
- **平均總分**: {author_stats['avg_overall']}/100
- **各維度平均分**:
  - 格式正確性: {author_stats['avg_format']}/100
  - 內容完整性: {author_stats['avg_content']}/100
  - 清晰度: {author_stats['avg_clarity']}/100
  - 可操作性: {author_stats['avg_actionability']}/100
- **分數範圍**: {author_stats['min_score']} - {author_stats['max_score']}
- **趨勢**: {trend_text}
- **最近5次評分**: {', '.join(map(str, author_stats['recent_scores']))}

💡 **評分參考**：請參考該作者的歷史表現，給予公正且一致的評分標準。如果該作者表現持續進步，可以在評語中給予鼓勵；如果表現退步或維持低分，請在建議中提供明確的改進方向。

"""

            # 構建評分提示
            if content_type == "issue":
                content_description = f"""
**Issue 標題**: {title}

**Issue 內容**:
{body}
"""
                # 偵測 issue 類型
                issue_type = self._detect_issue_type(title, body)
                self.logger.info(f"偵測到 issue 類型: {issue_type}")
            else:  # comment
                content_description = f"""
**評論內容**:
{body}
"""
                issue_type = "comment"

            # 根據類型選擇不同的評分標準
            if content_type == "issue" and issue_type == "bug":
                prompt = f"""你是一個專業的 QA Issue 品質評估專家，負責評估 GitHub Issue 和評論的品質。請根據標準的 Bug Report Template 格式來評估以下內容。

{content_description}
{author_history_text}

**標準 Issue Template 必填欄位**：
1. **Links** - 來源連結（Parent/child issue, Reference）
2. **Environment** - 環境資訊（FW/HW/Bootloader 版本、硬體型號等）
3. **Description** - 清楚簡潔的問題描述
4. **To Reproduce** - 重現步驟（必須是編號列表格式，如 "1. Go to...", "2. Click on...", "3. See error"）
5. **Expected Behavior** - 期望的行為
6. **Screenshots/Attachments** - 截圖或附件（如適用）

**前置檢查清單**（Notes section）：
- [ ] Add labels for `type`, `project`, `from` and `status`
- [ ] Add assignees
- [ ] Review issue content and delete this note

請從以下四個維度進行評分（每個維度 0-100 分）：

1. **格式正確性** (0-100分)
   - 是否遵循標準 template 的 Markdown 格式結構
   - 是否有正確的章節標題（## Links, ## Environment, ## Description 等）
   - To Reproduce 是否使用編號列表格式（1. 2. 3. ...）
   - 是否正確使用 HTML 註解（<!-- -->）
   - 是否設置了必要的 labels 和 assignees

2. **內容完整性** (0-100分)
   - **Links** 欄位是否有填寫（來源連結或相關 issue）
   - **Environment** 是否包含完整的 FW/HW/Bootloader 版本、硬體型號
   - **Description** 是否清楚描述問題
   - **To Reproduce** 是否提供詳細的重現步驟（至少 3 步）
   - **Expected Behavior** 是否說明期望的結果
   - **Screenshots/Attachments** 是否提供（針對視覺相關問題）
   - 是否移除了 template 中的註解提示（"<!-- -->" 內容應該被替換）

3. **清晰度** (0-100分)
   - Description 是否清楚易懂，避免模糊表述
   - To Reproduce 步驟是否具體明確（不能只寫 "Go to '...'"）
   - 技術術語使用是否正確
   - 問題現象描述是否準確
   - 是否避免無關資訊

4. **可操作性** (0-100分)
   - 根據 To Reproduce 步驟，開發人員是否能重現問題
   - Environment 資訊是否足夠讓開發人員建立測試環境
   - 是否提供具體的錯誤訊息或錯誤代碼
   - Expected Behavior 是否明確，讓開發人員知道如何驗證修復
   - 是否有助於快速定位問題根因

**特別注意**：
- 如果 issue 是從 test-lantech 轉過來的，檢查圖片連結是否已更新（不應該還指向舊 repo）
- 如果 template 註解還在（如 "<!-- ... -->"），應該提醒需要填寫實際內容
- 如果 To Reproduce 步驟只有 placeholder（如 "Go to '...'"），這是未完成的 issue

請以 JSON 格式回覆，格式如下：
```json
{{
  "format_score": 85,
  "format_feedback": "格式規範，使用了 Markdown，但標題可以更具體",
  "content_score": 90,
  "content_feedback": "包含了重現步驟、預期結果和實際結果，環境資訊完整",
  "clarity_score": 80,
  "clarity_feedback": "描述清晰，但部分技術術語需要更精確",
  "actionability_score": 88,
  "actionability_feedback": "提供了足夠的資訊幫助重現問題，建議補充日誌資訊",
  "overall_score": 86,
  "suggestions": [
    "建議在標題中明確指出問題模組或功能",
    "可以補充相關的錯誤日誌或堆疊追蹤",
    "建議標註問題的優先級或嚴重程度"
  ]
}}
```

請用繁體中文提供評估回饋，評分要客觀公正。"""

            elif content_type == "issue" and issue_type == "task":
                # Task 類型的評分標準
                prompt = f"""你是一個專業的項目管理和任務評估專家，負責評估 GitHub Task Issue 的品質。

{content_description}
{author_history_text}

**Task Template 標準結構**：
1. **Description** - 任務描述（清楚說明要做什麼）
2. **Todo** - 待辦事項清單（使用 checkbox: - [ ]）
3. **Links** - 相關連結（Parent/child issue, Reference）
4. **Deadline** - 完成期限（通常在標題中標註）

請從以下四個維度進行評分（每個維度 0-100 分）：

1. **格式正確性** (0-100分)
   - 是否有清楚的任務描述
   - Todo 是否使用 checkbox 格式（- [ ]）
   - 是否標註 deadline
   - 是否設置 assignees

2. **內容完整性** (0-100分)
   - Description 是否說明任務背景和目標
   - Todo 清單是否詳細且可執行
   - 是否有相關連結或參考資料
   - 是否移除了 template placeholder

3. **清晰度** (0-100分)
   - 任務目標是否明確
   - Todo 項目是否具體（不要太抽象）
   - 是否避免模糊的描述

4. **可操作性** (0-100分)
   - Todo 項目是否可以直接執行
   - 是否有明確的完成標準
   - 是否合理分配給不同成員
   - Deadline 是否合理

請以 JSON 格式回覆。請用繁體中文提供評估回饋。"""

            elif content_type == "issue" and issue_type == "request":
                # Request/Feature 類型的評分標準
                prompt = f"""你是一個專業的產品需求分析專家，負責評估 GitHub Feature Request 的品質。

{content_description}
{author_history_text}

**Request Template 標準結構**：
1. **Problem Description** - 問題或需求描述
2. **Product Info** - 產品系列/型號/平台資訊
3. **Firmware Version** - 韌體版本
4. **Specification** - 具體的需求規格
5. **Reference** - 參考資料（其他產品是否支援）

請從以下四個維度進行評分（每個維度 0-100 分）：

1. **格式正確性** (0-100分)
   - 是否遵循 Request template 結構
   - 是否包含產品和版本資訊
   - 是否設置適當的 labels

2. **內容完整性** (0-100分)
   - 問題或需求描述是否清楚
   - 產品資訊是否完整
   - Specification 是否詳細
   - 是否提供參考資料

3. **清晰度** (0-100分)
   - 需求是否明確
   - 規格描述是否清楚
   - 是否避免過於技術或過於簡略

4. **可操作性** (0-100分)
   - 開發團隊是否能理解需求
   - 規格是否可以實現
   - 是否有助於評估開發工作量

請以 JSON 格式回覆。請用繁體中文提供評估回饋。"""

            elif content_type == "issue" and issue_type == "test":
                # 測試結果類型的評分標準
                prompt = f"""你是一個專業的 QA 測試專家，負責評估測試結果報告的品質。

{content_description}
{author_history_text}

**測試結果報告標準結構**：
測試結果報告通常包含以下段落：
- **Issue Overview** - 測試問題概述
- **Test Result** - 測試結果（Pass/Fail/測試案例列表）
- **Test Environment** - 測試環境資訊（FW版本、HW版本、測試設備等）

請從以下四個維度進行評分（每個維度 0-100 分）：

1. **格式正確性** (0-100分)
   - 測試報告結構是否清楚（是否包含 Issue Overview、Test Result、Test Environment 等段落）
   - 是否使用表格或清單呈現測試結果
   - Markdown 格式是否正確（標題、表格、列表）
   - 是否有測試日期和測試人員資訊

2. **內容完整性** (0-100分)
   - **Issue Overview** 是否清楚說明測試目的或問題背景
   - **Test Result** 是否清楚列出測試案例和結果（Pass/Fail/Blocked）
   - **Test Environment** 是否包含完整的環境資訊（FW版本、HW版本、測試設備型號等）
   - 失敗的測試案例是否有詳細說明（錯誤訊息、截圖、日誌等）
   - 是否有測試覆蓋率或測試範圍說明

3. **清晰度** (0-100分)
   - 測試結果呈現是否一目了然（使用表格或清單）
   - 問題描述是否清楚具體
   - 測試數據和統計是否易於理解
   - 使用的技術術語是否正確

4. **可操作性** (0-100分)
   - 失敗的測試案例是否有足夠資訊讓開發人員重現問題
   - 是否提供下一步行動建議（需要修復的項目、阻塞問題等）
   - 是否有助於問題追蹤和版本控管
   - 測試環境資訊是否足夠讓其他人重現測試

請以 JSON 格式回覆，格式如下：
```json
{{
  "format_score": 85,
  "format_feedback": "評語",
  "content_score": 90,
  "content_feedback": "評語",
  "clarity_score": 80,
  "clarity_feedback": "評語",
  "actionability_score": 88,
  "actionability_feedback": "評語",
  "overall_score": 86,
  "suggestions": ["建議1", "建議2"]
}}
```

請用繁體中文提供評估回饋，評分要客觀公正。"""

            else:
                # Comment 或其他類型使用通用評分
                prompt = f"""你是一個專業的內容品質評估專家，負責評估 GitHub 內容的品質。

{content_description}
{author_history_text}

請從以下四個維度進行評分（每個維度 0-100 分）：

1. **格式正確性** (0-100分)
   - Markdown 格式是否正確
   - 結構是否清楚

2. **內容完整性** (0-100分)
   - 資訊是否完整
   - 是否回答了相關問題

3. **清晰度** (0-100分)
   - 描述是否清楚易懂
   - 邏輯是否連貫

4. **可操作性** (0-100分)
   - 是否提供有用的資訊
   - 是否有助於問題解決

請以 JSON 格式回覆，格式如下：
```json
{{
  "format_score": 85,
  "format_feedback": "評語",
  "content_score": 90,
  "content_feedback": "評語",
  "clarity_score": 80,
  "clarity_feedback": "評語",
  "actionability_score": 88,
  "actionability_feedback": "評語",
  "overall_score": 86,
  "suggestions": ["建議1", "建議2"]
}}
```

請用繁體中文提供評估回饋。"""

            # 將 prompt 寫入臨時文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name

            try:
                # 調用 Claude CLI
                result = subprocess.run(
                    ['sh', '-c', f'cat {prompt_file} | claude --print "$(cat)"'],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2分鐘超時
                )

                if result.returncode == 0:
                    response = result.stdout.strip()
                    self.logger.info(f"Claude 評分完成，回應長度: {len(response)}")

                    # 解析 JSON 回應
                    import json
                    import re

                    # 提取 JSON 部分（可能包含在 ```json ``` 中）
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # 嘗試直接解析
                        json_str = response

                    try:
                        score_data = json.loads(json_str)
                        return {
                            'success': True,
                            'scores': score_data
                        }
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSON 解析失敗: {e}, 原始回應: {response[:500]}")
                        return {
                            'success': False,
                            'error': f'JSON 解析失敗: {str(e)}'
                        }
                else:
                    error_msg = result.stderr.strip() or "Claude 執行失敗"
                    self.logger.error(f"Claude 執行失敗: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg
                    }
            finally:
                # 清理臨時文件
                if os.path.exists(prompt_file):
                    os.unlink(prompt_file)

        except subprocess.TimeoutExpired:
            self.logger.error("Claude 執行超時")
            return {
                'success': False,
                'error': 'Claude 執行超時'
            }
        except Exception as e:
            self.logger.error(f"Claude 執行異常: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _post_score_to_github(self, repo_name: str, issue_number: int,
                              score_data: Dict, content_type: str, author: str, source_url: str):
        """將評分結果發布到 GitHub Issue"""
        try:
            if not self.scoring_config.get('auto_comment', False):
                self.logger.info("自動評論功能已關閉，跳過發布")
                return

            self.logger.info(f"發布評分結果到 {repo_name}#{issue_number}")

            repo = self.github.get_repo(repo_name)
            issue = repo.get_issue(issue_number)

            # 格式化評分內容
            suggestions_list = "\n".join([f"- {s}" for s in score_data.get('suggestions', [])])

            content_type_display = "Issue" if content_type == "issue" else "評論"

            comment_body = f"""<!-- AUTO_SCORE_BOT_COMMENT -->
@{author}

## 📊 {content_type_display}品質評分

**評分來源**: {source_url}

### 評分結果

| 評分維度 | 分數 | 評語 |
|---------|------|------|
| 📝 格式正確性 | **{score_data.get('format_score', 0)}/100** | {score_data.get('format_feedback', 'N/A')} |
| 📋 內容完整性 | **{score_data.get('content_score', 0)}/100** | {score_data.get('content_feedback', 'N/A')} |
| 🎯 清晰度 | **{score_data.get('clarity_score', 0)}/100** | {score_data.get('clarity_feedback', 'N/A')} |
| ⚙️ 可操作性 | **{score_data.get('actionability_score', 0)}/100** | {score_data.get('actionability_feedback', 'N/A')} |

### 📊 總體評分: **{score_data.get('overall_score', 0)}/100**

### 💡 改進建議

{suggestions_list if suggestions_list else '暫無建議'}

---
*由 Claude AI 自動評分*
"""

            # 發布評論
            issue.create_comment(comment_body)
            self.logger.info(f"評分結果已發布到 {repo_name}#{issue_number}")

        except Exception as e:
            self.logger.error(f"發布評分結果失敗: {e}", exc_info=True)
            raise

    def should_score_issue(self, repo_name: str, event_type: str, action: str) -> bool:
        """判斷是否應該評分此 issue/comment"""
        # 檢查 repository 是否在目標列表中
        target_repos = self.scoring_config.get('target_repos', [])
        if repo_name not in target_repos:
            self.logger.info(f"Repository {repo_name} 不在評分目標列表中")
            return False

        # 檢查 action 是否匹配觸發條件
        if event_type == "issues":
            triggers = self.scoring_config.get('triggers', [])
            if action not in triggers:
                self.logger.info(f"Issue action '{action}' 不在觸發列表中")
                return False
        elif event_type == "issue_comment":
            triggers = self.scoring_config.get('comment_triggers', [])
            if action not in triggers:
                self.logger.info(f"Comment action '{action}' 不在觸發列表中")
                return False

        return True

    def score_issue(self, event_type: str, event_data: Dict) -> Dict:
        """評分 issue 或 comment（異步處理）"""
        repo_name = event_data.get('repository', {}).get('full_name')
        issue_number = event_data.get('issue', {}).get('number')
        action = event_data.get('action', '')

        self.logger.info(f"收到評分請求: {repo_name}#{issue_number} ({event_type}/{action})")

        # 確定內容類型和要評分的內容
        if event_type == "issues":
            content_type = "issue"
            issue_data = event_data.get('issue', {})
            title = issue_data.get('title', '')
            body = issue_data.get('body', '')

            # 使用 sender (執行動作的人) 而不是 issue.user (原始作者)
            # 這樣轉貼的 Issue 會以轉貼者作為人員統計依據
            author = event_data.get('sender', {}).get('login', '')
            if not author:
                # 如果沒有 sender,才使用原始作者作為備援
                author = issue_data.get('user', {}).get('login', '')

            issue_url = issue_data.get('html_url', '')
            comment_id = None

            # ✅ Issue 創建時評分（action = opened）
            # 🔄 Issue 編輯時更新標題（action = edited）
            if action == 'edited':
                # 更新現有評分記錄的標題
                self.logger.info(f"Issue 被編輯，更新標題: {repo_name}#{issue_number}")
                self.db.update_score_title(repo_name, issue_number, title)
                return {
                    'status': 'updated',
                    'message': f'已更新 Issue 標題'
                }
            elif action != 'opened':
                self.logger.info(f"跳過評分：Issue action 為 '{action}'，只評分 'opened'")
                return {
                    'status': 'skipped',
                    'message': f'只評分新建立的 Issue (opened)，當前 action: {action}'
                }

        else:  # issue_comment
            content_type = "comment"
            comment_data = event_data.get('comment', {})
            issue_data = event_data.get('issue', {})
            title = issue_data.get('title', '')  # 保留 issue 標題作為參考
            body = comment_data.get('body', '')

            # 使用 sender (執行動作的人) 而不是 comment.user (原始作者)
            # 這樣轉貼評論時會以轉貼者作為人員統計依據
            author = event_data.get('sender', {}).get('login', '')
            if not author:
                # 如果沒有 sender,才使用原始作者作為備援
                author = comment_data.get('user', {}).get('login', '')

            issue_url = comment_data.get('html_url', '')
            comment_id = comment_data.get('id')

            # 🔒 防止無限循環：跳過機器人自己的評論
            # 檢查評論是否包含自動評分標記
            if body and '<!-- AUTO_SCORE_BOT_COMMENT -->' in body:
                self.logger.info(f"跳過評分：這是機器人自己的評論 (repo={repo_name}, issue={issue_number}, comment={comment_id})")
                return {
                    'status': 'skipped',
                    'message': '跳過機器人自己的評論，避免無限循環'
                }

            # 也檢查作者是否為機器人（雙重保護）
            # 但如果評論包含結構化的修復報告內容，則仍然進行評分
            try:
                bot_user = self.github.get_user().login
                if author == bot_user:
                    # 檢查是否包含結構化的修復報告標記
                    structured_markers = [
                        '### Fixed in Version',
                        '### Root Cause',
                        '### Solution',
                        '### Post-Fix Side Effects Analysis'
                    ]
                    has_structured_content = all(marker in body for marker in structured_markers)

                    if has_structured_content:
                        self.logger.info(f"評論作者是機器人 ({author})，但包含結構化修復報告，仍進行評分")
                    else:
                        # 記錄缺少哪些標記以便除錯
                        missing_markers = [marker for marker in structured_markers if marker not in body]
                        self.logger.info(f"跳過評分：評論作者是機器人本身 ({author})，缺少標記: {missing_markers}")
                        return {
                            'status': 'skipped',
                            'message': '跳過機器人自己的評論'
                        }
            except Exception as e:
                self.logger.warning(f"無法獲取機器人用戶名: {e}")

            # ✅ 所有評論都進行評分（移除過濾邏輯）
            self.logger.info(f"準備評分評論: repo={repo_name}, issue={issue_number}, comment={comment_id}")

        # 創建評分記錄 - 使用時間戳確保唯一性
        timestamp = str(int(time.time() * 1000))
        score_id = f"{repo_name}#{issue_number}@{content_type}@{comment_id or 'issue'}@{timestamp}"

        score_record = {
            'score_id': score_id,
            'repo_name': repo_name,
            'issue_number': issue_number,
            'comment_id': comment_id,
            'event_type': event_type,
            'content_type': content_type,
            'title': title,
            'body': body,
            'author': author,
            'issue_url': issue_url,
            'status': 'queued'
        }

        self.db.create_score_record(score_record)

        # 啟動後台線程處理評分（不阻塞 webhook 響應）
        score_thread = threading.Thread(
            target=self._async_score_content,
            args=(score_id, repo_name, issue_number, content_type, title, body, comment_id, author, issue_url),
            daemon=True
        )
        score_thread.start()

        return {
            'status': 'success',
            'score_id': score_id,
            'message': f'{content_type} 已加入評分隊列'
        }

    def _async_score_content(self, score_id: str, repo_name: str, issue_number: int,
                             content_type: str, title: str, body: str,
                             comment_id: Optional[int], author: str, source_url: str):
        """異步執行評分（在後台線程中運行）"""
        try:
            # 更新狀態為處理中
            self.db.update_score_record(score_id, {
                'status': 'processing'
            })

            # 執行 Claude 評分
            score_result = self._perform_claude_scoring(
                repo_name, issue_number, content_type, title, body, author, comment_id
            )

            if score_result['success']:
                scores = score_result['scores']

                # 將評分結果發布到 GitHub
                self._post_score_to_github(repo_name, issue_number, scores, content_type, author, source_url)

                # 更新資料庫
                self.db.update_score_record(score_id, {
                    'status': 'completed',
                    'format_score': scores.get('format_score'),
                    'format_feedback': scores.get('format_feedback'),
                    'content_score': scores.get('content_score'),
                    'content_feedback': scores.get('content_feedback'),
                    'clarity_score': scores.get('clarity_score'),
                    'clarity_feedback': scores.get('clarity_feedback'),
                    'actionability_score': scores.get('actionability_score'),
                    'actionability_feedback': scores.get('actionability_feedback'),
                    'overall_score': scores.get('overall_score'),
                    'suggestions': '\n'.join(scores.get('suggestions', [])),
                    'completed_at': datetime.now().isoformat()
                })
            else:
                self.db.update_score_record(score_id, {
                    'status': 'failed',
                    'error_message': score_result.get('error', '評分失敗')
                })

        except Exception as e:
            self.logger.error(f"執行評分失敗: {e}", exc_info=True)
            self.db.update_score_record(score_id, {
                'status': 'failed',
                'error_message': str(e)
            })

    def process_event(self, event_type: str, payload: Dict) -> Dict:
        """處理 issue/comment 事件"""
        try:
            action = payload.get('action', '')

            # 將 repository 資訊添加到 payload 中
            payload['repository'] = payload.get('repository', {})
            payload['issue'] = payload.get('issue', {})

            repo_name = payload['repository'].get('full_name', '')

            self.logger.info(f"收到事件: {event_type} / {action} from {repo_name}")

            # 檢查是否應該觸發評分
            if not self.should_score_issue(repo_name, event_type, action):
                return {"status": "skipped", "reason": "不符合評分條件"}

            # 執行評分
            result = self.score_issue(event_type, payload)

            return result

        except Exception as e:
            self.logger.error(f"處理事件失敗: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }


# Flask 應用
app = Flask(__name__)
service = None


@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "healthy",
        "service": "Issue Scorer",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 issue/comment webhook"""
    try:
        event_type = request.headers.get('X-GitHub-Event', '')
        payload = request.json

        if event_type not in ['issues', 'issue_comment']:
            return jsonify({"error": "Invalid event type"}), 400

        result = service.process_event(event_type, payload)
        return jsonify(result), 200

    except Exception as e:
        service.logger.error(f"Webhook 處理失敗: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/scores', methods=['GET'])
def get_scores():
    """獲取評分列表"""
    try:
        limit = request.args.get('limit', 100, type=int)
        status = request.args.get('status')
        repo_name = request.args.get('repo')

        scores = service.db.get_all_score_records(limit=limit, status=status, repo_name=repo_name)
        stats = service.db.get_score_stats(repo_name=repo_name)

        return jsonify({
            'total': len(scores),
            'scores': scores,
            'stats': stats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scores/<score_id>', methods=['GET'])
def get_score(score_id):
    """獲取單個評分記錄"""
    try:
        score = service.db.get_score_record(score_id)
        if score:
            return jsonify(score)
        else:
            return jsonify({"error": "Score not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scores/<path:score_id>/feedback', methods=['POST'])
def update_feedback(score_id):
    """更新評分記錄的使用者反饋"""
    try:
        data = request.json
        feedback = data.get('user_feedback', '')

        # 更新資料庫
        success = service.db.update_score_record(score_id, {
            'user_feedback': feedback
        })

        if success:
            return jsonify({
                'status': 'success',
                'message': '反饋已更新'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '找不到評分記錄'
            }), 404

    except Exception as e:
        service.logger.error(f"更新反饋失敗: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/scores/<path:score_id>/ignore', methods=['POST'])
def toggle_ignore(score_id):
    """切換評分記錄的忽略狀態"""
    try:
        data = request.json
        ignored = data.get('ignored', False)

        # 更新資料庫
        success = service.db.update_score_record(score_id, {
            'ignored': 1 if ignored else 0
        })

        if success:
            return jsonify({
                'status': 'success',
                'message': '已更新忽略狀態',
                'ignored': ignored
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '找不到評分記錄'
            }), 404

    except Exception as e:
        service.logger.error(f"更新忽略狀態失敗: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def main():
    """主程序"""
    global service

    try:
        # 初始化服務
        service = IssueScorerService()

        # 獲取配置
        host = os.getenv("SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("SERVICE_PORT", "8083"))
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

        service.logger.info(f"啟動 Issue Scorer 服務: {host}:{port}")

        # 啟動 Flask
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        print(f"啟動失敗: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
