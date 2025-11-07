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


# Flask 應用
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


@app.route('/', methods=['GET'])
@auth.login_required
def index():
    """主頁 - 統一 Dashboard"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Workspace Monitor - Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .services {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .service-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .service-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 2px solid #eee;
            }
            .service-title {
                font-size: 1.5em;
                font-weight: bold;
                color: #333;
            }
            .service-status {
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                font-weight: bold;
            }
            .status-online { background: #32cd32; color: white; }
            .status-offline { background: #dc143c; color: white; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-bottom: 15px;
            }
            .stat-box {
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                margin-top: 5px;
                font-size: 0.9em;
            }
            .view-details {
                display: inline-block;
                margin-top: 15px;
                padding: 8px 20px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background 0.3s;
            }
            .view-details:hover {
                background: #764ba2;
            }
            .refresh-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #667eea;
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 50px;
                font-size: 1em;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: all 0.3s;
            }
            .refresh-btn:hover {
                background: #764ba2;
                transform: translateY(-2px);
                box-shadow: 0 6px 8px rgba(0,0,0,0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Workspace Monitor Dashboard</h1>

                        <div class="nav">
                <a href="/" class="active">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="services" id="services">
                <!-- 動態載入 -->
            </div>
        </div>

        <button class="refresh-btn" onclick="loadData()">🔄 重新整理</button>

        <script>
            async function loadData() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    const services = document.getElementById('services');

                    // PR Reviewer Card
                    const prData = data.pr_reviewer || {};
                    const prOnline = prData.total !== undefined;
                    const prStats = prData.stats || {};
                    // 計算實際總數（從 stats 計算）
                    const prTotal = (prStats.queued || 0) + (prStats.processing || 0) + (prStats.completed || 0) + (prStats.failed || 0);

                    // Issue Copier Card
                    const issueData = data.issue_copier || {};
                    const issueOnline = issueData.total !== undefined;
                    const issueStats = issueData.stats || {};

                    // Comment Sync Card
                    const commentStats = issueData.comment_stats || {};
                    const commentOnline = commentStats.total !== undefined;

                    // Issue Scorer Card
                    const scorerData = data.issue_scorer || {};
                    const scorerOnline = scorerData.total !== undefined;
                    const scorerStats = scorerData.stats || {};

                    services.innerHTML = `
                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">🤖 PR Auto-Reviewer</div>
                                <span class="service-status status-${prOnline ? 'online' : 'offline'}">
                                    ${prOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${prOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${prTotal}</div>
                                        <div class="stat-label">總任務數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${prStats.processing || 0}</div>
                                        <div class="stat-label">處理中</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${prStats.completed || 0}</div>
                                        <div class="stat-label">已完成</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${prStats.failed || 0}</div>
                                        <div class="stat-label">失敗</div>
                                    </div>
                                </div>
                                <a href="/pr-tasks" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>

                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">📋 Issue Auto-Copier</div>
                                <span class="service-status status-${issueOnline ? 'online' : 'offline'}">
                                    ${issueOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${issueOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.total || 0}</div>
                                        <div class="stat-label">總複製數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.success || 0}</div>
                                        <div class="stat-label">成功</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.failed || 0}</div>
                                        <div class="stat-label">失敗</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.total_images || 0}</div>
                                        <div class="stat-label">圖片處理</div>
                                    </div>
                                </div>
                                <a href="/issue-copies" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>

                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">💬 Comment Sync</div>
                                <span class="service-status status-${commentOnline ? 'online' : 'offline'}">
                                    ${commentOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${commentOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.total || 0}</div>
                                        <div class="stat-label">評論同步數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.total_synced || 0}</div>
                                        <div class="stat-label">已同步次數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.success || 0}</div>
                                        <div class="stat-label">成功</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.failed || 0}</div>
                                        <div class="stat-label">失敗</div>
                                    </div>
                                </div>
                                <a href="/comment-syncs" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>

                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">📊 Issue Quality Scorer</div>
                                <span class="service-status status-${scorerOnline ? 'online' : 'offline'}">
                                    ${scorerOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${scorerOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.total || 0}</div>
                                        <div class="stat-label">總評分數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.completed || 0}</div>
                                        <div class="stat-label">已完成</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.average_score !== null ? scorerStats.average_score : 'N/A'}</div>
                                        <div class="stat-label">平均分數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.processing || 0}</div>
                                        <div class="stat-label">處理中</div>
                                    </div>
                                </div>
                                <a href="/issue-scores" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>
                    `;

                } catch (error) {
                    console.error('載入數據失敗:', error);
                }
            }

            // 頁面載入時執行
            loadData();

            // 自動刷新（每 5 秒）
            setInterval(loadData, 5000);
        </script>
    </body>
    </html>
    """
    return html


@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        "status": "healthy",
        "service": "Workspace Monitor Gateway",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/dashboard', methods=['GET'])
@auth.login_required
def get_dashboard():
    """獲取 Dashboard 數據（聚合）"""
    data = gateway.get_aggregated_data()
    return jsonify(data)


@app.route('/api/webhooks', methods=['GET'])
@auth.login_required
def get_webhooks():
    """獲取 Webhook 歷史記錄"""
    try:
        limit = request.args.get('limit', 100, type=int)
        event_type = request.args.get('event_type')
        status = request.args.get('status')

        events = gateway.db.get_webhook_events(limit=limit, event_type=event_type, status=status)
        stats = gateway.db.get_webhook_stats()

        return jsonify({
            'total': len(events),
            'events': events,
            'stats': stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/webhook', methods=['POST'])
@app.route('/webhook/', methods=['POST'])
def webhook():
    """GitHub webhook 端點 - 路由到對應服務"""
    try:
        # 驗證簽名
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not gateway.verify_webhook_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 401

        # 獲取事件類型
        event_type = request.headers.get('X-GitHub-Event', '')
        payload = request.json

        # 記錄收到的事件
        repo_name = payload.get('repository', {}).get('full_name', 'unknown')
        gateway.logger.info(f"收到 webhook: 事件類型={event_type}, repository={repo_name}")

        # 路由到對應服務
        result = gateway.route_webhook(event_type, payload)

        return jsonify(result), 200

    except Exception as e:
        gateway.logger.error(f"Webhook 處理失敗: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/issue-scorer/scores', methods=['GET'])
@auth.login_required
def proxy_issue_scorer_scores():
    """代理 Issue Scorer 的評分數據 API"""
    try:
        limit = request.args.get('limit', 50, type=int)
        response = requests.get(f"{gateway.issue_scorer_url}/api/scores?limit={limit}", timeout=10)
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to fetch scores"}), response.status_code
    except Exception as e:
        gateway.logger.error(f"代理 Issue Scorer API 失敗: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/issue-scorer/scores/<score_id>/feedback', methods=['POST'])
@auth.login_required
def update_score_feedback(score_id):
    """更新評分記錄的使用者反饋"""
    try:
        data = request.json
        response = requests.post(
            f"{gateway.issue_scorer_url}/api/scores/{score_id}/feedback",
            json=data,
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to update feedback"}), response.status_code
    except Exception as e:
        gateway.logger.error(f"更新反饋失敗: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/all-scores', methods=['GET'])
@auth.login_required
def get_all_scores():
    """統一評分統計 API - 包含 Issue 和 PR 評分"""
    try:
        from datetime import datetime

        limit = request.args.get('limit', 100, type=int)
        # 只統計 2025-11-07 之後的評分
        cutoff_date = "2025-11-07"

        all_scores = []

        # 獲取 Issue 評分記錄
        try:
            issue_response = requests.get(f"{gateway.issue_scorer_url}/api/scores?limit={limit}", timeout=10)
            if issue_response.status_code == 200:
                issue_data = issue_response.json()
                for record in issue_data.get('scores', []):
                    created_at = record.get('created_at', '')
                    # 過濾：只保留 2025-11-07 之後的記錄
                    if created_at >= cutoff_date:
                        all_scores.append({
                            'type': 'issue',
                            'score': record.get('overall_score'),
                            'author': record.get('author'),
                            'repo': record.get('repo_name'),
                            'number': record.get('issue_number'),
                            'url': record.get('issue_url'),
                            'title': record.get('title'),
                            'created_at': created_at,
                            'content_type': record.get('content_type')  # 'issue' or 'comment'
                        })
        except Exception as e:
            gateway.logger.error(f"獲取 Issue 評分失敗: {e}")

        # 獲取 PR 評分記錄
        try:
            pr_response = requests.get(f"{gateway.pr_reviewer_url}/api/tasks?limit={limit}", timeout=10)
            if pr_response.status_code == 200:
                pr_data = pr_response.json()
                for record in pr_data.get('tasks', []):
                    created_at = record.get('created_at', '')
                    # 過濾：只保留 2025-11-07 之後且有評分的記錄
                    if record.get('score') and created_at >= cutoff_date:
                        all_scores.append({
                            'type': 'pr',
                            'score': record.get('score'),
                            'author': record.get('pr_author'),
                            'repo': record.get('repo'),
                            'number': record.get('pr_number'),
                            'url': record.get('pr_url'),
                            'title': record.get('pr_title'),
                            'created_at': created_at,
                            'content_type': 'pull_request'
                        })
        except Exception as e:
            gateway.logger.error(f"獲取 PR 評分失敗: {e}")

        # 按時間排序（最新的在前面）
        all_scores.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # 限制數量
        all_scores = all_scores[:limit]

        return jsonify({
            'total': len(all_scores),
            'scores': all_scores
        }), 200

    except Exception as e:
        gateway.logger.error(f"獲取統一評分數據失敗: {e}")
        return jsonify({"error": str(e)}), 500


# PR 審查任務頁面
@app.route('/pr-tasks')
@auth.login_required
def pr_tasks_page():
    """PR 審查任務列表頁面"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PR 審查任務 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .task-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .task-item:last-child { border-bottom: none; }
            .task-info h3 {
                color: #333;
                margin-bottom: 5px;
            }
            .task-info h3 a:hover {
                color: #4a90e2 !important;
                text-decoration: underline !important;
            }
            .task-info p {
                color: #666;
                font-size: 0.9em;
            }
            .task-info p a:hover {
                text-decoration: underline !important;
            }
            .status {
                padding: 5px 15px;
                border-radius: 15px;
                font-size: 0.85em;
                font-weight: bold;
            }
            .status.queued { background: #ffd93d; color: #333; }
            .status.pending { background: #ffd93d; color: #333; }
            .status.processing { background: #6bcf7f; color: white; }
            .status.completed { background: #4a90e2; color: white; }
            .status.failed { background: #e74c3c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 PR 審查任務</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks" class="active">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">審查任務列表</h2>
                <div id="tasks">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            async function loadTasks() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    // 計算總任務數
                    const stats = data.pr_reviewer.stats;
                    const total = (stats.queued || 0) + (stats.processing || 0) + (stats.completed || 0) + (stats.failed || 0);

                    // 顯示統計
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${total}</h3>
                            <p>總任務數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.queued || 0}</h3>
                            <p>待處理</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.processing || 0}</h3>
                            <p>處理中</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.completed || 0}</h3>
                            <p>已完成</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.failed || 0}</h3>
                            <p>失敗</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 顯示任務列表
                    const tasks = data.pr_reviewer.tasks;
                    if (tasks.length === 0) {
                        document.getElementById('tasks').innerHTML = '<p style="text-align: center; color: #666;">暫無任務</p>';
                        return;
                    }

                    const tasksHtml = tasks.map(task => {
                        // 顯示評分（如果有的話）
                        let scoreDisplay = '';
                        if (task.score !== null && task.score !== undefined && task.status === 'completed') {
                            scoreDisplay = `<span style="padding: 5px 15px; background: #667eea; color: white; border-radius: 15px; font-weight: bold;">${task.score}/100</span>`;
                        }

                        // PR 編號連結（優先使用 review_comment_url）
                        const prLink = task.review_comment_url
                            ? `<a href="${task.review_comment_url}" target="_blank" style="color: #4a90e2; text-decoration: none;" title="查看審查評論">#${task.pr_number} 📝</a>`
                            : `#${task.pr_number}`;

                        return `
                        <div class="task-item">
                            <div class="task-info">
                                <h3>
                                    <a href="${task.pr_url}" target="_blank" style="color: #333; text-decoration: none;">${task.pr_title}</a>
                                </h3>
                                <p>
                                    <strong>倉庫:</strong> ${task.repo} |
                                    <strong>PR:</strong> ${prLink} |
                                    <strong>作者:</strong> ${task.pr_author} |
                                    <strong>創建時間:</strong> ${new Date(task.created_at).toLocaleString('zh-TW')}
                                </p>
                                ${task.error_message ? `<p style="color: red;">錯誤: ${task.error_message}</p>` : ''}
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                ${scoreDisplay}
                                <span class="status ${task.status}">${getStatusText(task.status)}</span>
                            </div>
                        </div>
                        `;
                    }).join('');

                    document.getElementById('tasks').innerHTML = tasksHtml;
                } catch (error) {
                    document.getElementById('tasks').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            function getStatusText(status) {
                const statusMap = {
                    'queued': '待處理',
                    'pending': '待處理',
                    'processing': '處理中',
                    'completed': '已完成',
                    'failed': '失敗'
                };
                return statusMap[status] || status;
            }

            // 初始載入
            loadTasks();

            // 每30秒自動刷新
            setInterval(loadTasks, 30000);
        </script>
    </body>
    </html>
    """
    return html


# Issue 複製頁面
@app.route('/issue-copies')
@auth.login_required
def issue_copies_page():
    """Issue 複製記錄頁面"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Issue 複製記錄 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .record-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .record-item:last-child { border-bottom: none; }
            .record-info h3 {
                color: #333;
                margin-bottom: 10px;
            }
            .record-info p {
                color: #666;
                font-size: 0.9em;
                margin: 5px 0;
            }
            .record-info a {
                color: #4a90e2;
                text-decoration: none;
            }
            .record-info a:hover {
                text-decoration: underline;
            }
            .status {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: bold;
                margin-left: 10px;
            }
            .status.success { background: #6bcf7f; color: white; }
            .status.failed { background: #e74c3c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .labels {
                margin-top: 8px;
            }
            .label {
                display: inline-block;
                padding: 2px 8px;
                margin: 2px;
                border-radius: 10px;
                font-size: 0.75em;
                background: #f0f0f0;
                color: #333;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Issue 複製記錄</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies" class="active">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">複製記錄 (最近 50 筆)</h2>
                <div id="records">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            async function loadRecords() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    // 顯示統計
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.total}</h3>
                            <p>Issue 複製數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.success}</h3>
                            <p>複製成功</p>
                        </div>
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.failed}</h3>
                            <p>複製失敗</p>
                        </div>
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.total_images}</h3>
                            <p>圖片處理</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 顯示記錄列表
                    const records = data.issue_copier.records;
                    if (records.length === 0) {
                        document.getElementById('records').innerHTML = '<p style="text-align: center; color: #666;">暫無記錄</p>';
                        return;
                    }

                    const recordsHtml = records.map(record => `
                        <div class="record-item">
                            <div class="record-info">
                                <h3>
                                    ${record.source_issue_title}
                                    <span class="status ${record.status}">${record.status === 'success' ? '✓ 成功' : '✗ 失敗'}</span>
                                </h3>
                                <p>
                                    <strong>來源:</strong> <a href="${record.source_issue_url}" target="_blank">${record.source_repo}#${record.source_issue_number}</a> →
                                    <strong>目標:</strong> <a href="${record.target_issue_url}" target="_blank">${record.target_repo}#${record.target_issue_number}</a>
                                </p>
                                <p>
                                    <strong>創建時間:</strong> ${new Date(record.created_at).toLocaleString('zh-TW')}
                                    ${record.completed_at ? ` | <strong>完成時間:</strong> ${new Date(record.completed_at).toLocaleString('zh-TW')}` : ''}
                                    ${record.images_count > 0 ? ` | <strong>圖片:</strong> ${record.images_count} 張` : ''}
                                </p>
                                ${record.source_labels && record.source_labels.length > 0 ? `
                                    <div class="labels">
                                        ${record.source_labels.map(label => `<span class="label">${label}</span>`).join('')}
                                    </div>
                                ` : ''}
                                ${record.error_message ? `<p style="color: red; margin-top: 5px;">錯誤: ${record.error_message}</p>` : ''}
                            </div>
                        </div>
                    `).join('');

                    document.getElementById('records').innerHTML = recordsHtml;

                } catch (error) {
                    document.getElementById('records').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            // 初始載入
            loadRecords();

            // 每30秒自動刷新
            setInterval(loadRecords, 30000);
        </script>
    </body>
    </html>
    """
    return html


# Comment Syncs 頁面
@app.route('/comment-syncs')
@auth.login_required
def comment_syncs_page():
    """評論同步記錄頁面"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>評論同步記錄 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .record-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .record-item:last-child { border-bottom: none; }
            .record-info h3 {
                color: #333;
                margin-bottom: 10px;
            }
            .record-info p {
                color: #666;
                font-size: 0.9em;
                margin: 5px 0;
            }
            .record-info a {
                color: #4a90e2;
                text-decoration: none;
            }
            .record-info a:hover {
                text-decoration: underline;
            }
            .status {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: bold;
                margin-left: 10px;
            }
            .status.success { background: #6bcf7f; color: white; }
            .status.failed { background: #e74c3c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .comment-body {
                color: #666;
                font-style: italic;
                margin-top: 8px;
                padding: 8px;
                background: #f9f9f9;
                border-left: 3px solid #f093fb;
                border-radius: 4px;
            }
            .synced-repos {
                margin-top: 8px;
            }
            .repo-badge {
                display: inline-block;
                padding: 4px 10px;
                margin: 2px;
                background: #e3f2fd;
                color: #1976d2;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 500;
                text-decoration: none;
                transition: background 0.2s, transform 0.2s;
            }
            a.repo-badge:hover {
                background: #bbdefb;
                transform: translateY(-2px);
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💬 評論同步記錄</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs" class="active">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">同步記錄 (最近 50 筆)</h2>
                <div id="records">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            async function loadRecords() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    // 顯示統計
                    const commentStats = data.issue_copier.comment_stats || {};
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${commentStats.total || 0}</h3>
                            <p>評論同步數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${commentStats.total_synced || 0}</h3>
                            <p>已同步次數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${commentStats.success || 0}</h3>
                            <p>成功</p>
                        </div>
                        <div class="stat-box">
                            <h3>${commentStats.failed || 0}</h3>
                            <p>失敗</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 顯示 Comment Sync 記錄
                    const commentSyncs = data.issue_copier.comment_syncs || [];
                    if (commentSyncs.length === 0) {
                        document.getElementById('records').innerHTML = '<p style="text-align: center; color: #666;">暫無評論同步記錄</p>';
                        return;
                    }

                    const recordsHtml = commentSyncs.slice(0, 50).map(sync => `
                        <div class="record-item">
                            <div class="record-info">
                                <h3>
                                    💬 ${sync.comment_author} 的評論
                                    <span class="status ${sync.status}">${sync.status === 'success' ? '✓ 成功' : '✗ 失敗'}</span>
                                </h3>
                                <p>
                                    <strong>來源 Issue:</strong> <a href="${sync.source_issue_url}" target="_blank">${sync.source_repo}#${sync.source_issue_number}</a>
                                </p>
                                <div class="synced-repos">
                                    <strong>同步到:</strong>
                                    ${sync.synced_to_repos.map(repo => {
                                        // 從 "Intrising/test-switch#6991" 解析出 URL
                                        const match = repo.match(/^(.+)#(\\d+)$/);
                                        if (match) {
                                            const repoName = match[1];
                                            const issueNum = match[2];
                                            const url = `https://github.com/${repoName}/issues/${issueNum}`;
                                            return `<a href="${url}" target="_blank" class="repo-badge">${repo}</a>`;
                                        }
                                        return `<span class="repo-badge">${repo}</span>`;
                                    }).join(' ')}
                                    <span style="color: #999; font-size: 0.9em;">(${sync.synced_count} 個倉庫)</span>
                                </div>
                                <div class="comment-body">
                                    ${sync.comment_body.length > 300 ? sync.comment_body.substring(0, 300) + '...' : sync.comment_body}
                                </div>
                                <p style="font-size: 0.85em; color: #999; margin-top: 8px;">
                                    <strong>同步時間:</strong> ${new Date(sync.created_at).toLocaleString('zh-TW')}
                                </p>
                                ${sync.error_message ? `<p style="color: red; margin-top: 5px;">錯誤: ${sync.error_message}</p>` : ''}
                            </div>
                        </div>
                    `).join('');

                    document.getElementById('records').innerHTML = recordsHtml;

                } catch (error) {
                    document.getElementById('records').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            // 初始載入
            loadRecords();

            // 每30秒自動刷新
            setInterval(loadRecords, 30000);
        </script>
    </body>
    </html>
    """
    return html



# Webhook History 頁面
@app.route('/history')
@auth.login_required
def history_page():
    """Webhook 歷史記錄頁面"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>Webhook 歷史 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1600px; margin: 0 auto; }
            h1 { color: white; text-align: center; margin-bottom: 30px; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active { background: rgba(255,255,255,0.3); }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stat-box:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            }
            .stat-box:active {
                transform: translateY(-1px);
            }
            .stat-box h3 { font-size: 2em; margin-bottom: 5px; }
            .stat-box p { font-size: 0.9em; opacity: 0.9; }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            th {
                background: #f5f5f5;
                font-weight: 600;
            }
            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 500;
            }
            .badge.pull_request { background: #e3f2fd; color: #1976d2; }
            .badge.issues { background: #fff3e0; color: #f57c00; }
            .badge.issue_comment { background: #f3e5f5; color: #7b1fa2; }
            .badge.processed { background: #e8f5e9; color: #388e3c; }
            .badge.failed { background: #ffebee; color: #d32f2f; }
            .loading { text-align: center; padding: 40px; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📜 Webhook 歷史記錄</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history" class="active">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">Webhook 事件 (最近 100 筆)</h2>
                <div id="events">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            let allEvents = [];
            let currentFilter = { type: null, status: null };

            async function loadHistory() {
                try {
                    const response = await fetch('/api/webhooks?limit=100');
                    const data = await response.json();
                    allEvents = data.events || [];

                    // 顯示統計（帶過濾功能）
                    const stats = data.stats || {};
                    const statsHtml = `
                        <div class="stat-box" onclick="filterEvents(null, null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.total || 0}</h3>
                            <p>總事件數</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents('pull_request', null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_type?.pull_request || 0}</h3>
                            <p>PR 事件</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents('issues', null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_type?.issues || 0}</h3>
                            <p>Issue 事件</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents('issue_comment', null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_type?.issue_comment || 0}</h3>
                            <p>評論事件</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents(null, 'processed')" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_status?.processed || 0}</h3>
                            <p>已處理</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents(null, 'failed')" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_status?.failed || 0}</h3>
                            <p>失敗</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 初始顯示所有事件
                    renderEvents(allEvents);

                } catch (error) {
                    document.getElementById('events').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            function filterEvents(type, status) {
                currentFilter.type = type;
                currentFilter.status = status;

                let filtered = allEvents;

                // 根據事件類型過濾
                if (type) {
                    filtered = filtered.filter(e => e.event_type === type);
                }

                // 根據狀態過濾
                if (status) {
                    filtered = filtered.filter(e => e.status === status);
                }

                renderEvents(filtered);

                // 顯示當前過濾條件
                let filterText = '所有事件';
                if (type || status) {
                    const parts = [];
                    if (type) {
                        const typeNames = {
                            'pull_request': 'PR',
                            'issues': 'Issue',
                            'issue_comment': '評論'
                        };
                        parts.push(typeNames[type] || type);
                    }
                    if (status) {
                        const statusNames = {
                            'processed': '已處理',
                            'failed': '失敗'
                        };
                        parts.push(statusNames[status] || status);
                    }
                    filterText = parts.join(' - ');
                }

                document.querySelector('h2').textContent = `Webhook 事件 (${filterText}: ${filtered.length} 筆)`;
            }

            function renderEvents(events) {
                if (events.length === 0) {
                    document.getElementById('events').innerHTML = '<p style="text-align: center; color: #666;">暫無符合條件的記錄</p>';
                    return;
                }

                const eventsHtml = `
                    <table>
                        <thead>
                            <tr>
                                <th>時間</th>
                                <th>事件類型</th>
                                <th>倉庫</th>
                                <th>PR/Issue</th>
                                <th>動作</th>
                                <th>發送者</th>
                                <th>處理服務</th>
                                <th>狀態</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${events.map(event => `
                                <tr>
                                    <td>${new Date(event.created_at).toLocaleString('zh-TW')}</td>
                                    <td><span class="badge ${event.event_type}">${event.event_type}</span></td>
                                    <td>${event.repo_name || '-'}</td>
                                    <td>${event.pr_number ? '#' + event.pr_number : (event.issue_number ? '#' + event.issue_number : '-')}</td>
                                    <td>${event.action || '-'}</td>
                                    <td>${event.sender || '-'}</td>
                                    <td>${event.processed_by || '-'}</td>
                                    <td><span class="badge ${event.status}">${event.status}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
                document.getElementById('events').innerHTML = eventsHtml;
            }

            // 初始載入
            loadHistory();

            // 每30秒自動刷新
            setInterval(loadHistory, 30000);
        </script>
    </body>
    </html>
    """
    return html


# Issue 評分頁面
@app.route('/issue-scores')
@auth.login_required
def issue_scores_page():
    """Issue 品質評分頁面"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Issue 品質評分 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                display: inline-block;
                padding: 10px 20px;
                margin: 0 5px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                text-decoration: none;
                border-radius: 25px;
                transition: all 0.3s;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255, 255, 255, 0.4);
                transform: translateY(-2px);
            }
            .card {
                background: white;
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-number { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
            .stat-label { font-size: 0.9em; opacity: 0.9; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #999;
                font-size: 1.1em;
            }
            .score-item {
                border-bottom: 1px solid #eee;
                padding: 20px 0;
            }
            .score-item:last-child { border-bottom: none; }
            .score-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .score-title {
                font-size: 1.2em;
                font-weight: 600;
                color: #333;
            }
            .score-meta {
                font-size: 0.9em;
                color: #666;
                margin-bottom: 15px;
            }
            .score-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin: 15px 0;
            }
            .score-dimension {
                background: #f8f9fa;
                padding: 12px;
                border-radius: 8px;
                text-align: center;
            }
            .dimension-label {
                font-size: 0.85em;
                color: #666;
                margin-bottom: 5px;
            }
            .dimension-score {
                font-size: 1.5em;
                font-weight: bold;
                color: #667eea;
            }
            .overall-score {
                font-size: 2em;
                font-weight: bold;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .suggestions {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin-top: 15px;
                border-radius: 5px;
            }
            .suggestions h4 {
                color: #856404;
                margin-bottom: 10px;
            }
            .suggestions ul {
                margin-left: 20px;
                color: #856404;
            }
            .status {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
            }
            .status.completed { background: #d4edda; color: #155724; }
            .status.processing { background: #fff3cd; color: #856404; }
            .status.queued { background: #d1ecf1; color: #0c5460; }
            .status.failed { background: #f8d7da; color: #721c24; }
            .content-type {
                display: inline-block;
                padding: 3px 10px;
                background: #e7f1ff;
                color: #004085;
                border-radius: 12px;
                font-size: 0.8em;
                margin-left: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Issue 品質評分</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores" class="active">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">評分記錄 (最近 50 筆)</h2>
                <div id="scores">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            // HTML 轉義函數
            function escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            async function loadScores() {
                try {
                    // 從 Issue Scorer 服務獲取數據
                    const response = await fetch('/api/issue-scorer/scores?limit=50');
                    const data = await response.json();

                    // 更新統計數據
                    const stats = data.stats || {};
                    const statsHtml = `
                        <div class="stat-box">
                            <div class="stat-number">${stats.total || 0}</div>
                            <div class="stat-label">總評分數</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">${stats.completed || 0}</div>
                            <div class="stat-label">已完成</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">${stats.processing || 0}</div>
                            <div class="stat-label">處理中</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">${stats.average_score !== null && stats.average_score !== undefined ? stats.average_score : 'N/A'}</div>
                            <div class="stat-label">平均分數</div>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 更新評分記錄列表
                    const scores = data.scores || [];
                    if (scores.length === 0) {
                        document.getElementById('scores').innerHTML = '<p style="text-align: center; color: #999;">暫無評分記錄</p>';
                        return;
                    }

                    const scoresHtml = scores.map(score => {
                        const createdAt = new Date(score.created_at).toLocaleString('zh-TW');
                        const statusText = score.status === 'completed' ? '已完成' :
                                         score.status === 'processing' ? '處理中' :
                                         score.status === 'failed' ? '失敗' : '等待中';

                        const scoreDisplay = score.status === 'completed' && score.overall_score
                            ? `${score.overall_score}分`
                            : '';

                        // Issue 編號連結 (優先使用 score_comment_url)
                        const issueLink = score.score_comment_url
                            ? `<a href="${escapeHtml(score.score_comment_url)}" target="_blank" style="color: #667eea; text-decoration: none;" title="查看評分評論">#${score.issue_number}</a>`
                            : `<a href="${escapeHtml(score.issue_url)}" target="_blank" style="color: #667eea; text-decoration: none;">#${score.issue_number}</a>`;

                        const hasDetails = score.status === 'completed' && score.overall_score;
                        const detailsId = `details-${score.score_id.replace(/[^a-zA-Z0-9]/g, '-')}`;

                        return `
                            <div class="score-item">
                                <div class="score-header">
                                    <div>
                                        <a href="${escapeHtml(score.issue_url)}" target="_blank" style="color: #333; text-decoration: none;">
                                            <span class="score-title">${escapeHtml(score.title || 'N/A')}</span>
                                        </a>
                                        <span class="content-type">${score.content_type === 'issue' ? 'Issue' : 'Comment'}</span>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        ${scoreDisplay ? `<span style="padding: 5px 15px; background: #667eea; color: white; border-radius: 15px; font-weight: bold;">${scoreDisplay}</span>` : ''}
                                        <span class="status ${score.status}">${statusText}</span>
                                        ${hasDetails ? `<button onclick="toggleDetails('${detailsId}')" style="padding: 5px 10px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer;">詳細</button>` : ''}
                                    </div>
                                </div>
                                <div class="score-meta">
                                    <strong>倉庫:</strong> ${escapeHtml(score.repo_name)} |
                                    <strong>Issue:</strong> ${issueLink} |
                                    <strong>作者:</strong> ${escapeHtml(score.author)} |
                                    <strong>創建時間:</strong> ${createdAt}
                                </div>
                                ${hasDetails ? `
                                    <div id="${detailsId}" style="display: none; margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 15px;">
                                            <div><strong>📝 格式:</strong> ${score.format_score}分 - ${escapeHtml(score.format_feedback || '')}</div>
                                            <div><strong>📋 內容:</strong> ${score.content_score}分 - ${escapeHtml(score.content_feedback || '')}</div>
                                            <div><strong>🎯 清晰度:</strong> ${score.clarity_score}分 - ${escapeHtml(score.clarity_feedback || '')}</div>
                                            <div><strong>⚙️ 可操作性:</strong> ${score.actionability_score}分 - ${escapeHtml(score.actionability_feedback || '')}</div>
                                        </div>
                                        ${score.suggestions ? `
                                            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 15px; border-radius: 4px;">
                                                <strong style="color: #856404;">💡 改進建議:</strong>
                                                <ul style="margin: 10px 0 0 20px; color: #856404;">
                                                    ${score.suggestions.split('\\n').filter(s => s.trim()).map(s => '<li>' + escapeHtml(s) + '</li>').join('')}
                                                </ul>
                                            </div>
                                        ` : ''}
                                        <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
                                            <label style="display: block; font-weight: bold; margin-bottom: 8px; color: #495057;">
                                                🗣️ 你的意見（用於訓練改進）:
                                            </label>
                                            <textarea id="feedback-${detailsId}" style="width: 100%; min-height: 80px; padding: 10px; border: 1px solid #ced4da; border-radius: 4px; font-size: 14px; resize: vertical;" placeholder="例如：這個評分太高/太低，因為...">${escapeHtml(score.user_feedback || '')}</textarea>
                                            <button onclick="saveFeedback('${score.score_id}', '${detailsId}')" style="margin-top: 10px; padding: 8px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                                                💾 儲存意見
                                            </button>
                                            <span id="feedback-msg-${detailsId}" style="margin-left: 10px; color: #28a745;"></span>
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('');

                    document.getElementById('scores').innerHTML = scoresHtml;

                } catch (error) {
                    console.error('載入評分記錄失敗:', error);
                    document.getElementById('scores').innerHTML = '<p style="color: #dc3545; text-align: center;">載入失敗，請稍後再試</p>';
                }
            }

            // 展開/收合詳細資訊
            function toggleDetails(detailsId) {
                const element = document.getElementById(detailsId);
                if (element.style.display === 'none') {
                    element.style.display = 'block';
                } else {
                    element.style.display = 'none';
                }
            }

            // 儲存使用者反饋
            async function saveFeedback(scoreId, detailsId) {
                const feedbackTextarea = document.getElementById(`feedback-${detailsId}`);
                const messageSpan = document.getElementById(`feedback-msg-${detailsId}`);
                const feedback = feedbackTextarea.value.trim();

                try {
                    const response = await fetch(`/api/issue-scorer/scores/${scoreId}/feedback`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ user_feedback: feedback })
                    });

                    if (response.ok) {
                        messageSpan.textContent = '✅ 已儲存';
                        messageSpan.style.color = '#28a745';
                        setTimeout(() => { messageSpan.textContent = ''; }, 3000);
                    } else {
                        throw new Error('儲存失敗');
                    }
                } catch (error) {
                    messageSpan.textContent = '❌ 儲存失敗';
                    messageSpan.style.color = '#dc3545';
                    console.error('儲存反饋失敗:', error);
                }
            }

            // 頁面載入時執行
            loadScores();

            // 自動刷新（每 30 秒）
            setInterval(loadScores, 30000);
        </script>
    </body>
    </html>
    """
    return html



@app.route('/all-scores')
@auth.login_required
def all_scores_page():
    """統一評分統計頁面 - Issue 和 PR 評分"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>評分統計 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1600px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .score-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .score-item:last-child { border-bottom: none; }
            .score-info h3 {
                color: #333;
                margin-bottom: 5px;
                font-size: 1.1em;
            }
            .score-info p {
                color: #666;
                font-size: 0.9em;
                margin: 3px 0;
            }
            .score-info a {
                color: #4a90e2;
                text-decoration: none;
            }
            .score-info a:hover {
                text-decoration: underline;
            }
            .score-badge {
                padding: 8px 15px;
                border-radius: 20px;
                font-size: 1.2em;
                font-weight: bold;
                min-width: 70px;
                text-align: center;
            }
            .score-90 { background: #6bcf7f; color: white; }
            .score-80 { background: #85e085; color: white; }
            .score-70 { background: #ffd93d; color: #333; }
            .score-60 { background: #ffb84d; color: #333; }
            .score-low { background: #e74c3c; color: white; }
            .type-badge {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: bold;
                margin-left: 10px;
            }
            .type-issue { background: #3498db; color: white; }
            .type-pr { background: #9b59b6; color: white; }
            .type-comment { background: #1abc9c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .filter-tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .filter-tab {
                padding: 10px 20px;
                background: #f0f0f0;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .filter-tab.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 評分統計總覽</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores" class="active">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">人員統計</h2>
                <div class="stats" id="author-stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 15px;">評分記錄</h2>
                <div class="filter-tabs" id="filter-tabs">
                    <button class="filter-tab active" data-filter="all">全部</button>
                    <button class="filter-tab" data-filter="issue">Issue</button>
                    <button class="filter-tab" data-filter="pr">PR</button>
                </div>
                <div id="scores">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            let allScores = [];
            let currentFilter = 'all';

            async function loadScores() {
                try {
                    const response = await fetch('/api/all-scores?limit=200');
                    const data = await response.json();

                    allScores = data.scores || [];

                    // 計算統計數據
                    const totalScores = allScores.length;
                    const avgScore = totalScores > 0 
                        ? Math.round(allScores.reduce((sum, s) => sum + (s.score || 0), 0) / totalScores)
                        : 0;
                    
                    const issueCount = allScores.filter(s => s.type === 'issue').length;
                    const prCount = allScores.filter(s => s.type === 'pr').length;
                    
                    const highScores = allScores.filter(s => s.score >= 80).length;
                    const lowScores = allScores.filter(s => s.score < 60).length;

                    // 按人員統計
                    const byAuthor = {};
                    allScores.forEach(s => {
                        if (!byAuthor[s.author]) {
                            byAuthor[s.author] = { total: 0, sum: 0 };
                        }
                        byAuthor[s.author].total++;
                        byAuthor[s.author].sum += s.score || 0;
                    });

                    // 顯示統計數據
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${totalScores}</h3>
                            <p>總評分數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${avgScore}</h3>
                            <p>平均分數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${issueCount}</h3>
                            <p>Issue 評分</p>
                        </div>
                        <div class="stat-box">
                            <h3>${prCount}</h3>
                            <p>PR 評分</p>
                        </div>
                        <div class="stat-box">
                            <h3>${highScores}</h3>
                            <p>高分 (≥80)</p>
                        </div>
                        <div class="stat-box">
                            <h3>${lowScores}</h3>
                            <p>低分 (<60)</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 按人員統計平均分數（分開顯示）
                    const authorStats = Object.entries(byAuthor)
                        .map(([author, stats]) => ({
                            author,
                            avg: Math.round(stats.sum / stats.total),
                            count: stats.total
                        }))
                        .sort((a, b) => b.avg - a.avg);

                    let authorStatsHtml = '';
                    authorStats.forEach(stat => {
                        authorStatsHtml += `
                            <div class="stat-box">
                                <h3>${stat.avg}</h3>
                                <p>${stat.author} (${stat.count})</p>
                            </div>
                        `;
                    });

                    document.getElementById('author-stats').innerHTML = authorStatsHtml || '<p style="text-align: center; color: #666;">暫無人員統計</p>';

                    // 顯示評分列表
                    renderScores();

                } catch (error) {
                    document.getElementById('scores').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            function renderScores() {
                const filteredScores = currentFilter === 'all' 
                    ? allScores 
                    : allScores.filter(s => s.type === currentFilter);

                if (filteredScores.length === 0) {
                    document.getElementById('scores').innerHTML = '<p style="text-align: center; color: #666;">暫無評分記錄</p>';
                    return;
                }

                const scoresHtml = filteredScores.map(score => {
                    const scoreClass = score.score >= 90 ? 'score-90' :
                                     score.score >= 80 ? 'score-80' :
                                     score.score >= 70 ? 'score-70' :
                                     score.score >= 60 ? 'score-60' : 'score-low';

                    const typeClass = score.type === 'issue' ? 'type-issue' : 
                                    score.content_type === 'comment' ? 'type-comment' : 'type-pr';
                    const typeText = score.type === 'issue' ? 
                                   (score.content_type === 'comment' ? 'Comment' : 'Issue') : 'PR';

                    return `
                        <div class="score-item">
                            <div class="score-info">
                                <h3>
                                    <a href="${score.url}" target="_blank">${score.title || 'N/A'}</a>
                                    <span class="type-badge ${typeClass}">${typeText}</span>
                                </h3>
                                <p>
                                    <strong>作者:</strong> ${score.author} |
                                    <strong>倉庫:</strong> ${score.repo} |
                                    <strong>編號:</strong> <a href="${score.url}" target="_blank">#${score.number}</a> |
                                    <strong>時間:</strong> ${new Date(score.created_at).toLocaleString('zh-TW')}
                                </p>
                                <p>
                                    <strong>連結:</strong> <a href="${score.url}" target="_blank">${score.url}</a>
                                </p>
                            </div>
                            <div class="score-badge ${scoreClass}">${score.score}</div>
                        </div>
                    `;
                }).join('');

                document.getElementById('scores').innerHTML = scoresHtml;
            }

            // 過濾器事件
            document.getElementById('filter-tabs').addEventListener('click', (e) => {
                if (e.target.classList.contains('filter-tab')) {
                    document.querySelectorAll('.filter-tab').forEach(tab => tab.classList.remove('active'));
                    e.target.classList.add('active');
                    currentFilter = e.target.dataset.filter;
                    renderScores();
                }
            });

            // 初始載入
            loadScores();

            // 每30秒自動刷新
            setInterval(loadScores, 30000);
        </script>
    </body>
    </html>
    """
    return html

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
