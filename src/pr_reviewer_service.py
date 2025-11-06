#!/usr/bin/env python3
"""
PR Reviewer 微服務
專門處理 Pull Request 自動審查
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

# 導入共享模組
from database import TaskDatabase


class PRReviewerService:
    """PR Reviewer 微服務"""

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

        # PR 審查配置
        self.review_config = self.config.get('review', {})

        self.logger.info("PR Reviewer 服務初始化完成")

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

        self.logger = logging.getLogger("PRReviewer")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(handler)

    def _perform_codex_review(self, repo_name: str, pr_number: int, pr_data: Dict) -> Dict:
        """使用 Claude CLI 執行 PR 審查"""
        import subprocess
        import tempfile

        try:
            self.logger.info(f"開始使用 Claude 審查 {repo_name}#{pr_number}")

            # 獲取 PR 的詳細信息和 diff
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # 獲取 PR 的基本信息
            pr_title = pr.title
            pr_body = pr.body or "無描述"
            pr_url = pr.html_url

            # 獲取改動的文件列表
            files = pr.get_files()
            files_info = []
            total_changes = 0

            for file in files:
                if total_changes > 10000:  # 限制審查的代碼量
                    self.logger.warning("代碼改動太大，截斷部分內容")
                    break

                files_info.append({
                    'filename': file.filename,
                    'status': file.status,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'changes': file.changes,
                    'patch': file.patch if hasattr(file, 'patch') and file.patch else ''
                })
                total_changes += file.changes

            # 構建詳細的審查提示
            files_summary = "\n".join([
                f"- {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
                for f in files_info
            ])

            files_diff = "\n\n".join([
                f"### {f['filename']}\n```diff\n{f['patch']}\n```"
                for f in files_info if f['patch']
            ])

            prompt = f"""你是一個專業的 Code Review 專家，擁有豐富的軟體開發和代碼審查經驗。請以專業、嚴謹的態度審查以下 Pull Request。

**Pull Request 資訊**:
- **標題**: {pr_title}
- **描述**: {pr_body}
- **URL**: {pr_url}

**改動的文件**:
{files_summary}

**代碼改動內容**:
{files_diff}

請提供專業的代碼審查報告，包括：

1. **代碼質量評估**: 評估代碼的可讀性、可維護性、設計模式使用
2. **潛在問題或 Bug**: 指出可能的邏輯錯誤、邊界條件問題、異常處理缺失
3. **改進建議**: 提供具體的優化建議和最佳實踐
4. **安全性考量**: 檢查是否存在安全漏洞、敏感資料洩漏、注入攻擊風險
5. **性能影響**: 評估改動對系統性能的影響

請用繁體中文回答，保持專業且簡潔。如果代碼質量良好，請給予肯定；如果有問題，請明確指出並提供改進方案。"""

            # 將 prompt 寫入臨時文件（避免命令行參數過長）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name

            try:
                # 調用 Claude CLI，從文件讀取 prompt
                result = subprocess.run(
                    ['sh', '-c', f'cat {prompt_file} | claude --print "$(cat)"'],
                    capture_output=True,
                    text=True,
                    timeout=180  # 3分鐘超時
                )

                if result.returncode == 0:
                    review_content = result.stdout.strip()
                    self.logger.info(f"Claude 審查完成，內容長度: {len(review_content)}")
                    return {
                        'success': True,
                        'content': review_content
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
                import os
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

    def _post_review_to_github(self, repo_name: str, pr_number: int, review_content: str):
        """將審查結果發布到 GitHub PR"""
        try:
            self.logger.info(f"發布審查結果到 {repo_name}#{pr_number}")

            # 獲取 PR 對象
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # 格式化審查內容
            comment_body = f"""## 🤖 AI Code Review

{review_content}

---
*由 Claude AI 自動審查*
"""

            # 發布評論
            pr.create_issue_comment(comment_body)
            self.logger.info(f"審查結果已發布到 {repo_name}#{pr_number}")

        except Exception as e:
            self.logger.error(f"發布審查結果失敗: {e}", exc_info=True)
            raise

    def should_review_pr(self, pr_data: Dict) -> bool:
        """判斷是否應該審查此 PR"""
        # 檢查是否是 draft PR
        if self.review_config.get('skip_draft', True):
            if pr_data.get('draft', False):
                self.logger.info("跳過 draft PR")
                return False

        return True

    def review_pr(self, pr_data: Dict) -> Dict:
        """審查 PR（異步處理）"""
        repo_name = pr_data.get('repository', {}).get('full_name')
        pr_number = pr_data.get('number')

        self.logger.info(f"收到 PR 審查請求: {repo_name}#{pr_number}")

        # 創建任務記錄 - 使用時間戳確保每次審查都是唯一的任務
        import time
        timestamp = str(int(time.time() * 1000))  # 毫秒級時間戳
        task_id = f"{repo_name}#{pr_number}@{timestamp}"

        task_data = {
            'task_id': task_id,
            'pr_number': pr_number,
            'repo': repo_name,
            'pr_title': pr_data.get('title', ''),
            'pr_author': pr_data.get('user', {}).get('login', ''),
            'pr_url': pr_data.get('html_url', ''),
            'status': 'queued',
            'message': '等待審查'
        }

        self.db.create_task(task_data)

        # 啟動後台線程處理審查（不阻塞 webhook 響應）
        import threading
        review_thread = threading.Thread(
            target=self._async_review_pr,
            args=(task_id, repo_name, pr_number, pr_data),
            daemon=True
        )
        review_thread.start()

        return {
            'status': 'success',
            'task_id': task_id,
            'message': 'PR 已加入審查隊列'
        }

    def _async_review_pr(self, task_id: str, repo_name: str, pr_number: int, pr_data: Dict):
        """異步執行 PR 審查（在後台線程中運行）"""
        try:
            # 更新狀態為處理中
            self.db.update_task(task_id, {
                'status': 'processing',
                'message': '正在審查 PR...'
            })

            # 執行 Claude 審查
            review_result = self._perform_codex_review(repo_name, pr_number, pr_data)

            if review_result['success']:
                # 將審查結果發布到 GitHub
                self._post_review_to_github(repo_name, pr_number, review_result['content'])

                self.db.update_task(task_id, {
                    'status': 'completed',
                    'message': '審查完成',
                    'review_content': review_result['content']
                })
            else:
                self.db.update_task(task_id, {
                    'status': 'failed',
                    'error_message': review_result.get('error', '審查失敗')
                })

        except Exception as e:
            self.logger.error(f"執行審查失敗: {e}", exc_info=True)
            self.db.update_task(task_id, {
                'status': 'failed',
                'error_message': str(e)
            })

    def process_pr_event(self, event_type: str, payload: Dict) -> Dict:
        """處理 PR 事件"""
        try:
            action = payload.get('action', '')
            pr = payload.get('pull_request', {})
            # 將 repository 資訊添加到 pr 物件中，以便後續使用
            pr['repository'] = payload.get('repository', {})

            self.logger.info(f"收到 PR 事件: {action}")

            # 檢查是否應該觸發審查
            triggers = self.review_config.get('triggers', ['opened', 'synchronize', 'reopened'])

            if action not in triggers:
                return {"status": "skipped", "reason": f"action '{action}' not in triggers"}

            # 檢查是否應該審查
            if not self.should_review_pr(pr):
                return {"status": "skipped", "reason": "PR not eligible for review"}

            # 執行審查
            result = self.review_pr(pr)

            return result

        except Exception as e:
            self.logger.error(f"處理 PR 事件失敗: {e}", exc_info=True)
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
        "service": "PR Reviewer",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 PR webhook"""
    try:
        event_type = request.headers.get('X-GitHub-Event', '')
        payload = request.json

        if event_type != 'pull_request':
            return jsonify({"error": "Invalid event type"}), 400

        result = service.process_pr_event(event_type, payload)
        return jsonify(result), 200

    except Exception as e:
        service.logger.error(f"Webhook 處理失敗: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """獲取任務列表"""
    try:
        limit = request.args.get('limit', 100, type=int)
        status = request.args.get('status')

        tasks = service.db.get_all_tasks(limit=limit, status=status)
        stats = service.db.get_task_stats()

        return jsonify({
            'total': len(tasks),
            'tasks': tasks,
            'stats': stats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """獲取單個任務"""
    try:
        task = service.db.get_task(task_id)
        if task:
            return jsonify(task)
        else:
            return jsonify({"error": "Task not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    """主程序"""
    global service

    try:
        # 初始化服務
        service = PRReviewerService()

        # 獲取配置
        host = os.getenv("SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("SERVICE_PORT", "8081"))
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

        service.logger.info(f"啟動 PR Reviewer 服務: {host}:{port}")

        # 啟動 Flask
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        print(f"啟動失敗: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
