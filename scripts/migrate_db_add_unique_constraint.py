#!/usr/bin/env python3
"""
資料庫遷移腳本：添加唯一約束索引前清理重複記錄
"""
import sqlite3
import sys
from datetime import datetime

DB_PATH = "/var/lib/github-monitor/tasks.db"

def migrate_database():
    """執行資料庫遷移"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("開始遷移資料庫...")

        # 1. 找出所有重複的記錄組合
        cursor.execute("""
            SELECT source_repo, source_issue_number, target_repo, COUNT(*) as count
            FROM issue_copy_records
            GROUP BY source_repo, source_issue_number, target_repo
            HAVING COUNT(*) > 1
        """)

        duplicates = cursor.fetchall()
        print(f"\n找到 {len(duplicates)} 組重複記錄")

        # 2. 對每組重複記錄，只保留最早的一條（created_at 最小）
        for source_repo, source_issue_number, target_repo, count in duplicates:
            print(f"\n處理重複: {source_repo}#{source_issue_number} -> {target_repo} ({count} 條記錄)")

            # 找出所有該組的記錄
            cursor.execute("""
                SELECT record_id, created_at, status, target_issue_number, target_issue_url
                FROM issue_copy_records
                WHERE source_repo = ? AND source_issue_number = ? AND target_repo = ?
                ORDER BY created_at ASC
            """, (source_repo, source_issue_number, target_repo))

            records = cursor.fetchall()

            # 保留第一條（最早的），刪除其他的
            keep_record = records[0]
            print(f"  保留記錄: {keep_record[0]} (創建於 {keep_record[1]}, status={keep_record[2]})")

            for record in records[1:]:
                print(f"  刪除記錄: {record[0]} (創建於 {record[1]}, status={record[2]})")
                cursor.execute("DELETE FROM issue_copy_records WHERE record_id = ?", (record[0],))

        # 3. 提交刪除操作
        conn.commit()
        print(f"\n✓ 已清理重複記錄")

        # 4. 嘗試創建唯一約束索引
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_copy_unique_source_target
                ON issue_copy_records(source_repo, source_issue_number, target_repo)
            """)
            conn.commit()
            print("✓ 已創建唯一約束索引")
        except sqlite3.IntegrityError as e:
            print(f"✗ 創建唯一約束失敗: {e}")
            print("  可能還有其他重複記錄，請手動檢查")
            return False

        # 5. 驗證結果
        cursor.execute("""
            SELECT COUNT(*) FROM issue_copy_records
        """)
        total_count = cursor.fetchone()[0]
        print(f"\n遷移完成！資料庫中共有 {total_count} 條記錄")

        conn.close()
        return True

    except Exception as e:
        print(f"\n✗ 遷移失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"資料庫路徑: {DB_PATH}")
    print("=" * 60)

    success = migrate_database()
    sys.exit(0 if success else 1)
