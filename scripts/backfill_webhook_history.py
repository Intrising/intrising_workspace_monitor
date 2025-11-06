#!/usr/bin/env python3
"""
回填 webhook 歷史記錄
從現有的 review_tasks, issue_copy_records, comment_sync_records 表中提取資料
"""
import sqlite3
import uuid
import os

def backfill_webhook_history():
    db_path = os.getenv("DB_PATH", "/var/lib/github-monitor/tasks.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("開始回填 webhook 歷史記錄...")

    # 1. 從 review_tasks 回填 PR webhook 事件
    print("\n處理 PR 審查任務...")
    cursor.execute("""
        SELECT task_id, repo, pr_number, pr_title, pr_author, status, created_at, error_message
        FROM review_tasks
        ORDER BY created_at DESC
    """)

    pr_tasks = cursor.fetchall()
    print(f"找到 {len(pr_tasks)} 個 PR 審查任務")

    pr_count = 0
    for task in pr_tasks:
        event_id = f"pull_request-{task['repo']}-{task['pr_number']}-{str(uuid.uuid4())[:8]}"

        # 檢查是否已存在
        cursor.execute("SELECT event_id FROM webhook_events WHERE event_id = ?", (event_id,))
        if cursor.fetchone():
            continue

        try:
            cursor.execute("""
                INSERT INTO webhook_events
                (event_id, event_type, repo_name, pr_number, issue_number, action, sender,
                 payload, processed_by, status, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                'pull_request',
                task['repo'],
                task['pr_number'],
                None,
                'opened',
                task['pr_author'],
                f'{{"pull_request": {{"title": "{task["pr_title"]}", "number": {task["pr_number"]}}}}}',
                'pr-reviewer',
                'processed' if task['status'] in ('completed', 'success') else 'failed',
                task['error_message'],
                task['created_at']
            ))
            pr_count += 1
        except Exception as e:
            print(f"錯誤插入 PR 事件 {event_id}: {e}")
            continue

    conn.commit()
    print(f"✓ 成功回填 {pr_count} 個 PR webhook 事件")

    # 2. 從 issue_copy_records 回填 Issue webhook 事件
    print("\n處理 Issue 複製記錄...")
    cursor.execute("""
        SELECT record_id, source_repo, source_issue_number, target_repo, target_issue_number,
               status, created_at, error_message
        FROM issue_copy_records
        ORDER BY created_at DESC
    """)

    issue_records = cursor.fetchall()
    print(f"找到 {len(issue_records)} 個 Issue 複製記錄")

    issue_count = 0
    for record in issue_records:
        event_id = f"issues-{record['source_repo']}-{record['source_issue_number']}-{str(uuid.uuid4())[:8]}"

        cursor.execute("SELECT event_id FROM webhook_events WHERE event_id = ?", (event_id,))
        if cursor.fetchone():
            continue

        try:
            cursor.execute("""
                INSERT INTO webhook_events
                (event_id, event_type, repo_name, pr_number, issue_number, action, sender,
                 payload, processed_by, status, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                'issues',
                record['source_repo'],
                None,
                record['source_issue_number'],
                'opened',
                'unknown',
                f'{{"issue": {{"number": {record["source_issue_number"]}}}}}',
                'issue-copier',
                'processed' if record['status'] == 'success' else 'failed',
                record['error_message'],
                record['created_at']
            ))
            issue_count += 1
        except Exception as e:
            print(f"錯誤插入 Issue 事件 {event_id}: {e}")
            continue

    conn.commit()
    print(f"✓ 成功回填 {issue_count} 個 Issue webhook 事件")

    # 3. 從 comment_sync_records 回填 Comment webhook 事件
    print("\n處理評論同步記錄...")
    cursor.execute("""
        SELECT sync_id, source_repo, source_issue_number, comment_author, synced_count,
               status, created_at, error_message
        FROM comment_sync_records
        ORDER BY created_at DESC
    """)

    comment_records = cursor.fetchall()
    print(f"找到 {len(comment_records)} 個評論同步記錄")

    comment_count = 0
    for record in comment_records:
        event_id = f"issue_comment-{record['source_repo']}-{record['source_issue_number']}-{str(uuid.uuid4())[:8]}"

        cursor.execute("SELECT event_id FROM webhook_events WHERE event_id = ?", (event_id,))
        if cursor.fetchone():
            continue

        try:
            cursor.execute("""
                INSERT INTO webhook_events
                (event_id, event_type, repo_name, pr_number, issue_number, action, sender,
                 payload, processed_by, status, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                'issue_comment',
                record['source_repo'],
                None,
                record['source_issue_number'],
                'created',
                record['comment_author'],
                f'{{"issue": {{"number": {record["source_issue_number"]}}}, "comment": {{"user": {{"login": "{record["comment_author"]}"}}}}}}',
                'issue-copier',
                'processed' if record['status'] == 'success' else 'failed',
                record['error_message'],
                record['created_at']
            ))
            comment_count += 1
        except Exception as e:
            print(f"錯誤插入 Comment 事件 {event_id}: {e}")
            continue

    conn.commit()
    conn.close()
    print(f"✓ 成功回填 {comment_count} 個評論 webhook 事件")

    print(f"\n✅ 回填完成！")
    print(f"   - PR 事件: {pr_count}")
    print(f"   - Issue 事件: {issue_count}")
    print(f"   - Comment 事件: {comment_count}")
    print(f"   - 總計: {pr_count + issue_count + comment_count} 個事件")

if __name__ == '__main__':
    backfill_webhook_history()
