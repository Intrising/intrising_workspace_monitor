#!/usr/bin/env python3
"""
GitHub PR Auto-Reviewer - 使用 Anthropic API
接收 GitHub webhook 並使用 Claude API 自動審查 Pull Requests
"""

import os
import sys
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional
from flask import Flask, request, jsonify
from github import Github
from dotenv import load_dotenv
import yaml
import anthropic


class PRReviewer:
    """PR 自動審查器（使用 Anthropic API）"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化審查器"""
        load_dotenv()

        # 載入配置
        self.config = self._load_config(config_path)

        # 設置日誌
        self._setup_logging()

        # 初始化 GitHub 客戶端
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN 環境變數未設置")

        github_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
        self.github = Github(github_token, base_url=github_api_url)

        # 初始化 Anthropic 客戶端
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY 環境變數未設置")

        self.claude = anthropic.Anthropic(api_key=anthropic_api_key)

        # Webhook 密鑰
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")

        self.logger.info("PR Reviewer 初始化完成")

    def _load_config(self, config_path: str) -> dict:
        """載入 YAML 配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"無法載入配置文件: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """設置日誌系統"""
        log_level = os.getenv("LOG_LEVEL", "INFO")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        self.logger = logging.getLogger("PRReviewer")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(handler)

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """驗證 GitHub webhook 簽名"""
        if not self.webhook_secret:
            self.logger.warning("WEBHOOK_SECRET 未設置，跳過簽名驗證")
            return True

        expected_signature = 'sha256=' + hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        """獲取 PR 的 diff 內容"""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # 獲取文件變更
            files = pr.get_files()
            diff_content = []

            for file in files:
                diff_content.append(f"\n{'='*80}")
                diff_content.append(f"文件: {file.filename}")
                diff_content.append(f"狀態: {file.status}")
                diff_content.append(f"變更: +{file.additions} -{file.deletions}")
                diff_content.append(f"{'='*80}\n")

                if file.patch:
                    diff_content.append(file.patch)
                else:
                    diff_content.append("(無 diff 內容 - 可能是二進制文件)")

            return "\n".join(diff_content)

        except Exception as e:
            self.logger.error(f"獲取 PR diff 失敗: {e}")
            return ""

    def get_pr_context(self, repo_full_name: str, pr_number: int) -> Dict:
        """獲取 PR 的上下文信息"""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            return {
                "title": pr.title,
                "description": pr.body or "(無描述)",
                "author": pr.user.login,
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "files_changed": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "commits": pr.commits,
            }

        except Exception as e:
            self.logger.error(f"獲取 PR 上下文失敗: {e}")
            return {}

    def review_pr_with_claude(self, repo_full_name: str, pr_number: int) -> Optional[str]:
        """使用 Claude API 審查 PR"""
        try:
            # 獲取 PR 上下文和 diff
            context = self.get_pr_context(repo_full_name, pr_number)
            diff = self.get_pr_diff(repo_full_name, pr_number)

            if not diff:
                self.logger.warning(f"PR #{pr_number} 沒有 diff 內容")
                return None

            # 構建審查提示詞
            review_config = self.config.get("review", {})
            prompt = self._build_review_prompt(context, diff, review_config)

            # 調用 Claude API
            self.logger.info(f"正在使用 Claude API 審查 PR #{pr_number}...")

            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            review_content = message.content[0].text
            self.logger.info(f"Claude 審查完成: {len(review_content)} 字符")

            return review_content

        except Exception as e:
            self.logger.error(f"Claude 審查失敗: {e}")
            return None

    def _build_review_prompt(self, context: Dict, diff: str, config: Dict) -> str:
        """構建審查提示詞"""
        focus_areas = config.get("focus_areas", [
            "代碼質量",
            "潛在 bug",
            "性能問題",
            "安全漏洞",
            "最佳實踐"
        ])

        language = config.get("language", "zh-TW")

        prompt = f"""你是一位專業的代碼審查專家。請仔細審查以下 Pull Request 的代碼變更。

## PR 信息
- **標題**: {context.get('title', 'N/A')}
- **作者**: {context.get('author', 'N/A')}
- **分支**: {context.get('head_branch', 'N/A')} → {context.get('base_branch', 'N/A')}
- **文件變更**: {context.get('files_changed', 0)} 個文件
- **代碼變更**: +{context.get('additions', 0)} -{context.get('deletions', 0)} 行

## PR 描述
{context.get('description', '(無描述)')}

## 代碼變更
{diff}

## 審查要求
請重點關注以下方面：
{chr(10).join(f"- {area}" for area in focus_areas)}

## 輸出格式
請提供以下格式的審查報告：

### 總體評價
[簡要總結這個 PR 的整體質量和主要變更]

### 發現的問題
[列出發現的問題，按嚴重程度排序]
- **嚴重**: [嚴重問題]
- **中等**: [中等問題]
- **輕微**: [輕微問題]

### 改進建議
[提供具體的改進建議]

### 優點
[指出代碼的優點]

### 結論
[給出總體建議：批准/需要修改/拒絕]

請使用 {language} 回覆。
"""
        return prompt

    def post_review_comment(self, repo_full_name: str, pr_number: int, review_content: str):
        """發布審查評論到 PR"""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # 添加審查評論
            comment_body = f"""## 🤖 自動代碼審查

{review_content}

---
*由 Claude AI 自動生成 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            pr.create_issue_comment(comment_body)
            self.logger.info(f"已發布審查評論到 PR #{pr_number}")

            # 可選：添加審查標籤
            auto_label = self.config.get("review", {}).get("auto_label", True)
            if auto_label:
                try:
                    pr.add_to_labels("auto-reviewed")
                except Exception as e:
                    self.logger.debug(f"添加標籤失敗: {e}")

        except Exception as e:
            self.logger.error(f"發布審查評論失敗: {e}")

    def process_pr_event(self, event_type: str, payload: Dict) -> Dict:
        """處理 PR 事件"""
        try:
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            repo_full_name = payload.get("repository", {}).get("full_name", "")
            pr_number = pr.get("number", 0)

            self.logger.info(f"收到 PR 事件: {event_type} - {action} - {repo_full_name}#{pr_number}")

            # 檢查是否應該審查
            review_triggers = self.config.get("review", {}).get("triggers", ["opened", "synchronize"])

            if action not in review_triggers:
                self.logger.info(f"動作 '{action}' 不在觸發列表中，跳過審查")
                return {"status": "skipped", "reason": "action not in triggers"}

            # 檢查是否是 draft PR
            if pr.get("draft", False):
                skip_draft = self.config.get("review", {}).get("skip_draft", True)
                if skip_draft:
                    self.logger.info("跳過 draft PR")
                    return {"status": "skipped", "reason": "draft PR"}

            # 執行審查
            review_content = self.review_pr_with_claude(repo_full_name, pr_number)

            if review_content:
                # 發布審查評論
                self.post_review_comment(repo_full_name, pr_number, review_content)

                return {
                    "status": "success",
                    "pr_number": pr_number,
                    "repo": repo_full_name,
                    "review_length": len(review_content)
                }
            else:
                return {
                    "status": "error",
                    "reason": "review generation failed"
                }

        except Exception as e:
            self.logger.error(f"處理 PR 事件失敗: {e}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e)
            }


# Flask 應用
app = Flask(__name__)
reviewer = None


@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        "status": "healthy",
        "service": "PR Auto-Reviewer (API)",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
@app.route('/webhook/', methods=['POST'])
def webhook():
    """GitHub webhook 端點"""
    try:
        # 驗證簽名
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not reviewer.verify_webhook_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 401

        # 獲取事件類型
        event_type = request.headers.get('X-GitHub-Event', '')

        # 只處理 PR 事件
        if event_type != 'pull_request':
            return jsonify({"status": "ignored", "event": event_type}), 200

        # 處理 PR 事件
        payload = request.json
        result = reviewer.process_pr_event(event_type, payload)

        return jsonify(result), 200

    except Exception as e:
        reviewer.logger.error(f"Webhook 處理失敗: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def main():
    """主程序入口"""
    global reviewer

    try:
        # 初始化審查器
        reviewer = PRReviewer()

        # 獲取配置
        host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
        port = int(os.getenv("WEBHOOK_PORT", "8080"))
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

        reviewer.logger.info(f"啟動 webhook 服務器: {host}:{port}")

        # 啟動 Flask 應用
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        print(f"啟動失敗: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
