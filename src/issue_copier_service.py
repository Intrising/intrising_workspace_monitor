#!/usr/bin/env python3
"""
Issue Copier 微服務
專門處理 Issue 自動複製和評論同步
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict
from flask import Flask, request, jsonify
from github import Github
from dotenv import load_dotenv
import yaml

# 導入共享模組
from database import TaskDatabase
from issue_copier import IssueCopier


class IssueCopierService:
    """Issue Copier 微服務"""

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

        # Issue Copier 配置
        issue_copy_config = self.config.get('issue_copy', {})

        # 初始化 Issue Copier
        if issue_copy_config.get('enabled', False):
            self.issue_copier = IssueCopier(
                config=issue_copy_config,
                github_client=self.github,
                logger=self.logger,
                database=self.db
            )
            self.logger.info("Issue Copier 已啟用")
        else:
            self.issue_copier = None
            self.logger.warning("Issue Copier 未啟用")

        self.logger.info("Issue Copier 服務初始化完成")

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

        self.logger = logging.getLogger("IssueCopier")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(handler)

    def process_webhook(self, event_type: str, payload: Dict) -> Dict:
        """處理 webhook 事件"""
        if not self.issue_copier:
            return {
                "status": "skipped",
                "reason": "Issue Copier not enabled"
            }

        try:
            # 處理 Issue 事件
            if event_type == 'issues':
                result = self.issue_copier.process_issue_event(event_type, payload)
                return result

            # 處理評論事件
            elif event_type == 'issue_comment':
                result = self.issue_copier.process_comment_event(event_type, payload)
                return result

            else:
                return {
                    "status": "skipped",
                    "reason": f"Unsupported event type: {event_type}"
                }

        except Exception as e:
            self.logger.error(f"處理 webhook 失敗: {e}", exc_info=True)
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
        "service": "Issue Copier",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 Issue webhook"""
    try:
        event_type = request.headers.get('X-GitHub-Event', '')
        payload = request.json

        if event_type not in ['issues', 'issue_comment']:
            return jsonify({"error": "Invalid event type"}), 400

        result = service.process_webhook(event_type, payload)
        return jsonify(result), 200

    except Exception as e:
        service.logger.error(f"Webhook 處理失敗: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/issue-copies', methods=['GET'])
def get_issue_copies():
    """獲取 Issue 複製記錄"""
    try:
        limit = request.args.get('limit', 100, type=int)
        status = request.args.get('status')

        records = service.db.get_copy_records(limit=limit, status=status)
        stats = service.db.get_copy_stats()

        return jsonify({
            'total': len(records),
            'records': records,
            'stats': stats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/comment-syncs', methods=['GET'])
def get_comment_syncs():
    """獲取評論同步記錄"""
    try:
        limit = request.args.get('limit', 50, type=int)
        status = request.args.get('status')

        records = service.db.get_comment_sync_records(limit=limit, status=status)
        stats = service.db.get_comment_sync_stats()

        return jsonify({
            'total': len(records),
            'records': records,
            'stats': stats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """獲取統計數據"""
    try:
        copy_stats = service.db.get_copy_stats()
        comment_stats = service.db.get_comment_sync_stats()

        return jsonify({
            'issue_copies': copy_stats,
            'comment_syncs': comment_stats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    """主程序"""
    global service

    try:
        # 初始化服務
        service = IssueCopierService()

        # 獲取配置
        host = os.getenv("SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("SERVICE_PORT", "8082"))
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

        service.logger.info(f"啟動 Issue Copier 服務: {host}:{port}")

        # 啟動 Flask
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        print(f"啟動失敗: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
