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
                        review_content TEXT,
                        score INTEGER,
                        review_comment_url TEXT
                    )
                """)

                # 為現有記錄添加 score 欄位（如果表已存在）
                try:
                    cursor.execute("ALTER TABLE review_tasks ADD COLUMN score INTEGER")
                    self.logger.info("已為 review_tasks 表添加 score 欄位")
                except Exception as e:
                    # 欄位可能已存在，忽略錯誤
                    pass

                # 為現有記錄添加 review_comment_url 欄位（如果表已存在）
                try:
                    cursor.execute("ALTER TABLE review_tasks ADD COLUMN review_comment_url TEXT")
                    self.logger.info("已為 review_tasks 表添加 review_comment_url 欄位")
                except Exception as e:
                    # 欄位可能已存在，忽略錯誤
                    pass

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

                # 創建 webhook 事件記錄表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS webhook_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        repo_name TEXT,
                        pr_number INTEGER,
                        issue_number INTEGER,
                        action TEXT,
                        sender TEXT,
                        payload TEXT,
                        processed_by TEXT,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        created_at TEXT NOT NULL
                    )
                """)

                # Webhook 事件索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_webhook_created_at
                    ON webhook_events(created_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_webhook_type
                    ON webhook_events(event_type, created_at DESC)
                """)

                # 創建 issue 品質評分記錄表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS issue_scores (
                        score_id TEXT PRIMARY KEY,
                        repo_name TEXT NOT NULL,
                        issue_number INTEGER NOT NULL,
                        comment_id INTEGER,
                        event_type TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        title TEXT,
                        body TEXT,
                        author TEXT,
                        issue_url TEXT,
                        format_score INTEGER,
                        format_feedback TEXT,
                        content_score INTEGER,
                        content_feedback TEXT,
                        clarity_score INTEGER,
                        clarity_feedback TEXT,
                        actionability_score INTEGER,
                        actionability_feedback TEXT,
                        overall_score INTEGER,
                        suggestions TEXT,
                        user_feedback TEXT,
                        ignored BOOLEAN DEFAULT 0,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                """)

                # Issue 評分記錄索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_score_created_at
                    ON issue_scores(created_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_score_repo
                    ON issue_scores(repo_name, created_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_score_issue
                    ON issue_scores(repo_name, issue_number, created_at DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_score_status
                    ON issue_scores(status)
                """)

                # 為現有表添加 user_feedback 欄位（如果不存在）
                try:
                    cursor.execute("ALTER TABLE issue_scores ADD COLUMN user_feedback TEXT")
                    self.logger.info("已為 issue_scores 表添加 user_feedback 欄位")
                except Exception:
                    # 欄位可能已存在，忽略錯誤
                    pass

                # 為現有表添加 ignored 欄位（如果不存在）
                try:
                    cursor.execute("ALTER TABLE issue_scores ADD COLUMN ignored BOOLEAN DEFAULT 0")
                    self.logger.info("已為 issue_scores 表添加 ignored 欄位")
                except Exception:
                    # 欄位可能已存在，忽略錯誤
                    pass

                # 創建反饋分析模式表 - 用於學習循環
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback_patterns (
                        pattern_id TEXT PRIMARY KEY,
                        pattern_type TEXT NOT NULL,
                        dimension TEXT,
                        feedback_theme TEXT NOT NULL,
                        occurrence_count INTEGER DEFAULT 1,
                        avg_score_deviation REAL,
                        example_feedbacks TEXT,
                        identified_issue TEXT,
                        suggested_adjustment TEXT,
                        last_seen TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                # 索引用於快速查詢反饋模式
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_pattern_type
                    ON feedback_patterns(pattern_type, occurrence_count DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_dimension
                    ON feedback_patterns(dimension, occurrence_count DESC)
                """)

                # 創建反饋分析快照表 - 存儲定期的聚合分析結果
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback_snapshots (
                        snapshot_id TEXT PRIMARY KEY,
                        snapshot_date TEXT NOT NULL,
                        total_feedbacks INTEGER,
                        positive_count INTEGER,
                        negative_count INTEGER,
                        neutral_count INTEGER,
                        top_issues TEXT,
                        learning_insights TEXT,
                        prompt_adjustments TEXT,
                        created_at TEXT NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_snapshot_date
                    ON feedback_snapshots(snapshot_date DESC)
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
                        'pr_author', 'pr_url', 'error_message', 'review_content',
                        'score', 'review_comment_url'
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

    def record_webhook_event(self, event_data: Dict) -> bool:
        """
        記錄 webhook 事件

        Args:
            event_data: 事件數據字典，包含:
                - event_id: 事件 ID
                - event_type: 事件類型 (pull_request, issues, issue_comment)
                - repo_name: 倉庫名稱
                - pr_number: PR 編號 (可選)
                - issue_number: Issue 編號 (可選)
                - action: 動作 (opened, closed, created, etc.)
                - sender: 發送者
                - payload: 完整的 payload (JSON)
                - processed_by: 處理服務 (pr-reviewer, issue-copier)
                - status: 狀態 (processed, skipped, failed)
                - error_message: 錯誤信息 (可選)

        Returns:
            bool: 是否成功
        """
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO webhook_events (
                            event_id, event_type, repo_name, pr_number, issue_number,
                            action, sender, payload, processed_by, status,
                            error_message, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event_data.get('event_id'),
                        event_data.get('event_type'),
                        event_data.get('repo_name'),
                        event_data.get('pr_number'),
                        event_data.get('issue_number'),
                        event_data.get('action'),
                        event_data.get('sender'),
                        json.dumps(event_data.get('payload', {})),
                        event_data.get('processed_by'),
                        event_data.get('status', 'processed'),
                        event_data.get('error_message'),
                        event_data.get('created_at', datetime.now().isoformat())
                    ))

                    conn.commit()
                    self.logger.debug(f"Webhook 事件已記錄: {event_data.get('event_id')}")
                    return True

        except Exception as e:
            self.logger.error(f"記錄 webhook 事件失敗: {e}")
            return False

    def get_webhook_events(self, limit: int = 100, event_type: str = None, status: str = None) -> List[Dict]:
        """
        獲取 webhook 事件記錄

        Args:
            limit: 返回記錄數量限制
            event_type: 過濾事件類型
            status: 過濾狀態

        Returns:
            List[Dict]: 事件記錄列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 只顯示我們處理的事件類型
                query = "SELECT * FROM webhook_events WHERE event_type IN ('pull_request', 'issues', 'issue_comment')"
                params = []

                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type)

                if status:
                    query += " AND status = ?"
                    params.append(status)

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                events = []
                for row in rows:
                    event = dict(row)
                    # 解析 payload JSON
                    if event.get('payload'):
                        try:
                            event['payload'] = json.loads(event['payload'])
                        except:
                            pass
                    events.append(event)

                return events

        except Exception as e:
            self.logger.error(f"獲取 webhook 事件失敗: {e}")
            return []

    def get_webhook_stats(self) -> Dict:
        """
        獲取 webhook 事件統計

        Returns:
            Dict: 統計信息
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 只統計我們處理的事件類型
                event_filter = "WHERE event_type IN ('pull_request', 'issues', 'issue_comment')"

                # 總事件數
                cursor.execute(f"SELECT COUNT(*) FROM webhook_events {event_filter}")
                total = cursor.fetchone()[0]

                # 按類型統計
                cursor.execute(f"""
                    SELECT event_type, COUNT(*) as count
                    FROM webhook_events
                    {event_filter}
                    GROUP BY event_type
                """)
                by_type = {row[0]: row[1] for row in cursor.fetchall()}

                # 按狀態統計
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM webhook_events
                    {event_filter}
                    GROUP BY status
                """)
                by_status = {row[0]: row[1] for row in cursor.fetchall()}

                # 按處理服務統計
                cursor.execute(f"""
                    SELECT processed_by, COUNT(*) as count
                    FROM webhook_events
                    {event_filter}
                    AND processed_by IS NOT NULL
                    GROUP BY processed_by
                """)
                by_service = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    'total': total,
                    'by_type': by_type,
                    'by_status': by_status,
                    'by_service': by_service
                }

        except Exception as e:
            self.logger.error(f"獲取 webhook 統計失敗: {e}")
            return {
                'total': 0,
                'by_type': {},
                'by_status': {},
                'by_service': {}
            }

    # ==================== Issue Scoring Methods ====================

    def create_score_record(self, score_data: Dict) -> bool:
        """
        創建 issue 評分記錄

        Args:
            score_data: 評分數據字典

        Returns:
            bool: 是否創建成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO issue_scores
                    (score_id, repo_name, issue_number, comment_id, event_type, content_type,
                     title, body, author, issue_url, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    score_data.get('score_id'),
                    score_data.get('repo_name'),
                    score_data.get('issue_number'),
                    score_data.get('comment_id'),
                    score_data.get('event_type'),
                    score_data.get('content_type'),
                    score_data.get('title'),
                    score_data.get('body'),
                    score_data.get('author'),
                    score_data.get('issue_url'),
                    score_data.get('status', 'queued'),
                    now
                ))

                conn.commit()
                self.logger.info(f"創建評分記錄: {score_data.get('score_id')}")
                return True

        except sqlite3.IntegrityError as e:
            self.logger.warning(f"評分記錄已存在: {score_data.get('score_id')}")
            return False
        except Exception as e:
            self.logger.error(f"創建評分記錄失敗: {e}")
            return False

    def update_score_record(self, score_id: str, update_data: Dict) -> bool:
        """
        更新評分記錄

        Args:
            score_id: 評分記錄 ID
            update_data: 要更新的數據

        Returns:
            bool: 是否更新成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 構建 SET 子句
                set_parts = []
                values = []

                for key, value in update_data.items():
                    if key != 'score_id':
                        set_parts.append(f"{key} = ?")
                        values.append(value)

                if not set_parts:
                    return False

                values.append(score_id)

                query = f"UPDATE issue_scores SET {', '.join(set_parts)} WHERE score_id = ?"
                cursor.execute(query, values)
                conn.commit()

                self.logger.info(f"更新評分記錄: {score_id}")
                return True

        except Exception as e:
            self.logger.error(f"更新評分記錄失敗: {e}")
            return False

    def update_score_title(self, repo_name: str, issue_number: int, new_title: str) -> bool:
        """
        更新指定 Issue 的所有評分記錄的標題

        Args:
            repo_name: 倉庫名稱
            issue_number: Issue 編號
            new_title: 新標題

        Returns:
            bool: 是否更新成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    UPDATE issue_scores
                    SET title = ?
                    WHERE repo_name = ? AND issue_number = ?
                """
                cursor.execute(query, (new_title, repo_name, issue_number))
                conn.commit()

                updated_count = cursor.rowcount
                if updated_count > 0:
                    self.logger.info(f"已更新 {updated_count} 筆評分記錄的標題: {repo_name}#{issue_number}")
                return True

        except Exception as e:
            self.logger.error(f"更新評分記錄標題失敗: {e}")
            return False

    def delete_score_record(self, score_id: str) -> bool:
        """
        刪除評分記錄

        Args:
            score_id: 評分記錄 ID

        Returns:
            bool: 是否刪除成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "DELETE FROM issue_scores WHERE score_id = ?"
                cursor.execute(query, (score_id,))
                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.info(f"已刪除評分記錄: {score_id}")
                    return True
                else:
                    self.logger.warning(f"找不到評分記錄: {score_id}")
                    return False

        except Exception as e:
            self.logger.error(f"刪除評分記錄失敗: {e}")
            return False

    def get_score_record(self, score_id: str) -> Optional[Dict]:
        """
        獲取單個評分記錄

        Args:
            score_id: 評分記錄 ID

        Returns:
            評分記錄字典或 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM issue_scores WHERE score_id = ?", (score_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except Exception as e:
            self.logger.error(f"獲取評分記錄失敗: {e}")
            return None

    def get_score_by_comment_id(self, repo_name: str, issue_number: int, comment_id: int) -> List[Dict]:
        """
        根據 comment_id 查找評分記錄

        Args:
            repo_name: Repository 名稱
            issue_number: Issue 編號
            comment_id: Comment ID

        Returns:
            評分記錄列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM issue_scores
                    WHERE repo_name = ? AND issue_number = ? AND comment_id = ?
                    ORDER BY created_at DESC
                """, (repo_name, issue_number, comment_id))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"根據 comment_id 查找評分記錄失敗: {e}")
            return []

    def get_all_score_records(self, limit: int = 100, status: str = None, repo_name: str = None) -> List[Dict]:
        """
        獲取所有評分記錄

        Args:
            limit: 返回記錄數量限制
            status: 按狀態過濾
            repo_name: 按 repository 過濾

        Returns:
            評分記錄列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM issue_scores WHERE 1=1"
                params = []

                if status:
                    query += " AND status = ?"
                    params.append(status)

                if repo_name:
                    query += " AND repo_name = ?"
                    params.append(repo_name)

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"獲取評分記錄失敗: {e}")
            return []

    def check_comment_already_scored(self, repo_name: str, issue_number: int, comment_id: int) -> bool:
        """
        檢查特定 comment 是否已經被評分過

        Args:
            repo_name: Repository 名稱
            issue_number: Issue 編號
            comment_id: Comment ID

        Returns:
            True 如果已經評分過, False 如果還沒有
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM issue_scores
                    WHERE repo_name = ? AND issue_number = ? AND comment_id = ?
                """, (repo_name, issue_number, comment_id))

                result = cursor.fetchone()
                return result['count'] > 0

        except Exception as e:
            self.logger.error(f"檢查 comment 評分狀態失敗: {e}")
            return False

    def get_score_stats(self, repo_name: str = None) -> Dict:
        """
        獲取評分統計

        Args:
            repo_name: 按 repository 過濾

        Returns:
            統計數據字典
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                where_clause = "WHERE (ignored IS NULL OR ignored = 0)"
                params = []

                if repo_name:
                    where_clause += " AND repo_name = ?"
                    params.append(repo_name)

                # 總評分數（排除已忽略的）
                cursor.execute(f"SELECT COUNT(*) FROM issue_scores {where_clause}", params)
                total = cursor.fetchone()[0]

                # 按狀態統計（排除已忽略的）
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM issue_scores
                    {where_clause}
                    GROUP BY status
                """, params)
                by_status = {row[0]: row[1] for row in cursor.fetchall()}

                # 按內容類型統計（排除已忽略的）
                cursor.execute(f"""
                    SELECT content_type, COUNT(*) as count
                    FROM issue_scores
                    {where_clause}
                    GROUP BY content_type
                """, params)
                by_type = {row[0]: row[1] for row in cursor.fetchall()}

                # 平均分數（只計算已完成的且未忽略的）
                cursor.execute(f"""
                    SELECT AVG(overall_score) as avg_score
                    FROM issue_scores
                    {where_clause} AND status = 'completed' AND overall_score IS NOT NULL
                """, params)
                result = cursor.fetchone()
                avg_score = round(result[0], 1) if result[0] is not None else None

                return {
                    'total': total,
                    'queued': by_status.get('queued', 0),
                    'processing': by_status.get('processing', 0),
                    'completed': by_status.get('completed', 0),
                    'failed': by_status.get('failed', 0),
                    'by_type': by_type,
                    'average_score': avg_score
                }

        except Exception as e:
            self.logger.error(f"獲取評分統計失敗: {e}")
            return {
                'total': 0,
                'queued': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'by_type': {},
                'average_score': None
            }

    # ==================== Author History & Statistics Methods ====================

    def get_author_pr_history(self, author: str, limit: int = 20) -> Dict:
        """
        獲取作者的 PR 審查歷史和統計

        Args:
            author: PR 作者名稱
            limit: 返回的最大記錄數

        Returns:
            包含歷史記錄和統計的字典
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 獲取作者的 PR 記錄
                cursor.execute("""
                    SELECT task_id, pr_number, repo, pr_title, pr_url, score,
                           status, created_at, completed_at, review_comment_url
                    FROM review_tasks
                    WHERE pr_author = ? AND status = 'completed'
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (author, limit))

                records = [dict(row) for row in cursor.fetchall()]

                # 計算統計
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_prs,
                        AVG(CASE WHEN score IS NOT NULL THEN score END) as avg_score,
                        MIN(CASE WHEN score IS NOT NULL THEN score END) as min_score,
                        MAX(CASE WHEN score IS NOT NULL THEN score END) as max_score,
                        COUNT(CASE WHEN score IS NOT NULL THEN 1 END) as scored_prs
                    FROM review_tasks
                    WHERE pr_author = ? AND status = 'completed'
                """, (author,))

                stats_row = cursor.fetchone()
                stats = {
                    'total_prs': stats_row['total_prs'] or 0,
                    'avg_score': round(stats_row['avg_score'], 1) if stats_row['avg_score'] else None,
                    'min_score': stats_row['min_score'],
                    'max_score': stats_row['max_score'],
                    'scored_prs': stats_row['scored_prs'] or 0
                }

                # 獲取最近5次的分數趨勢（用於判斷進步或退步）
                cursor.execute("""
                    SELECT score
                    FROM review_tasks
                    WHERE pr_author = ? AND status = 'completed' AND score IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (author,))

                recent_scores = [row['score'] for row in cursor.fetchall()]

                # 計算趨勢（如果有足夠的數據）
                trend = None
                if len(recent_scores) >= 3:
                    # 簡單的趨勢判斷：比較前半和後半的平均分
                    mid = len(recent_scores) // 2
                    recent_avg = sum(recent_scores[:mid]) / mid
                    older_avg = sum(recent_scores[mid:]) / (len(recent_scores) - mid)

                    if recent_avg > older_avg + 5:
                        trend = 'improving'  # 進步中
                    elif recent_avg < older_avg - 5:
                        trend = 'declining'  # 退步中
                    else:
                        trend = 'stable'  # 穩定

                stats['trend'] = trend
                stats['recent_scores'] = recent_scores

                return {
                    'records': records,
                    'stats': stats
                }

        except Exception as e:
            self.logger.error(f"獲取作者 PR 歷史失敗: {e}")
            return {
                'records': [],
                'stats': {
                    'total_prs': 0,
                    'avg_score': None,
                    'min_score': None,
                    'max_score': None,
                    'scored_prs': 0,
                    'trend': None,
                    'recent_scores': []
                }
            }

    def get_author_issue_history(self, author: str, limit: int = 20) -> Dict:
        """
        獲取作者的 Issue 評分歷史和統計

        Args:
            author: Issue 作者名稱
            limit: 返回的最大記錄數

        Returns:
            包含歷史記錄和統計的字典
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 獲取作者的 Issue 評分記錄（排除已忽略的）
                cursor.execute("""
                    SELECT score_id, repo_name, issue_number, content_type,
                           title, issue_url, overall_score, format_score,
                           content_score, clarity_score, actionability_score,
                           status, created_at, completed_at
                    FROM issue_scores
                    WHERE author = ? AND status = 'completed' AND (ignored IS NULL OR ignored = 0)
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (author, limit))

                records = [dict(row) for row in cursor.fetchall()]

                # 計算統計
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_issues,
                        AVG(overall_score) as avg_overall,
                        AVG(format_score) as avg_format,
                        AVG(content_score) as avg_content,
                        AVG(clarity_score) as avg_clarity,
                        AVG(actionability_score) as avg_actionability,
                        MIN(overall_score) as min_score,
                        MAX(overall_score) as max_score
                    FROM issue_scores
                    WHERE author = ? AND status = 'completed' AND (ignored IS NULL OR ignored = 0)
                """, (author,))

                stats_row = cursor.fetchone()
                stats = {
                    'total_issues': stats_row['total_issues'] or 0,
                    'avg_overall': round(stats_row['avg_overall'], 1) if stats_row['avg_overall'] else None,
                    'avg_format': round(stats_row['avg_format'], 1) if stats_row['avg_format'] else None,
                    'avg_content': round(stats_row['avg_content'], 1) if stats_row['avg_content'] else None,
                    'avg_clarity': round(stats_row['avg_clarity'], 1) if stats_row['avg_clarity'] else None,
                    'avg_actionability': round(stats_row['avg_actionability'], 1) if stats_row['avg_actionability'] else None,
                    'min_score': stats_row['min_score'],
                    'max_score': stats_row['max_score']
                }

                # 獲取最近5次的分數趨勢
                cursor.execute("""
                    SELECT overall_score
                    FROM issue_scores
                    WHERE author = ? AND status = 'completed' AND (ignored IS NULL OR ignored = 0)
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (author,))

                recent_scores = [row['overall_score'] for row in cursor.fetchall()]

                # 計算趨勢
                trend = None
                if len(recent_scores) >= 3:
                    mid = len(recent_scores) // 2
                    recent_avg = sum(recent_scores[:mid]) / mid
                    older_avg = sum(recent_scores[mid:]) / (len(recent_scores) - mid)

                    if recent_avg > older_avg + 5:
                        trend = 'improving'
                    elif recent_avg < older_avg - 5:
                        trend = 'declining'
                    else:
                        trend = 'stable'

                stats['trend'] = trend
                stats['recent_scores'] = recent_scores

                # 按內容類型統計
                cursor.execute("""
                    SELECT content_type, COUNT(*) as count, AVG(overall_score) as avg_score
                    FROM issue_scores
                    WHERE author = ? AND status = 'completed' AND (ignored IS NULL OR ignored = 0)
                    GROUP BY content_type
                """, (author,))

                by_type = {}
                for row in cursor.fetchall():
                    by_type[row['content_type']] = {
                        'count': row['count'],
                        'avg_score': round(row['avg_score'], 1) if row['avg_score'] else None
                    }

                stats['by_content_type'] = by_type

                return {
                    'records': records,
                    'stats': stats
                }

        except Exception as e:
            self.logger.error(f"獲取作者 Issue 歷史失敗: {e}")
            return {
                'records': [],
                'stats': {
                    'total_issues': 0,
                    'avg_overall': None,
                    'avg_format': None,
                    'avg_content': None,
                    'avg_clarity': None,
                    'avg_actionability': None,
                    'min_score': None,
                    'max_score': None,
                    'trend': None,
                    'recent_scores': [],
                    'by_content_type': {}
                }
            }

    def get_author_combined_stats(self, author: str) -> Dict:
        """
        獲取作者的綜合統計（PR + Issue）

        Args:
            author: 作者名稱

        Returns:
            綜合統計字典
        """
        try:
            pr_history = self.get_author_pr_history(author, limit=10)
            issue_history = self.get_author_issue_history(author, limit=10)

            return {
                'author': author,
                'pr_stats': pr_history['stats'],
                'issue_stats': issue_history['stats'],
                'pr_recent_records': pr_history['records'][:5],  # 最近5個 PR
                'issue_recent_records': issue_history['records'][:5]  # 最近5個 Issue
            }

        except Exception as e:
            self.logger.error(f"獲取作者綜合統計失敗: {e}")
            return {
                'author': author,
                'pr_stats': {},
                'issue_stats': {},
                'pr_recent_records': [],
                'issue_recent_records': []
            }

    def get_common_issues_by_author(self, author: str, repo: str = None) -> List[Dict]:
        """
        分析作者常見的問題模式（從審查內容中提取）

        Args:
            author: 作者名稱
            repo: 可選的倉庫過濾

        Returns:
            常見問題列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 獲取作者的所有 PR 審查內容
                query = """
                    SELECT review_content, score, pr_title, repo, created_at
                    FROM review_tasks
                    WHERE pr_author = ? AND status = 'completed' AND review_content IS NOT NULL
                """
                params = [author]

                if repo:
                    query += " AND repo = ?"
                    params.append(repo)

                query += " ORDER BY created_at DESC LIMIT 10"

                cursor.execute(query, params)
                reviews = cursor.fetchall()

                # 從審查內容中提取常見問題關鍵詞
                issue_patterns = {
                    '程式碼品質': ['代碼質量', '代码质量', '程式碼品質', 'code quality'],
                    '命名規範': ['命名', 'naming', '變數名', '变量名'],
                    '錯誤處理': ['錯誤處理', '错误处理', 'error handling', '例外處理'],
                    '效能問題': ['效能', '性能', 'performance', '優化', '优化'],
                    '安全問題': ['安全', 'security', '漏洞', '风险'],
                    '測試覆蓋': ['測試', '测试', 'test', 'coverage'],
                    '註解不足': ['註解', '注释', 'comment', '文檔', '文档'],
                    '重複程式碼': ['重複', '重复', 'duplicate', 'DRY']
                }

                issue_counts = {pattern: 0 for pattern in issue_patterns}

                for review in reviews:
                    content = review['review_content'] or ''
                    for issue_type, keywords in issue_patterns.items():
                        if any(keyword.lower() in content.lower() for keyword in keywords):
                            issue_counts[issue_type] += 1

                # 排序並過濾（只返回至少出現2次的問題）
                common_issues = [
                    {'issue_type': issue_type, 'occurrence_count': count}
                    for issue_type, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
                    if count >= 2
                ]

                return common_issues

        except Exception as e:
            self.logger.error(f"分析作者常見問題失敗: {e}")
            return []

    def get_repository_best_practices(self, repo: str, limit: int = 10) -> List[str]:
        """
        從高分 PR 中提取專案的最佳實踐建議

        Args:
            repo: 倉庫名稱
            limit: 分析的高分 PR 數量

        Returns:
            最佳實踐建議列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 獲取該倉庫評分最高的 PR 審查內容
                cursor.execute("""
                    SELECT review_content, score, pr_title
                    FROM review_tasks
                    WHERE repo = ? AND status = 'completed' AND score >= 85
                    ORDER BY score DESC, created_at DESC
                    LIMIT ?
                """, (repo, limit))

                high_score_reviews = cursor.fetchall()

                if not high_score_reviews:
                    return []

                # 從高分審查中提取正面評價關鍵詞
                positive_patterns = [
                    '程式碼清晰', '代碼清晰', 'clean code', 'well structured',
                    '良好的', '優秀的', '完整的測試', 'comprehensive test',
                    '詳細的註解', 'well documented', '命名清晰', 'clear naming',
                    '錯誤處理完善', 'proper error handling'
                ]

                practices = []
                for review in high_score_reviews:
                    content = review['review_content'] or ''
                    for pattern in positive_patterns:
                        if pattern.lower() in content.lower():
                            practices.append(f"參考 PR '{review['pr_title'][:50]}' (評分: {review['score']})")
                            break  # 每個 PR 只添加一次

                return practices[:5]  # 返回前5個

        except Exception as e:
            self.logger.error(f"獲取專案最佳實踐失敗: {e}")
            return []
