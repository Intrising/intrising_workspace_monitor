#!/usr/bin/env python3
"""
GitHub Monitor - 企業級 PR 監控工具
監控 GitHub Pull Requests 並發送警報通知
"""

import os
import sys
import time
import logging
import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import yaml
from dotenv import load_dotenv
from github import Github, GithubException
import requests
import schedule


class PRMonitor:
    """GitHub PR 監控器"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化監控器"""
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

        # Slack 配置
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.slack_channel = os.getenv("SLACK_CHANNEL", "#pr-alerts")

        # Email 配置
        self.email_from = os.getenv("EMAIL_FROM", "github-monitor@example.com")
        self.msmtp_config = os.getenv("MSMTP_CONFIG", "/home/appuser/.msmtprc")

        self.logger.info("PR Monitor 初始化完成")

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
        log_level = os.getenv("LOG_LEVEL", self.config.get("logging", {}).get("level", "INFO"))
        log_format = self.config.get("logging", {}).get("format", "text")

        if log_format == "json":
            formatter = logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        self.logger = logging.getLogger("PRMonitor")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(handler)

        # 文件日誌（如果配置了）
        log_file = self.config.get("logging", {}).get("file")
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"無法創建日誌文件: {e}")

    def check_pr_issues(self, pr) -> List[Dict]:
        """檢查 PR 是否有問題"""
        issues = []
        alert_config = self.config.get("monitor", {}).get("alerts", {})

        # 檢查開啟時間
        open_hours = alert_config.get("open_duration_hours", 24)
        if open_hours > 0:
            created_at = pr.created_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            hours_open = (now - created_at).total_seconds() / 3600

            if hours_open > open_hours:
                issues.append({
                    "type": "open_too_long",
                    "severity": "warning",
                    "message": f"PR 已開啟 {hours_open:.1f} 小時"
                })

        # 檢查是否有 reviewer
        if alert_config.get("no_reviewer", False):
            if pr.requested_reviewers is None or len(pr.requested_reviewers) == 0:
                if pr.requested_teams is None or len(pr.requested_teams) == 0:
                    issues.append({
                        "type": "no_reviewer",
                        "severity": "warning",
                        "message": "沒有指定審查者"
                    })

        # 檢查是否有衝突
        if alert_config.get("has_conflicts", False):
            if pr.mergeable_state == "dirty":
                issues.append({
                    "type": "has_conflicts",
                    "severity": "error",
                    "message": "存在合併衝突"
                })

        # 檢查 CI 狀態
        if alert_config.get("ci_failed", False):
            try:
                # 獲取最新的 commit
                commits = pr.get_commits()
                if commits.totalCount > 0:
                    latest_commit = commits.reversed[0]
                    # 檢查 CI 狀態
                    statuses = latest_commit.get_combined_status()
                    if statuses.state in ["failure", "error"]:
                        issues.append({
                            "type": "ci_failed",
                            "severity": "error",
                            "message": f"CI 檢查失敗: {statuses.state}"
                        })
            except Exception as e:
                self.logger.debug(f"無法獲取 CI 狀態: {e}")

        return issues

    def send_slack_notification(self, pr, issues: List[Dict]):
        """發送 Slack 通知"""
        if not self.slack_webhook:
            self.logger.warning("Slack webhook 未配置，跳過通知")
            return

        # 構建 Slack 消息
        severity_emoji = {
            "error": "🔴",
            "warning": "⚠️",
            "info": "ℹ️"
        }

        issue_lines = []
        for issue in issues:
            emoji = severity_emoji.get(issue["severity"], "•")
            issue_lines.append(f"{emoji} {issue['message']}")

        message = {
            "channel": self.slack_channel,
            "username": "PR Monitor Bot",
            "icon_emoji": ":github:",
            "attachments": [{
                "color": "danger" if any(i["severity"] == "error" for i in issues) else "warning",
                "title": f"PR #{pr.number}: {pr.title}",
                "title_link": pr.html_url,
                "fields": [
                    {
                        "title": "儲存庫",
                        "value": pr.base.repo.full_name,
                        "short": True
                    },
                    {
                        "title": "作者",
                        "value": pr.user.login,
                        "short": True
                    },
                    {
                        "title": "分支",
                        "value": f"{pr.head.ref} → {pr.base.ref}",
                        "short": True
                    },
                    {
                        "title": "發現問題",
                        "value": "\n".join(issue_lines),
                        "short": False
                    }
                ],
                "footer": "GitHub Monitor",
                "ts": int(time.time())
            }]
        }

        try:
            response = requests.post(
                self.slack_webhook,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            self.logger.info(f"已發送 Slack 通知: PR #{pr.number}")
        except Exception as e:
            self.logger.error(f"發送 Slack 通知失敗: {e}")

    def send_email_notification(self, pr, issues: List[Dict]):
        """使用 msmtp 發送郵件通知"""
        email_config = self.config.get("notifications", {}).get("email", {})

        if not email_config.get("enabled", False):
            return

        recipients = email_config.get("recipients", [])
        if not recipients:
            self.logger.warning("Email 收件人列表為空，跳過郵件通知")
            return

        try:
            # 構建郵件內容
            subject = f"[PR Alert] #{pr.number}: {pr.title}"

            # 構建問題列表
            issue_list = []
            for issue in issues:
                severity_icon = {
                    "error": "🔴",
                    "warning": "⚠️",
                    "info": "ℹ️"
                }
                icon = severity_icon.get(issue["severity"], "•")
                issue_list.append(f"  {icon} {issue['message']}")

            # 郵件正文
            body = f"""GitHub Monitor 警報通知

PR 資訊：
  標題: {pr.title}
  編號: #{pr.number}
  URL: {pr.html_url}
  儲存庫: {pr.base.repo.full_name}
  作者: {pr.user.login}
  分支: {pr.head.ref} → {pr.base.ref}

發現的問題：
{chr(10).join(issue_list)}

請及時處理。

---
此郵件由 GitHub Monitor 自動發送
時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            # 使用 msmtp 發送郵件
            for recipient in recipients:
                self._send_email_via_msmtp(
                    to=recipient,
                    subject=subject,
                    body=body
                )

            self.logger.info(f"已發送郵件通知: PR #{pr.number} 到 {len(recipients)} 個收件人")

        except Exception as e:
            self.logger.error(f"發送郵件通知失敗: {e}")

    def _send_email_via_msmtp(self, to: str, subject: str, body: str):
        """使用 msmtp 發送單封郵件"""
        # 構建完整的郵件內容（包含 header）
        email_content = f"""From: {self.email_from}
To: {to}
Subject: {subject}
Content-Type: text/plain; charset=UTF-8

{body}
"""

        try:
            # 調用 msmtp 發送郵件
            process = subprocess.Popen(
                ['msmtp', '-C', self.msmtp_config, '-t'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = process.communicate(email_content.encode('utf-8'))

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise Exception(f"msmtp 執行失敗 (退出碼 {process.returncode}): {error_msg}")

            self.logger.debug(f"郵件已發送至 {to}")

        except FileNotFoundError:
            raise Exception("msmtp 未安裝或不在 PATH 中")
        except Exception as e:
            raise Exception(f"發送郵件至 {to} 失敗: {e}")

    def monitor_repository(self, owner: str, repo: str, branches: List[str]):
        """監控指定的儲存庫"""
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            self.logger.info(f"檢查儲存庫: {owner}/{repo}")

            # 獲取 PR 狀態過濾條件
            pr_states = self.config.get("monitor", {}).get("pr_states", ["open"])

            for state in pr_states:
                pulls = repository.get_pulls(state=state, sort="created", direction="desc")

                for pr in pulls:
                    # 過濾分支
                    if branches and pr.base.ref not in branches:
                        continue

                    # 檢查 PR 問題
                    issues = self.check_pr_issues(pr)

                    if issues:
                        self.logger.warning(
                            f"PR #{pr.number} ({pr.title}) 發現 {len(issues)} 個問題"
                        )

                        # 發送通知
                        if self.config.get("notifications", {}).get("slack", {}).get("enabled", False):
                            self.send_slack_notification(pr, issues)

                        if self.config.get("notifications", {}).get("email", {}).get("enabled", False):
                            self.send_email_notification(pr, issues)
                    else:
                        self.logger.debug(f"PR #{pr.number} 狀態正常")

        except GithubException as e:
            self.logger.error(f"GitHub API 錯誤 ({owner}/{repo}): {e}")
        except Exception as e:
            self.logger.error(f"監控儲存庫時發生錯誤 ({owner}/{repo}): {e}")

    def get_organization_repositories(self, org_name: str) -> List[str]:
        """獲取組織下的所有儲存庫名稱"""
        try:
            org = self.github.get_organization(org_name)
            repos = org.get_repos()
            repo_names = [repo.name for repo in repos]
            self.logger.info(f"組織 {org_name} 下找到 {len(repo_names)} 個儲存庫")
            return repo_names
        except Exception as e:
            self.logger.error(f"無法獲取組織 {org_name} 的儲存庫列表: {e}")
            return []

    def run_check(self):
        """執行一次完整檢查"""
        self.logger.info("=== 開始 PR 檢查 ===")
        start_time = time.time()

        repositories = self.config.get("monitor", {}).get("repositories", [])

        if not repositories:
            self.logger.warning("配置中沒有指定要監控的儲存庫")
            return

        for repo_config in repositories:
            owner = repo_config.get("owner")
            repo = repo_config.get("repo")
            branches = repo_config.get("branches", [])

            # 支持監控整個組織
            monitor_all = repo_config.get("all", False)

            if not owner:
                self.logger.warning(f"儲存庫配置缺少 owner: {repo_config}")
                continue

            # 如果設置了 all: true，監控組織下所有儲存庫
            if monitor_all:
                self.logger.info(f"監控組織 {owner} 下的所有儲存庫")
                org_repos = self.get_organization_repositories(owner)
                for repo_name in org_repos:
                    self.monitor_repository(owner, repo_name, branches)
            elif repo:
                # 監控單個儲存庫
                self.monitor_repository(owner, repo, branches)
            else:
                self.logger.warning(f"儲存庫配置不完整: {repo_config}")
                continue

        elapsed = time.time() - start_time
        self.logger.info(f"=== PR 檢查完成 (耗時 {elapsed:.2f} 秒) ===")

    def start(self):
        """啟動監控服務"""
        check_interval = int(os.getenv(
            "CHECK_INTERVAL",
            self.config.get("monitor", {}).get("check_interval", 300)
        ))

        self.logger.info(f"PR Monitor 啟動中... (檢查間隔: {check_interval} 秒)")

        # 立即執行第一次檢查
        self.run_check()

        # 排程定期檢查
        schedule.every(check_interval).seconds.do(self.run_check)

        # 主循環
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("收到中斷信號，正在停止...")
        except Exception as e:
            self.logger.error(f"發生未預期的錯誤: {e}", exc_info=True)
            sys.exit(1)


def main():
    """主程式入口"""
    try:
        monitor = PRMonitor()
        monitor.start()
    except Exception as e:
        print(f"啟動失敗: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
