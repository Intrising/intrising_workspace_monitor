#!/usr/bin/env python3
"""
測試 Issue Copier 功能
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

def test_issue_webhook():
    """測試發送 issue webhook 到本地服務"""

    # Webhook URL
    webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:5000/webhook")

    print(f"測試 Issue Webhook")
    print(f"目標 URL: {webhook_url}")
    print("-" * 60)

    # 模擬 GitHub issue webhook payload
    # 這是一個 "opened" 事件的範例
    payload = {
        "action": "opened",
        "issue": {
            "number": 123,
            "title": "測試 Issue - 自動複製功能",
            "body": """## 問題描述

這是一個測試 issue，用於測試自動複製功能。

### 步驟重現
1. 執行測試程式
2. 檢查結果
3. 驗證圖片是否正確複製

### 預期結果
- Issue 應該被複製到對應的 repository
- 圖片應該被重新上傳
- Labels 應該被保留

### 測試圖片
![Test Image](https://via.placeholder.com/150)

### 額外資訊
- 環境: Production
- 版本: 1.0.0
""",
            "labels": [
                {"name": "OS3"},
                {"name": "bug"},
                {"name": "high-priority"}
            ],
            "html_url": "https://github.com/Intrising/test-Lantech/issues/123",
            "user": {
                "login": "test-user"
            }
        },
        "repository": {
            "full_name": "Intrising/test-Lantech",
            "name": "test-Lantech",
            "owner": {
                "login": "Intrising"
            }
        }
    }

    # 設置 headers
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues",
        "X-Hub-Signature-256": "sha256=test_signature"  # 測試時可能需要關閉簽名驗證
    }

    print("發送 payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("-" * 60)

    try:
        # 發送 POST 請求
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=30
        )

        print(f"\n響應狀態碼: {response.status_code}")
        print(f"響應內容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print("\n✅ 測試成功！")
                print(f"   來源 Issue: {result.get('source_issue')}")
                print(f"   目標 Repositories: {', '.join(result.get('target_repos', []))}")
                print(f"   已複製的 URLs:")
                for url in result.get('copied_urls', []):
                    print(f"   - {url}")
            else:
                print(f"\n⚠️  狀態: {result.get('status')}")
                print(f"   原因: {result.get('reason', 'N/A')}")
        else:
            print(f"\n❌ 測試失敗！HTTP {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("\n❌ 連接失敗！請確認服務是否正在運行。")
        print(f"   提示: 請先啟動服務 (python src/pr_reviewer.py)")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")


def test_labeled_event():
    """測試 labeled 事件（當 issue 被添加 label 時）"""

    webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:5000/webhook")

    print(f"\n測試 Issue Labeled Event")
    print(f"目標 URL: {webhook_url}")
    print("-" * 60)

    payload = {
        "action": "labeled",
        "issue": {
            "number": 456,
            "title": "測試 Issue - Labeled 事件",
            "body": "這個 issue 是透過添加 label 觸發的",
            "labels": [
                {"name": "OS5"},
                {"name": "enhancement"}
            ],
            "html_url": "https://github.com/Intrising/test-Lantech/issues/456"
        },
        "label": {
            "name": "OS5"
        },
        "repository": {
            "full_name": "Intrising/test-Lantech"
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues",
        "X-Hub-Signature-256": "sha256=test_signature"
    }

    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)

        print(f"\n響應狀態碼: {response.status_code}")
        print(f"響應內容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

        if response.status_code == 200:
            print("\n✅ Labeled 事件測試成功！")
        else:
            print(f"\n❌ 測試失敗！")

    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")


def main():
    """主函數"""
    print("=" * 60)
    print("Issue Copier 測試工具")
    print("=" * 60)

    # 測試 opened 事件
    test_issue_webhook()

    # 等待一下
    print("\n" + "=" * 60)
    input("按 Enter 繼續測試 labeled 事件...")

    # 測試 labeled 事件
    test_labeled_event()

    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
