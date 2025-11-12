#!/usr/bin/env python3
"""
Workspace Monitor Gateway - Route Handlers
包含所有 Flask route 處理函數（不含 @app.route decorator）
"""

from datetime import datetime
from flask import request, jsonify
import requests
from typing import Dict
from urllib.parse import quote

from gateway_templates import (
    index_template,
    pr_tasks_template,
    issue_copies_template,
    comment_syncs_template,
    history_template,
    issue_scores_template,
    all_scores_template,
    scorer_config_template
)


# ============================================================================
# API Routes
# ============================================================================

def get_dashboard(gateway) -> Dict:
    """獲取 Dashboard 數據（聚合）"""
    data = gateway.get_aggregated_data()
    return jsonify(data)


def get_webhooks(gateway) -> tuple:
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
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def handle_webhook(gateway) -> tuple:
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


def proxy_issue_scorer_scores(gateway) -> tuple:
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


def update_score_feedback(gateway, score_id: str) -> tuple:
    """更新評分記錄的使用者反饋"""
    try:
        data = request.json
        # URL encode the score_id for forwarding to issue-scorer
        encoded_score_id = quote(score_id, safe='')
        response = requests.post(
            f"{gateway.issue_scorer_url}/api/scores/{encoded_score_id}/feedback",
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


def toggle_score_ignore(gateway, score_id: str) -> tuple:
    """切換評分記錄的忽略狀態"""
    try:
        data = request.json
        # URL encode the score_id for forwarding to issue-scorer
        encoded_score_id = quote(score_id, safe='')
        response = requests.post(
            f"{gateway.issue_scorer_url}/api/scores/{encoded_score_id}/ignore",
            json=data,
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to toggle ignore status"}), response.status_code
    except Exception as e:
        gateway.logger.error(f"切換忽略狀態失敗: {e}")
        return jsonify({"error": str(e)}), 500


def get_all_scores(gateway) -> tuple:
    """統一評分統計 API - 包含 Issue 和 PR 評分"""
    try:
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
                    # 過濾：只保留 2025-11-07 之後的記錄（包含被忽略的記錄）
                    if created_at >= cutoff_date:
                        all_scores.append({
                            'type': 'issue',
                            'score_id': record.get('score_id'),  # 加入 score_id 用於刪除
                            'score': record.get('overall_score'),
                            'author': record.get('author'),
                            'repo': record.get('repo_name'),
                            'number': record.get('issue_number'),
                            'url': record.get('issue_url'),
                            'title': record.get('title'),
                            'created_at': created_at,
                            'content_type': record.get('content_type'),  # 'issue' or 'comment'
                            'ignored': record.get('ignored', False)  # 加入忽略狀態
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


def delete_score_record(gateway, score_id: str) -> tuple:
    """刪除評分記錄"""
    try:
        # URL encode the score_id for forwarding to issue-scorer
        encoded_score_id = quote(score_id, safe='')
        response = requests.delete(
            f"{gateway.issue_scorer_url}/api/scores/{encoded_score_id}",
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to delete score record"}), response.status_code
    except Exception as e:
        gateway.logger.error(f"刪除評分記錄失敗: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Page Routes
# ============================================================================

def index() -> str:
    """主頁 - 統一 Dashboard"""
    return index_template()


def pr_tasks_page() -> str:
    """PR 審查任務列表頁面"""
    return pr_tasks_template()


def issue_copies_page() -> str:
    """Issue 複製記錄頁面"""
    return issue_copies_template()


def comment_syncs_page() -> str:
    """評論同步記錄頁面"""
    return comment_syncs_template()


def history_page() -> str:
    """Webhook 歷史記錄頁面"""
    return history_template()


def issue_scores_page() -> str:
    """Issue 品質評分頁面"""
    return issue_scores_template()


def all_scores_page() -> str:
    """統一評分統計頁面 - Issue 和 PR 評分"""
    return all_scores_template()


def scorer_config_page() -> str:
    """評分配置管理頁面"""
    return scorer_config_template()


def get_scorer_config(gateway) -> tuple:
    """獲取評分配置"""
    try:
        response = requests.get(f"{gateway.issue_scorer_url}/api/config", timeout=10)
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to fetch config"}), response.status_code
    except Exception as e:
        gateway.logger.error(f"獲取評分配置失敗: {e}")
        return jsonify({"error": str(e)}), 500


def update_scorer_config(gateway) -> tuple:
    """更新評分配置"""
    try:
        data = request.json
        response = requests.post(
            f"{gateway.issue_scorer_url}/api/config",
            json=data,
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to update config"}), response.status_code
    except Exception as e:
        gateway.logger.error(f"更新評分配置失敗: {e}")
        return jsonify({"error": str(e)}), 500


def get_feedback_analytics(gateway) -> str:
    """反饋分析頁面"""
    try:
        # 獲取統計數據
        response = requests.get(
            f"{gateway.issue_scorer_url}/api/feedback/statistics?days=30",
            timeout=10
        )
        stats = response.json().get('data', {}) if response.status_code == 200 else {}

        # 獲取見解
        response = requests.get(
            f"{gateway.issue_scorer_url}/api/feedback/insights?days=30",
            timeout=10
        )
        insights = response.json().get('data', {}) if response.status_code == 200 else {}

        # 獲取反饋列表
        response = requests.get(
            f"{gateway.issue_scorer_url}/api/feedback/list?days=30&limit=20",
            timeout=10
        )
        feedbacks = response.json().get('data', []) if response.status_code == 200 else []

        from gateway_templates import feedback_analytics_template
        return feedback_analytics_template(stats, insights, feedbacks)

    except Exception as e:
        gateway.logger.error(f"獲取反饋分析失敗: {e}")
        return f"<h1>Error</h1><p>{str(e)}</p>"


def get_feedback_patterns_api(gateway) -> tuple:
    """獲取反饋模式 API"""
    try:
        days = request.args.get('days', 30, type=int)
        response = requests.get(
            f"{gateway.issue_scorer_url}/api/feedback/patterns?days={days}",
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to fetch patterns"}), response.status_code
    except Exception as e:
        gateway.logger.error(f"獲取反饋模式失敗: {e}")
        return jsonify({"error": str(e)}), 500
