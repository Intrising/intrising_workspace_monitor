#!/usr/bin/env python3
"""
資料庫管理模組 - 用於存儲 PR 審查任務記錄
使用 SQLite 實現持久化存儲
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager
import threading


class TaskDatabase:
    """PR 審查任務資料庫"""

    def __init__(self, db_path: str = "/var/lib/github-monitor/tasks.db"):
        """
        初始化資料庫

        Args:
            db_path: 資料庫文件路徑
        """
        self.db_path = db_path
        self.logger = logging.getLogger("TaskDatabase")
        self.lock = threading.Lock()

        # 初始化資料庫
        self._init_database()

    def _init_database(self):
        """創建資料表（如果不存在）"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 創建任務表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS review_tasks (
                        task_id TEXT PRIMARY KEY,
                        pr_number INTEGER NOT NULL,
                        repo TEXT NOT NULL,
                        pr_title TEXT,
                        pr_author TEXT,
                        pr_url TEXT,
                        status TEXT NOT NULL,
                        progress INTEGER DEFAULT 0,
                        message TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        completed_at TEXT,
                        error_message TEXT,
                        review_content TEXT
                    )
                """)

                # 創建索引以加速查詢
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status
                    ON review_tasks(status)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at
                    ON review_tasks(created_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_repo_pr
                    ON review_tasks(repo, pr_number)
                """)

                # 創建 issue 複製記錄表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS issue_copy_records (
                        record_id TEXT PRIMARY KEY,
                        source_repo TEXT NOT NULL,
                        source_issue_number INTEGER NOT NULL,
                        source_issue_title TEXT,
                        source_issue_url TEXT,
                        source_labels TEXT,
                        target_repo TEXT NOT NULL,
                        target_issue_number INTEGER,
                        target_issue_url TEXT,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        images_count INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                """)

                # Issue 複製記錄索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_copy_created_at
                    ON issue_copy_records(created_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_copy_source
                    ON issue_copy_records(source_repo, source_issue_number)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_copy_status
                    ON issue_copy_records(status)
                """)

                # 創建唯一約束索引，防止同一個 issue 被重複複製到同一個目標 repo
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_copy_unique_source_target
                    ON issue_copy_records(source_repo, source_issue_number, target_repo)
                """)

                # 創建評論同步記錄表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS comment_sync_records (
                        sync_id TEXT PRIMARY KEY,
                        source_repo TEXT NOT NULL,
                        source_issue_number INTEGER NOT NULL,
                        source_issue_url TEXT,
                        comment_author TEXT,
                        comment_body TEXT,
                        synced_to_repos TEXT,
                        synced_count INTEGER DEFAULT 0,
                        total_targets INTEGER DEFAULT 0,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        created_at TEXT NOT NULL
                    )
                """)

                # 評論同步記錄索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sync_created_at
                    ON comment_sync_records(created_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sync_source
                    ON comment_sync_records(source_repo, source_issue_number)
                """)

                conn.commit()
                self.logger.info(f"資料庫初始化完成: {self.db_path}")

        except Exception as e:
            self.logger.error(f"資料庫初始化失敗: {e}")
            raise

    @contextmanager
    def _get_connection(self):
        """獲取資料庫連接（上下文管理器）"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # 使結果可以通過列名訪問
            yield conn
        finally:
            if conn:
                conn.close()

    def create_task(self, task_data: Dict) -> bool:
        """
        創建新任務

        Args:
            task_data: 任務數據字典

        Returns:
            是否成功
        """
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO review_tasks (
                            task_id, pr_number, repo, pr_title, pr_author,
                            pr_url, status, progress, message, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task_data.get('pr_id') or task_data.get('task_id'),
                        task_data.get('pr_number'),
                        task_data.get('repo'),
                        task_data.get('pr_title'),
                        task_data.get('pr_author'),
                        task_data.get('pr_url'),
                        task_data.get('status', 'queued'),
                        task_data.get('progress', 0),
                        task_data.get('message', '等待處理'),
                        task_data.get('created_at', datetime.now().isoformat()),
                        task_data.get('updated_at', datetime.now().isoformat())
                    ))

                    conn.commit()
                    self.logger.info(f"任務已創建: {task_data.get('pr_id')}")
                    return True

        except sqlite3.IntegrityError:
            # 任務已存在，更新它
            self.logger.warning(f"任務已存在，將更新: {task_data.get('pr_id')}")
            return self.update_task(
                task_data.get('pr_id') or task_data.get('task_id'),
                task_data
            )
        except Exception as e:
            self.logger.error(f"創建任務失敗: {e}")
            return False

    def update_task(self, task_id: str, updates: Dict) -> bool:
        """
        更新任務狀態

        Args:
            task_id: 任務 ID
            updates: 要更新的字段字典

        Returns:
            是否成功
        """
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # 構建更新語句
                    set_clauses = []
                    values = []

                    # 允許更新的字段
                    updatable_fields = [
                        'status', 'progress', 'message', 'pr_title',
                        'pr_author', 'pr_url', 'error_message', 'review_content'
                    ]

                    for field in updatable_fields:
                        if field in updates:
                            set_clauses.append(f"{field} = ?")
                            values.append(updates[field])

                    # 總是更新 updated_at
                    set_clauses.append("updated_at = ?")
                    values.append(updates.get('updated_at', datetime.now().isoformat()))

                    # 如果狀態為 completed，設置 completed_at
                    if updates.get('status') == 'completed':
                        set_clauses.append("completed_at = ?")
                        values.append(datetime.now().isoformat())

                    values.append(task_id)

                    sql = f"""
                        UPDATE review_tasks
                        SET {', '.join(set_clauses)}
                        WHERE task_id = ?
                    """

                    cursor.execute(sql, values)
                    conn.commit()

                    if cursor.rowcount > 0:
                        self.logger.debug(f"任務已更新: {task_id}")
                        return True
                    else:
                        self.logger.warning(f"任務不存在: {task_id}")
                        return False

        except Exception as e:
            self.logger.error(f"更新任務失敗: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        獲取單個任務

        Args:
            task_id: 任務 ID

        Returns:
            任務數據字典或 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM review_tasks WHERE task_id = ?
                """, (task_id,))

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except Exception as e:
            self.logger.error(f"獲取任務失敗: {e}")
            return None

    def get_all_tasks(self, limit: int = 100, status: Optional[str] = None) -> List[Dict]:
        """
        獲取所有任務

        Args:
            limit: 返回的最大任務數
            status: 可選的狀態過濾

        Returns:
            任務列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if status:
                    cursor.execute("""
                        SELECT * FROM review_tasks
                        WHERE status = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (status, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM review_tasks
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"獲取任務列表失敗: {e}")
            return []

    def get_task_stats(self) -> Dict:
        """
        獲取任務統計

        Returns:
            統計數據字典
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT
                        status,
                        COUNT(*) as count
                    FROM review_tasks
                    GROUP BY status
                """)

                stats = {
                    'queued': 0,
                    'processing': 0,
                    'completed': 0,
                    'failed': 0
                }

                for row in cursor.fetchall():
                    stats[row['status']] = row['count']

                return stats

        except Exception as e:
            self.logger.error(f"獲取統計失敗: {e}")
            return {'queued': 0, 'processing': 0, 'completed': 0, 'failed': 0}

    def delete_old_tasks(self, days: int = 30) -> int:
        """
        刪除舊任務（清理數據）

        Args:
            days: 保留最近 N 天的任務

        Returns:
            刪除的任務數
        """
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # 計算日期閾值
                    from datetime import timedelta
                    threshold = (datetime.now() - timedelta(days=days)).isoformat()

                    cursor.execute("""
                        DELETE FROM review_tasks
                        WHERE created_at < ? AND status IN ('completed', 'failed')
                    """, (threshold,))

                    deleted_count = cursor.rowcount
                    conn.commit()

                    if deleted_count > 0:
                        self.logger.info(f"已刪除 {deleted_count} 個舊任務")

                    return deleted_count

        except Exception as e:
            self.logger.error(f"刪除舊任務失敗: {e}")
            return 0

    def search_tasks(self, repo: Optional[str] = None,
                    pr_number: Optional[int] = None,
                    pr_author: Optional[str] = None) -> List[Dict]:
        """
        搜索任務

        Args:
            repo: 倉庫名稱
            pr_number: PR 編號
            pr_author: PR 作者

        Returns:
            匹配的任務列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                conditions = []
                values = []

                if repo:
                    conditions.append("repo = ?")
                    values.append(repo)

                if pr_number:
                    conditions.append("pr_number = ?")
                    values.append(pr_number)

                if pr_author:
                    conditions.append("pr_author = ?")
                    values.append(pr_author)

                if conditions:
                    sql = f"""
                        SELECT * FROM review_tasks
                        WHERE {' AND '.join(conditions)}
                        ORDER BY created_at DESC
                    """
                    cursor.execute(sql, values)
                else:
                    cursor.execute("""
                        SELECT * FROM review_tasks
                        ORDER BY created_at DESC
                    """)

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"搜索任務失敗: {e}")
            return []

    # ==================== Issue Copy Records 方法 ====================

    def create_copy_record(self, record_data: Dict) -> bool:
        """
        創建 issue 複製記錄

        Args:
            record_data: 記錄數據字典

        Returns:
            是否成功（如果因唯一約束而失敗，也返回 False，表示已存在）
        """
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # 將 labels 列表轉為 JSON 字符串
                    labels_json = json.dumps(record_data.get('source_labels', []))

                    cursor.execute("""
                        INSERT INTO issue_copy_records (
                            record_id, source_repo, source_issue_number,
                            source_issue_title, source_issue_url, source_labels,
                            target_repo, target_issue_number, target_issue_url,
                            status, error_message, images_count, created_at, completed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record_data.get('record_id'),
                        record_data.get('source_repo'),
                        record_data.get('source_issue_number'),
                        record_data.get('source_issue_title'),
                        record_data.get('source_issue_url'),
                        labels_json,
                        record_data.get('target_repo'),
                        record_data.get('target_issue_number'),
                        record_data.get('target_issue_url'),
                        record_data.get('status', 'pending'),
                        record_data.get('error_message'),
                        record_data.get('images_count', 0),
                        record_data.get('created_at', datetime.now().isoformat()),
                        record_data.get('completed_at')
                    ))

                    conn.commit()
                    self.logger.info(f"複製記錄已創建: {record_data.get('record_id')}")
                    return True

        except sqlite3.IntegrityError as e:
            # 唯一約束衝突，說明已經有相同的複製記錄
            if "idx_copy_unique_source_target" in str(e) or "UNIQUE constraint failed" in str(e):
                self.logger.warning(f"複製記錄已存在（避免重複）: {record_data.get('source_repo')}#{record_data.get('source_issue_number')} -> {record_data.get('target_repo')}")
                return False
            else:
                self.logger.error(f"創建複製記錄失敗（IntegrityError）: {e}")
                return False
        except Exception as e:
            self.logger.error(f"創建複製記錄失敗: {e}")
            return False

    def update_copy_record(self, record_id: str, updates: Dict) -> bool:
        """
        更新複製記錄

        Args:
            record_id: 記錄 ID
            updates: 要更新的字段字典

        Returns:
            是否成功
        """
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    set_clauses = []
                    values = []

                    updatable_fields = [
                        'target_issue_number', 'target_issue_url', 'status',
                        'error_message', 'images_count'
                    ]

                    for field in updatable_fields:
                        if field in updates:
                            set_clauses.append(f"{field} = ?")
                            values.append(updates[field])

                    # 如果狀態為 success，設置 completed_at
                    if updates.get('status') in ['success', 'failed']:
                        set_clauses.append("completed_at = ?")
                        values.append(datetime.now().isoformat())

                    values.append(record_id)

                    sql = f"""
                        UPDATE issue_copy_records
                        SET {', '.join(set_clauses)}
                        WHERE record_id = ?
                    """

                    cursor.execute(sql, values)
                    conn.commit()

                    if cursor.rowcount > 0:
                        self.logger.debug(f"複製記錄已更新: {record_id}")
                        return True
                    else:
                        self.logger.warning(f"複製記錄不存在: {record_id}")
                        return False

        except Exception as e:
            self.logger.error(f"更新複製記錄失敗: {e}")
            return False

    def get_copy_records(self, limit: int = 100, status: Optional[str] = None) -> List[Dict]:
        """
        獲取複製記錄列表

        Args:
            limit: 返回的最大記錄數
            status: 可選的狀態過濾

        Returns:
            記錄列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if status:
                    cursor.execute("""
                        SELECT * FROM issue_copy_records
                        WHERE status = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (status, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM issue_copy_records
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))

                rows = cursor.fetchall()
                records = []
                for row in rows:
                    record = dict(row)
                    # 將 labels JSON 字符串轉回列表
                    try:
                        record['source_labels'] = json.loads(record.get('source_labels', '[]'))
                    except:
                        record['source_labels'] = []
                    records.append(record)

                return records

        except Exception as e:
            self.logger.error(f"獲取複製記錄失敗: {e}")
            return []

    def get_copy_stats(self) -> Dict:
        """
        獲取複製統計

        Returns:
            統計數據字典
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 總體統計
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(images_count) as total_images
                    FROM issue_copy_records
                """)

                row = cursor.fetchone()
                stats = {
                    'total': row['total'] or 0,
                    'success': row['success'] or 0,
                    'failed': row['failed'] or 0,
                    'pending': row['pending'] or 0,
                    'total_images': row['total_images'] or 0
                }

                # 按來源 repo 統計
                cursor.execute("""
                    SELECT source_repo, COUNT(*) as count
                    FROM issue_copy_records
                    GROUP BY source_repo
                    ORDER BY count DESC
                """)

                stats['by_source_repo'] = {}
                for row in cursor.fetchall():
                    stats['by_source_repo'][row['source_repo']] = row['count']

                # 按目標 repo 統計
                cursor.execute("""
                    SELECT target_repo, COUNT(*) as count
                    FROM issue_copy_records
                    WHERE status = 'success'
                    GROUP BY target_repo
                    ORDER BY count DESC
                """)

                stats['by_target_repo'] = {}
                for row in cursor.fetchall():
                    stats['by_target_repo'][row['target_repo']] = row['count']

                return stats

        except Exception as e:
            self.logger.error(f"獲取複製統計失敗: {e}")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'pending': 0,
                'total_images': 0,
                'by_source_repo': {},
                'by_target_repo': {}
            }

    def search_copy_records(self, source_repo: Optional[str] = None,
                           target_repo: Optional[str] = None,
                           source_issue_number: Optional[int] = None) -> List[Dict]:
        """
        搜索複製記錄

        Args:
            source_repo: 來源倉庫
            target_repo: 目標倉庫
            source_issue_number: 來源 issue 編號

        Returns:
            匹配的記錄列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                conditions = []
                values = []

                if source_repo:
                    conditions.append("source_repo = ?")
                    values.append(source_repo)

                if target_repo:
                    conditions.append("target_repo = ?")
                    values.append(target_repo)

                if source_issue_number:
                    conditions.append("source_issue_number = ?")
                    values.append(source_issue_number)

                if conditions:
                    sql = f"""
                        SELECT * FROM issue_copy_records
                        WHERE {' AND '.join(conditions)}
                        ORDER BY created_at DESC
                    """
                    cursor.execute(sql, values)
                else:
                    cursor.execute("""
                        SELECT * FROM issue_copy_records
                        ORDER BY created_at DESC
                    """)

                rows = cursor.fetchall()
                records = []
                for row in rows:
                    record = dict(row)
                    try:
                        record['source_labels'] = json.loads(record.get('source_labels', '[]'))
                    except:
                        record['source_labels'] = []
                    records.append(record)

                return records

        except Exception as e:
            self.logger.error(f"搜索複製記錄失敗: {e}")
            return []

    # ============ 評論同步記錄相關方法 ============

    def create_comment_sync_record(self, record_data: Dict) -> bool:
        """
        創建評論同步記錄

        Args:
            record_data: 記錄數據字典

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 將同步目標列表轉換為 JSON
                synced_to_repos = json.dumps(record_data.get('synced_to_repos', []))

                cursor.execute("""
                    INSERT INTO comment_sync_records (
                        sync_id, source_repo, source_issue_number, source_issue_url,
                        comment_author, comment_body, synced_to_repos,
                        synced_count, total_targets, status, error_message, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_data['sync_id'],
                    record_data['source_repo'],
                    record_data['source_issue_number'],
                    record_data.get('source_issue_url', ''),
                    record_data.get('comment_author', ''),
                    record_data.get('comment_body', ''),
                    synced_to_repos,
                    record_data.get('synced_count', 0),
                    record_data.get('total_targets', 0),
                    record_data['status'],
                    record_data.get('error_message'),
                    record_data.get('created_at', datetime.now().isoformat())
                ))

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"創建評論同步記錄失敗: {e}")
            return False

    def get_comment_sync_records(self, limit: int = 50, status: str = None) -> List[Dict]:
        """
        獲取評論同步記錄

        Args:
            limit: 返回記錄數量
            status: 過濾狀態（可選）

        Returns:
            記錄列表
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if status:
                    cursor.execute("""
                        SELECT * FROM comment_sync_records
                        WHERE status = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (status, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM comment_sync_records
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))

                rows = cursor.fetchall()
                records = []
                for row in rows:
                    record = dict(row)
                    # 將同步目標 JSON 字符串轉回列表
                    try:
                        record['synced_to_repos'] = json.loads(record.get('synced_to_repos', '[]'))
                    except:
                        record['synced_to_repos'] = []
                    records.append(record)

                return records

        except Exception as e:
            self.logger.error(f"獲取評論同步記錄失敗: {e}")
            return []

    def get_comment_sync_stats(self) -> Dict:
        """
        獲取評論同步統計

        Returns:
            統計數據字典
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 總體統計
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(synced_count) as total_synced,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed
                    FROM comment_sync_records
                """)

                stats_row = cursor.fetchone()
                stats = {
                    'total': stats_row[0] or 0,
                    'total_synced': stats_row[1] or 0,
                    'success': stats_row[2] or 0,
                    'failed': stats_row[3] or 0
                }

                return stats

        except Exception as e:
            self.logger.error(f"獲取評論同步統計失敗: {e}")
            return {
                'total': 0,
                'total_synced': 0,
                'success': 0,
                'failed': 0
            }
