#!/usr/bin/env python3
"""
健康檢查腳本
檢查 PR Monitor 服務是否正常運行
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def check_process_running() -> bool:
    """檢查主進程是否運行"""
    try:
        # 檢查是否有 pr_monitor.py 進程
        import subprocess
        result = subprocess.run(
            ['pgrep', '-f', 'pr_monitor.py'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"檢查進程失敗: {e}", file=sys.stderr)
        return False


def check_log_activity(log_path: str, max_age_minutes: int = 10) -> bool:
    """檢查日誌文件是否有最近的活動"""
    try:
        log_file = Path(log_path)
        if not log_file.exists():
            print(f"日誌文件不存在: {log_path}", file=sys.stderr)
            return False

        # 檢查最後修改時間
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        age = datetime.now() - mtime

        if age > timedelta(minutes=max_age_minutes):
            print(f"日誌文件超過 {max_age_minutes} 分鐘未更新", file=sys.stderr)
            return False

        return True
    except Exception as e:
        print(f"檢查日誌失敗: {e}", file=sys.stderr)
        return False


def check_github_api() -> bool:
    """檢查 GitHub API 連接"""
    try:
        import requests
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("GITHUB_TOKEN 未設置", file=sys.stderr)
            return False

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(
            "https://api.github.com/rate_limit",
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            print(f"GitHub API 返回錯誤: {response.status_code}", file=sys.stderr)
            return False

        data = response.json()
        remaining = data.get("rate", {}).get("remaining", 0)

        if remaining < 10:
            print(f"GitHub API 配額即將用盡: {remaining}", file=sys.stderr)
            return False

        return True
    except Exception as e:
        print(f"檢查 GitHub API 失敗: {e}", file=sys.stderr)
        return False


def main():
    """主檢查邏輯"""
    checks = []

    # 基本進程檢查
    if check_process_running():
        checks.append(("進程運行", True))
    else:
        checks.append(("進程運行", False))

    # 日誌活動檢查
    log_path = os.getenv("LOG_FILE", "/var/log/github-monitor/app.log")
    if os.path.exists(log_path):
        log_ok = check_log_activity(log_path)
        checks.append(("日誌活動", log_ok))
    else:
        checks.append(("日誌活動", None))  # 日誌文件不存在不視為錯誤

    # GitHub API 連接檢查
    if check_github_api():
        checks.append(("GitHub API", True))
    else:
        checks.append(("GitHub API", False))

    # 輸出結果
    all_ok = all(status for _, status in checks if status is not None)

    for check_name, status in checks:
        if status is True:
            print(f"✓ {check_name}: OK")
        elif status is False:
            print(f"✗ {check_name}: FAILED")
        else:
            print(f"- {check_name}: SKIPPED")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
