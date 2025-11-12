#!/usr/bin/env python3
"""
Workspace Monitor Gateway - Webhook 路由和 Web UI
接收 GitHub webhook 並路由到對應的微服務
"""

import os
import sys
import hmac
import hashlib
import logging
import requests
from datetime import datetime
from typing import Dict, Optional
from flask import Flask, request, jsonify, render_template_string
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import yaml
import uuid

# 導入資料庫模組
from database import TaskDatabase

# 導入 route 處理函數
from gateway_routes import (
    get_dashboard,
    get_webhooks,
    handle_webhook,
    proxy_issue_scorer_scores,
    update_score_feedback,
    toggle_score_ignore,
    get_all_scores,
    delete_score_record,
    index,
    pr_tasks_page,
    issue_copies_page,
    comment_syncs_page,
    history_page,
    issue_scores_page,
    all_scores_page,
    scorer_config_page,
    get_scorer_config,
    update_scorer_config,
    get_feedback_analytics,
    get_feedback_patterns_api
)


class WorkspaceGateway:
    """Workspace Monitor Gateway"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化 Gateway"""
        load_dotenv()

        # 載入配置
        self.config = self._load_config(config_path)

        # 設置日誌
        self._setup_logging()

        # Webhook 密鑰
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")

        # 微服務端點
        self.pr_reviewer_url = os.getenv("PR_REVIEWER_URL", "http://pr-reviewer:8081")
        self.issue_copier_url = os.getenv("ISSUE_COPIER_URL", "http://issue-copier:8082")
        self.issue_scorer_url = os.getenv("ISSUE_SCORER_URL", "http://issue-scorer:8083")

        # 資料庫（用於記錄 webhook 歷史）
        db_path = os.getenv("DB_PATH", "/var/lib/github-monitor/tasks.db")
        self.db = TaskDatabase(db_path)

        self.logger.info("Workspace Gateway 初始化完成")
        self.logger.info(f"PR Reviewer: {self.pr_reviewer_url}")
        self.logger.info(f"Issue Copier: {self.issue_copier_url}")
        self.logger.info(f"Issue Scorer: {self.issue_scorer_url}")

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

        self.logger = logging.getLogger("Gateway")
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

    def route_webhook(self, event_type: str, payload: Dict) -> Dict:
        """路由 webhook 到對應的微服務"""
        try:
            results = {}
            processed_by = []
            overall_status = 'processed'
            error_msgs = []

            # 提取基本信息
            repo_name = payload.get('repository', {}).get('full_name')
            sender = payload.get('sender', {}).get('login')
            action = payload.get('action')
            pr_number = payload.get('pull_request', {}).get('number')
            issue_number = payload.get('issue', {}).get('number')

            # 路由 PR 事件到 PR Reviewer
            if event_type == 'pull_request':
                self.logger.info(f"路由 PR 事件到 PR Reviewer")
                processed_by.append('pr-reviewer')
                try:
                    response = requests.post(
                        f"{self.pr_reviewer_url}/webhook",
                        json=payload,
                        headers={'X-GitHub-Event': event_type},
                        timeout=10
                    )
                    results['pr_reviewer'] = {
                        'status': 'success' if response.status_code == 200 else 'error',
                        'response': response.json() if response.status_code == 200 else None,
                        'error': response.text if response.status_code != 200 else None
                    }
                    if response.status_code != 200:
                        overall_status = 'failed'
                        error_msgs.append(f"PR Reviewer: {response.text}")
                except Exception as e:
                    self.logger.error(f"路由到 PR Reviewer 失敗: {e}")
                    results['pr_reviewer'] = {'status': 'error', 'error': str(e)}
                    overall_status = 'failed'
                    error_msgs.append(f"PR Reviewer: {str(e)}")

            # 路由 Issue 事件到 Issue Copier
            if event_type in ['issues', 'issue_comment']:
                self.logger.info(f"路由 {event_type} 事件到 Issue Copier")
                processed_by.append('issue-copier')
                try:
                    response = requests.post(
                        f"{self.issue_copier_url}/webhook",
                        json=payload,
                        headers={'X-GitHub-Event': event_type},
                        timeout=10
                    )
                    results['issue_copier'] = {
                        'status': 'success' if response.status_code == 200 else 'error',
                        'response': response.json() if response.status_code == 200 else None,
                        'error': response.text if response.status_code != 200 else None
                    }
                    if response.status_code != 200:
                        overall_status = 'failed'
                        error_msgs.append(f"Issue Copier: {response.text}")
                except Exception as e:
                    self.logger.error(f"路由到 Issue Copier 失敗: {e}")
                    results['issue_copier'] = {'status': 'error', 'error': str(e)}
                    overall_status = 'failed'
                    error_msgs.append(f"Issue Copier: {str(e)}")

            # 路由 Issue 事件到 Issue Scorer
            if event_type in ['issues', 'issue_comment']:
                self.logger.info(f"路由 {event_type} 事件到 Issue Scorer")
                processed_by.append('issue-scorer')
                try:
                    response = requests.post(
                        f"{self.issue_scorer_url}/webhook",
                        json=payload,
                        headers={'X-GitHub-Event': event_type},
                        timeout=10
                    )
                    results['issue_scorer'] = {
                        'status': 'success' if response.status_code == 200 else 'error',
                        'response': response.json() if response.status_code == 200 else None,
                        'error': response.text if response.status_code != 200 else None
                    }
                    if response.status_code != 200:
                        overall_status = 'failed'
                        error_msgs.append(f"Issue Scorer: {response.text}")
                except Exception as e:
                    self.logger.error(f"路由到 Issue Scorer 失敗: {e}")
                    results['issue_scorer'] = {'status': 'error', 'error': str(e)}
                    overall_status = 'failed'
                    error_msgs.append(f"Issue Scorer: {str(e)}")

            # 記錄 webhook 事件到資料庫
            try:
                event_id = f"{event_type}-{repo_name}-{pr_number or issue_number or 'unknown'}-{str(uuid.uuid4())[:8]}"
                self.db.record_webhook_event({
                    'event_id': event_id,
                    'event_type': event_type,
                    'repo_name': repo_name,
                    'pr_number': pr_number,
                    'issue_number': issue_number,
                    'action': action,
                    'sender': sender,
                    'payload': payload,
                    'processed_by': ','.join(processed_by) if processed_by else None,
                    'status': overall_status,
                    'error_message': '; '.join(error_msgs) if error_msgs else None
                })
            except Exception as e:
                self.logger.error(f"記錄 webhook 事件失敗: {e}")

            return {
                'status': 'success',
                'event_type': event_type,
                'routed_to': list(results.keys()),
                'results': results
            }

        except Exception as e:
            self.logger.error(f"路由 webhook 失敗: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_aggregated_data(self) -> Dict:
        """聚合來自各微服務的數據"""
        data = {
            'pr_reviewer': None,
            'issue_copier': None,
            'issue_scorer': None,
            'timestamp': datetime.now().isoformat()
        }

        # 從 PR Reviewer 獲取數據
        try:
            response = requests.get(f"{self.pr_reviewer_url}/api/tasks", timeout=5)
            if response.status_code == 200:
                data['pr_reviewer'] = response.json()
        except Exception as e:
            self.logger.error(f"獲取 PR Reviewer 數據失敗: {e}")

        # 從 Issue Copier 獲取數據
        try:
            response = requests.get(f"{self.issue_copier_url}/api/issue-copies", timeout=5)
            if response.status_code == 200:
                data['issue_copier'] = response.json()

                # 同時獲取 comment sync 數據
                try:
                    comment_response = requests.get(f"{self.issue_copier_url}/api/comment-syncs", timeout=5)
                    if comment_response.status_code == 200:
                        comment_data = comment_response.json()
                        data['issue_copier']['comment_syncs'] = comment_data.get('records', [])
                        data['issue_copier']['comment_stats'] = comment_data.get('stats', {})
                except Exception as ce:
                    self.logger.error(f"獲取 Comment Sync 數據失敗: {ce}")

        except Exception as e:
            self.logger.error(f"獲取 Issue Copier 數據失敗: {e}")

        # 從 Issue Scorer 獲取數據
        try:
            response = requests.get(f"{self.issue_scorer_url}/api/scores", timeout=5)
            if response.status_code == 200:
                data['issue_scorer'] = response.json()
        except Exception as e:
            self.logger.error(f"獲取 Issue Scorer 數據失敗: {e}")

        return data


# ============================================================================
# Flask 應用初始化
# ============================================================================

app = Flask(__name__)
auth = HTTPBasicAuth()
gateway = None

# 用戶認證數據
users = {}


def init_auth():
    """初始化認證用戶"""
    global users
    web_username = os.getenv("WEB_USERNAME", "admin")
    web_password = os.getenv("WEB_PASSWORD", "")

    if web_password:
        users[web_username] = generate_password_hash(web_password)
        app.logger.info(f"Web 認證已啟用，用戶名: {web_username}")
    else:
        app.logger.warning("WEB_PASSWORD 未設置，Web UI 將不需要認證")


@auth.verify_password
def verify_password(username, password):
    """驗證用戶名和密碼"""
    if not users:
        return True

    if username in users and check_password_hash(users[username], password):
        return username
    return None


# ============================================================================
# 註冊所有 Routes
# ============================================================================

# Health Check
@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        "status": "healthy",
        "service": "Workspace Monitor Gateway",
        "timestamp": datetime.now().isoformat()
    })


# API Routes
@app.route('/api/dashboard', methods=['GET'])
@auth.login_required
def api_dashboard():
    """獲取 Dashboard 數據（聚合）"""
    return get_dashboard(gateway)


@app.route('/api/webhooks', methods=['GET'])
@auth.login_required
def api_webhooks():
    """獲取 Webhook 歷史記錄"""
    return get_webhooks(gateway)


@app.route('/webhook', methods=['POST'])
@app.route('/webhook/', methods=['POST'])
def webhook():
    """GitHub webhook 端點 - 路由到對應服務"""
    return handle_webhook(gateway)


@app.route('/api/issue-scorer/scores', methods=['GET'])
@auth.login_required
def api_issue_scorer_scores():
    """代理 Issue Scorer 的評分數據 API"""
    return proxy_issue_scorer_scores(gateway)


@app.route('/api/issue-scorer/scores/<path:score_id>/feedback', methods=['POST'])
@auth.login_required
def api_update_score_feedback(score_id):
    """更新評分記錄的使用者反饋"""
    return update_score_feedback(gateway, score_id)


@app.route('/api/issue-scorer/scores/<path:score_id>/ignore', methods=['POST'])
@auth.login_required
def api_toggle_score_ignore(score_id):
    """切換評分記錄的忽略狀態"""
    return toggle_score_ignore(gateway, score_id)


@app.route('/api/all-scores', methods=['GET'])
@auth.login_required
def api_all_scores():
    """統一評分統計 API - 包含 Issue 和 PR 評分"""
    return get_all_scores(gateway)


@app.route('/api/all-scores/<path:score_id>', methods=['DELETE'])
@auth.login_required
def api_delete_score_record(score_id):
    """刪除評分記錄"""
    return delete_score_record(gateway, score_id)


# Page Routes
@app.route('/', methods=['GET'])
@auth.login_required
def page_index():
    """主頁 - 統一 Dashboard"""
    return index()


@app.route('/pr-tasks')
@auth.login_required
def page_pr_tasks():
    """PR 審查任務列表頁面"""
    return pr_tasks_page()


@app.route('/issue-copies')
@auth.login_required
def page_issue_copies():
    """Issue 複製記錄頁面"""
    return issue_copies_page()


@app.route('/comment-syncs')
@auth.login_required
def page_comment_syncs():
    """評論同步記錄頁面"""
    return comment_syncs_page()


@app.route('/history')
@auth.login_required
def page_history():
    """Webhook 歷史記錄頁面"""
    return history_page()


@app.route('/issue-scores')
@auth.login_required
def page_issue_scores():
    """Issue 品質評分頁面"""
    return issue_scores_page()


@app.route('/all-scores')
@auth.login_required
def page_all_scores():
    """統一評分統計頁面 - Issue 和 PR 評分"""
    return all_scores_page()


@app.route('/scorer-config')
@auth.login_required
def page_scorer_config():
    """評分配置管理頁面"""
    return scorer_config_page()


@app.route('/api/scorer-config', methods=['GET'])
@auth.login_required
def api_get_scorer_config():
    """獲取評分配置 API"""
    return get_scorer_config(gateway)


@app.route('/api/scorer-config', methods=['POST'])
@auth.login_required
def api_update_scorer_config():
    """更新評分配置 API"""
    return update_scorer_config(gateway)


@app.route('/feedback-analytics')
@auth.login_required
def page_feedback_analytics():
    """反饋學習分析頁面"""
    return get_feedback_analytics(gateway)


@app.route('/api/feedback/patterns', methods=['GET'])
@auth.login_required
def api_feedback_patterns():
    """獲取反饋模式 API"""
    return get_feedback_patterns_api(gateway)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """主程序入口"""
    global gateway

    try:
        # 初始化 Gateway
        gateway = WorkspaceGateway()

        # 初始化認證
        init_auth()

        # 獲取配置
        host = os.getenv("GATEWAY_HOST", "0.0.0.0")
        port = int(os.getenv("GATEWAY_PORT", "8080"))
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

        gateway.logger.info(f"啟動 Gateway 服務器: {host}:{port}")

        # 啟動 Flask 應用
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        print(f"啟動失敗: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
