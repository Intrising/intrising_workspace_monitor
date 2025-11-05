#!/usr/bin/env python3
"""
同步缺失的 issue 複製記錄到資料庫
掃描所有目標 repo 中的 [LT#] issues，並將缺失的記錄補充到資料庫
"""

import os
import sys
import re
from datetime import datetime
from github import Github
from dotenv import load_dotenv

# 添加 src 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from database import TaskDatabase

load_dotenv()

def main():
    # 初始化
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'github_monitor.db')

    # 如果在 Docker 容器中，使用容器路徑
    if os.path.exists('/var/lib/github-monitor/tasks.db'):
        db_path = '/var/lib/github-monitor/tasks.db'

    db = TaskDatabase(db_path)
    gh = Github(os.getenv('GITHUB_TOKEN'))

    # 目標 repositories
    target_repos = [
        'Intrising/QA-Switch-OS2',
        'Intrising/QA-Switch-OS3OS4',
        'Intrising/QA-Switch-OS5',
        'Intrising/QA-Viewer',
        'Intrising/test-switch'
    ]

    print('開始掃描所有目標 repo 中的 [LT#] issues...\n')

    # 收集所有複製的 issues
    all_copies = {}  # {source_num: [(target_repo, target_num, target_url), ...]}

    for repo_name in target_repos:
        print(f'掃描 {repo_name}...')
        try:
            # 搜尋標題中包含 [LT# 的 issues
            search_results = gh.search_issues(f'repo:{repo_name} is:issue "[LT#" in:title')

            for result in search_results:
                # 從標題提取來源 issue 編號
                match = re.search(r'\[LT#(\d+)\]', result.title)
                if match:
                    source_num = int(match.group(1))
                    if source_num not in all_copies:
                        all_copies[source_num] = []

                    all_copies[source_num].append({
                        'target_repo': repo_name,
                        'target_number': result.number,
                        'target_url': result.html_url
                    })

            print(f'  找到 {search_results.totalCount} 個 issues')

        except Exception as e:
            print(f'  錯誤: {e}')

    print(f'\n總共找到 {len(all_copies)} 個來源 issues\n')

    # 檢查資料庫中缺失的記錄
    missing_count = 0
    added_count = 0

    for source_num in sorted(all_copies.keys()):
        for copy in all_copies[source_num]:
            # 檢查資料庫中是否已有記錄
            existing_records = db.search_copy_records(
                source_repo='Intrising/test-Lantech',
                target_repo=copy['target_repo'],
                source_issue_number=source_num
            )

            # 檢查是否有成功的記錄
            has_record = any(r.get('status') == 'success' for r in existing_records)

            if not has_record:
                missing_count += 1
                print(f'缺失記錄: test-Lantech #{source_num} -> {copy["target_repo"]} #{copy["target_number"]}')

                try:
                    # 獲取來源 issue 資訊
                    source_issue = gh.get_repo('Intrising/test-Lantech').get_issue(source_num)

                    # 創建記錄
                    record_id = f'Intrising/test-Lantech#{source_num}->{copy["target_repo"]}@{datetime.now().timestamp()}'

                    db.create_copy_record({
                        'record_id': record_id,
                        'source_repo': 'Intrising/test-Lantech',
                        'source_issue_number': source_num,
                        'source_issue_title': source_issue.title,
                        'source_issue_url': source_issue.html_url,
                        'source_labels': [label.name for label in source_issue.labels],
                        'target_repo': copy['target_repo'],
                        'target_issue_number': copy['target_number'],
                        'target_issue_url': copy['target_url'],
                        'status': 'success',
                        'images_count': 0,
                        'created_at': source_issue.created_at.isoformat()
                    })

                    added_count += 1
                    print(f'  ✓ 已添加')

                except Exception as e:
                    print(f'  ✗ 添加失敗: {e}')

    print(f'\n完成！')
    print(f'  缺失記錄: {missing_count}')
    print(f'  成功添加: {added_count}')

if __name__ == '__main__':
    main()
