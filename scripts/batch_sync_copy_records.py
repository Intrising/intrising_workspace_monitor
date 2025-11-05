#!/usr/bin/env python3
"""
批量補充缺失的 issue 複製記錄到資料庫
掃描所有目標 repo 中的 [LT#] issues，並將缺失的記錄補充到資料庫
分批處理以避免 GitHub API 限制
"""

import os
import sys
import re
import time
from datetime import datetime
from github import Github, GithubException
from dotenv import load_dotenv

# 添加 src 目錄到路徑
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(parent_dir, 'src'))
sys.path.insert(0, '/app')  # 在 Docker 容器中
from database import TaskDatabase

load_dotenv()

def main():
    # 初始化
    db_path = '/var/lib/github-monitor/tasks.db'

    # 如果不在 Docker 容器中，使用本地路徑
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'github_monitor.db')

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

    print('=' * 60)
    print('批量補充 Issue 複製記錄')
    print('=' * 60)
    print()

    # 步驟 1: 掃描所有目標 repo
    print('步驟 1/3: 掃描所有目標 repo 中的 [LT#] issues...\n')

    all_copies = {}  # {source_num: [(target_repo, target_num, target_url), ...]}

    for repo_name in target_repos:
        print(f'掃描 {repo_name}...', end=' ')
        sys.stdout.flush()

        try:
            # 搜尋標題中包含 [LT# 的 issues
            search_results = gh.search_issues(f'repo:{repo_name} is:issue "[LT#" in:title', sort='created', order='desc')

            count = 0
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
                    count += 1

            print(f'找到 {count} 個 issues')

            # 避免 API 限制
            time.sleep(2)

        except GithubException as e:
            print(f'錯誤: {e}')
            if e.status == 403:
                print('  API 限制，等待 60 秒...')
                time.sleep(60)

    print(f'\n總共找到 {len(all_copies)} 個來源 issues\n')

    # 步驟 2: 檢查缺失的記錄
    print('步驟 2/3: 檢查缺失的記錄...\n')

    missing_records = []

    for source_num in sorted(all_copies.keys(), reverse=True):
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
                missing_records.append({
                    'source_num': source_num,
                    'target_repo': copy['target_repo'],
                    'target_number': copy['target_number'],
                    'target_url': copy['target_url']
                })

    print(f'發現 {len(missing_records)} 筆缺失的記錄\n')

    # 步驟 3: 批量補充記錄
    print('步驟 3/3: 批量補充記錄...\n')

    added_count = 0
    failed_count = 0
    skipped_count = 0

    # 只處理最近的 200 筆（避免過度使用 API）
    records_to_add = missing_records[:200]

    if len(missing_records) > 200:
        skipped_count = len(missing_records) - 200
        print(f'⚠️  只處理最近的 200 筆記錄，跳過 {skipped_count} 筆較舊的記錄\n')

    for i, record in enumerate(records_to_add, 1):
        source_num = record['source_num']
        target_repo = record['target_repo']
        target_number = record['target_number']
        target_url = record['target_url']

        print(f'[{i}/{len(records_to_add)}] test-Lantech #{source_num} -> {target_repo} #{target_number}', end=' ')
        sys.stdout.flush()

        try:
            # 獲取來源 issue 資訊
            source_issue = gh.get_repo('Intrising/test-Lantech').get_issue(source_num)

            # 創建記錄
            record_id = f'Intrising/test-Lantech#{source_num}->{target_repo}@{datetime.now().timestamp()}'

            db.create_copy_record({
                'record_id': record_id,
                'source_repo': 'Intrising/test-Lantech',
                'source_issue_number': source_num,
                'source_issue_title': source_issue.title,
                'source_issue_url': source_issue.html_url,
                'source_labels': [label.name for label in source_issue.labels],
                'target_repo': target_repo,
                'target_issue_number': target_number,
                'target_issue_url': target_url,
                'status': 'success',
                'images_count': 0
            })

            added_count += 1
            print('✓')

            # 每 10 筆休息一下，避免 API 限制
            if i % 10 == 0:
                time.sleep(2)

        except GithubException as e:
            failed_count += 1
            print(f'✗ GitHub API 錯誤: {e.status}')

            if e.status == 403:
                print('  API 限制，等待 60 秒...')
                time.sleep(60)
            elif e.status == 404:
                print('  Issue 不存在，跳過')

        except Exception as e:
            failed_count += 1
            print(f'✗ 錯誤: {e}')

    # 總結
    print()
    print('=' * 60)
    print('完成！')
    print('=' * 60)
    print(f'總缺失記錄: {len(missing_records)}')
    print(f'成功添加:   {added_count}')
    print(f'添加失敗:   {failed_count}')
    print(f'跳過處理:   {skipped_count}')
    print()

if __name__ == '__main__':
    main()
