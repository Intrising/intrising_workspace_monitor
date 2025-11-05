#!/usr/bin/env python3
"""
手動觸發 issue 複製
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def trigger_issue_copy(repo, issue_number):
    """手動觸發 issue 複製"""

    webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8080/webhook")
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        print("錯誤: GITHUB_TOKEN 未設置")
        sys.exit(1)

    # 從 GitHub API 獲取 issue 資訊
    api_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    print(f"獲取 issue 資訊: {repo}#{issue_number}")
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        print(f"錯誤: 無法獲取 issue 資訊 (HTTP {response.status_code})")
        print(response.text)
        sys.exit(1)

    issue_data = response.json()

    # 構建 webhook payload
    payload = {
        "action": "labeled",  # 模擬 labeled 事件
        "issue": {
            "number": issue_data["number"],
            "title": issue_data["title"],
            "body": issue_data.get("body", ""),
            "labels": [{"name": label["name"]} for label in issue_data["labels"]],
            "html_url": issue_data["html_url"],
            "user": issue_data["user"]
        },
        "repository": {
            "full_name": repo,
            "name": repo.split("/")[1],
            "owner": {
                "login": repo.split("/")[0]
            }
        }
    }

    print(f"Labels: {', '.join([l['name'] for l in payload['issue']['labels']])}")
    print(f"\n發送 webhook 到: {webhook_url}")

    # 發送 webhook
    webhook_headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues"
    }

    response = requests.post(webhook_url, json=payload, headers=webhook_headers, timeout=30)

    print(f"\n響應狀態: HTTP {response.status_code}")
    print(f"響應內容:")
    print(response.json())

    if response.status_code == 200:
        result = response.json()
        if result.get("status") == "success":
            print("\n✅ Issue 複製成功！")
            print(f"來源: {result.get('source_issue')}")
            print(f"已複製到:")
            for url in result.get('copied_urls', []):
                print(f"  - {url}")
        else:
            print(f"\n⚠️ 狀態: {result.get('status')}")
            print(f"原因: {result.get('reason', 'N/A')}")
    else:
        print(f"\n❌ 請求失敗")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python trigger_issue_copy.py <repo> <issue_number>")
        print("範例: python trigger_issue_copy.py Intrising/test-Lantech 1422")
        sys.exit(1)

    repo = sys.argv[1]
    issue_number = int(sys.argv[2])

    trigger_issue_copy(repo, issue_number)
