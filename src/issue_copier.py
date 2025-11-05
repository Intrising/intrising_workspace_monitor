#!/usr/bin/env python3
"""
GitHub Issue Auto-Copier - Webhook 驅動的 Issue 複製系統
監聽特定 repository 的 issues，根據 label 自動複製到目標 repositories
"""

import os
import re
import logging
import requests
import tempfile
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from github import Github, GithubException
from dotenv import load_dotenv


class IssueCopier:
    """Issue 自動複製器"""

    def __init__(self, config: dict, github_client: Github, logger: logging.Logger, database=None):
        """初始化複製器

        Args:
            config: issue_copy 配置字典
            github_client: GitHub API 客戶端
            logger: 日誌記錄器
            database: 資料庫實例（可選）
        """
        self.config = config
        self.github = github_client
        self.logger = logger
        self.db = database

        # 來源 repository
        self.source_repo = config.get("source_repo", "")

        # Label 映射規則
        self.label_to_repo = config.get("label_to_repo", {})

        # 默認目標 repository（當沒有匹配的 label 時使用）
        self.default_target_repo = config.get("default_target_repo")

        # 其他配置
        self.add_source_reference = config.get("add_source_reference", True)
        self.copy_labels = config.get("copy_labels", True)
        self.reupload_images = config.get("reupload_images", True)
        self.add_copy_comment = config.get("add_copy_comment", True)

        self.logger.info("Issue Copier 初始化完成")
        self.logger.info(f"來源 repository: {self.source_repo}")
        self.logger.info(f"Label 映射規則: {self.label_to_repo}")

    def download_image(self, url: str) -> Optional[Tuple[bytes, str]]:
        """下載圖片

        Args:
            url: 圖片 URL

        Returns:
            (圖片內容, 文件名) 或 None（如果下載失敗）
        """
        try:
            self.logger.info(f"下載圖片: {url}")

            # 發送 GET 請求下載圖片
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # 從 URL 中提取文件名
            filename = url.split("/")[-1].split("?")[0]  # 移除查詢參數
            if not filename:
                filename = "image.png"

            self.logger.info(f"成功下載圖片: {filename} ({len(response.content)} bytes)")
            return response.content, filename

        except Exception as e:
            self.logger.error(f"下載圖片失敗 ({url}): {e}")
            return None

    def upload_image_to_repo(self, repo_full_name: str, image_data: bytes, filename: str) -> Optional[str]:
        """上傳圖片到指定 repository（透過 GitHub Issue 附件 API）

        Args:
            repo_full_name: 目標 repository 全名（例如 "owner/repo"）
            image_data: 圖片二進制數據
            filename: 文件名

        Returns:
            上傳後的圖片 URL，失敗返回 None
        """
        try:
            repo = self.github.get_repo(repo_full_name)

            # GitHub 不直接提供圖片上傳 API
            # 我們需要透過創建一個臨時 issue comment 來上傳圖片
            # 但這需要先有一個 issue，所以我們改用另一種方法

            # 方法：使用 GitHub Asset Upload API（透過 PyGithub 的內部方法）
            # 注意：這是一個 workaround，因為 PyGithub 沒有直接的圖片上傳 API

            # 更好的方法：使用 GitHub's Asset Uploads for Releases
            # 但對於 issue 圖片，最簡單的方法是使用 git repo 存儲

            # 先嘗試使用 repo 的 create_file 上傳到 assets 目錄
            asset_path = f"assets/issue_images/{filename}"

            try:
                # 檢查文件是否已存在
                contents = repo.get_contents(asset_path)
                # 如果存在，更新文件
                result = repo.update_file(
                    path=asset_path,
                    message=f"Upload issue image: {filename}",
                    content=image_data,
                    sha=contents.sha,
                    branch="main"
                )
            except GithubException as e:
                if e.status == 404:
                    # 文件不存在，創建新文件
                    result = repo.create_file(
                        path=asset_path,
                        message=f"Upload issue image: {filename}",
                        content=image_data,
                        branch="main"
                    )
                else:
                    raise

            # 獲取文件的 raw URL
            raw_url = result['content'].download_url
            self.logger.info(f"成功上傳圖片到 {repo_full_name}: {raw_url}")
            return raw_url

        except Exception as e:
            self.logger.error(f"上傳圖片到 {repo_full_name} 失敗: {e}")
            return None

    def process_images_in_body(self, body: str, source_repo: str, target_repo: str) -> str:
        """處理 issue body 中的圖片（保留原始 URL）

        Args:
            body: 原始 issue body 文本
            source_repo: 來源 repository
            target_repo: 目標 repository

        Returns:
            處理後的 body 文本（保留原始圖片 URL）
        """
        if not body:
            return body

        # 保留原始圖片 URL，不做任何處理
        return body

    def get_target_repos_by_labels(self, labels: List[str]) -> List[str]:
        """根據 labels 獲取目標 repositories

        Args:
            labels: Issue 的 label 列表

        Returns:
            目標 repository 列表（去重後）
        """
        # 優先權處理：如果有 viewer-box，只複製到 QA-Viewer
        if "project: viewer-box" in labels:
            if "project: viewer-box" in self.label_to_repo:
                target_repo = self.label_to_repo["project: viewer-box"]
                self.logger.info(f"檢測到 'project: viewer-box' label，只複製到 '{target_repo}'（忽略其他 project labels）")
                return [target_repo]

        # 一般處理：根據所有 labels 映射
        target_repos = []

        for label in labels:
            if label in self.label_to_repo:
                target_repo = self.label_to_repo[label]
                if target_repo not in target_repos:
                    target_repos.append(target_repo)
                    self.logger.info(f"Label '{label}' -> Repository '{target_repo}'")

        # 如果沒有匹配的 target repos，且設定了默認目標，使用默認目標
        if not target_repos and self.default_target_repo:
            self.logger.info(f"沒有匹配的 project label，使用默認目標 repository: '{self.default_target_repo}'")
            target_repos.append(self.default_target_repo)

        return target_repos

    def copy_issue(self, source_issue_data: Dict, target_repo_name: str) -> Optional[Dict]:
        """複製 issue 到目標 repository

        Args:
            source_issue_data: 來源 issue 的數據字典
            target_repo_name: 目標 repository 名稱

        Returns:
            包含新建 issue 資訊的字典，失敗返回 None
            {
                'url': str,
                'number': int,
                'images_count': int
            }
        """
        record_id = None
        images_count = 0

        try:
            source_repo = source_issue_data['repository']
            source_number = source_issue_data['number']
            source_title = source_issue_data['title']
            source_body = source_issue_data['body'] or ""
            source_labels = source_issue_data['labels']
            source_url = source_issue_data['html_url']

            self.logger.info(f"開始複製 issue #{source_number} 從 {source_repo} 到 {target_repo_name}")

            # 檢查是否已經複製過（避免重複複製）
            if self.db:
                existing_records = self.db.search_copy_records(
                    source_repo=source_repo,
                    target_repo=target_repo_name,
                    source_issue_number=source_number
                )
                # 檢查是否有成功或進行中的複製記錄（避免並發重複）
                for record in existing_records:
                    if record.get('status') == 'success':
                        self.logger.info(f"Issue #{source_number} 已經複製到 {target_repo_name}，跳過重複複製")
                        return {
                            'url': record.get('target_issue_url'),
                            'number': record.get('target_issue_number'),
                            'images_count': record.get('images_count', 0),
                            'skipped': True,
                            'reason': 'already copied'
                        }
                    elif record.get('status') == 'pending':
                        # 檢查 pending 記錄的創建時間，如果是最近 30 秒內創建的，視為正在處理中
                        from datetime import datetime, timedelta
                        try:
                            created_at_str = record.get('created_at', '')
                            if created_at_str:
                                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                time_diff = datetime.now().astimezone() - created_at.astimezone()
                                if time_diff < timedelta(seconds=30):
                                    self.logger.info(f"Issue #{source_number} 正在複製到 {target_repo_name}（pending狀態），跳過重複複製")
                                    return {
                                        'url': None,
                                        'number': None,
                                        'images_count': 0,
                                        'skipped': True,
                                        'reason': 'copy in progress'
                                    }
                        except Exception as e:
                            self.logger.warning(f"解析 pending 記錄時間失敗: {e}")

            # 獲取目標 repository
            target_repo = self.github.get_repo(target_repo_name)

            # 檢查目標 repo 是否已存在相同標題的 issue
            expected_title = f"[LT#{source_number}] {source_title}"
            try:
                # 搜尋目標 repo 中是否有相同標題的 issue
                search_query = f'repo:{target_repo_name} is:issue "{expected_title}"'
                search_results = self.github.search_issues(search_query)

                if search_results.totalCount > 0:
                    existing_issue = search_results[0]
                    self.logger.info(f"目標 repo 中已存在相同標題的 issue: {existing_issue.html_url}")
                    return {
                        'url': existing_issue.html_url,
                        'number': existing_issue.number,
                        'images_count': 0,
                        'skipped': True,
                        'reason': 'duplicate title exists in target repo'
                    }
            except Exception as e:
                self.logger.warning(f"搜尋現有 issue 時發生錯誤: {e}")

            # 創建資料庫記錄（使用唯一約束防止並發重複）
            from datetime import datetime
            record_id = f"{source_repo}#{source_number}->{target_repo_name}@{datetime.now().timestamp()}"

            if self.db:
                record_created = self.db.create_copy_record({
                    'record_id': record_id,
                    'source_repo': source_repo,
                    'source_issue_number': source_number,
                    'source_issue_title': source_title,
                    'source_issue_url': source_url,
                    'source_labels': source_labels,
                    'target_repo': target_repo_name,
                    'status': 'pending'
                })

                # 如果記錄創建失敗（因唯一約束），說明已經有另一個並發請求在處理
                if not record_created:
                    self.logger.info(f"Issue #{source_number} 正在被另一個請求複製到 {target_repo_name}，跳過")
                    # 查詢現有記錄
                    existing_records = self.db.search_copy_records(
                        source_repo=source_repo,
                        target_repo=target_repo_name,
                        source_issue_number=source_number
                    )
                    if existing_records and existing_records[0].get('status') == 'success':
                        return {
                            'url': existing_records[0].get('target_issue_url'),
                            'number': existing_records[0].get('target_issue_number'),
                            'images_count': existing_records[0].get('images_count', 0),
                            'skipped': True,
                            'reason': 'duplicate prevented by unique constraint'
                        }
                    else:
                        return {
                            'url': None,
                            'number': None,
                            'images_count': 0,
                            'skipped': True,
                            'reason': 'duplicate copy in progress'
                        }

            # 處理圖片（下載並重新上傳）
            processed_body, images_count = self._process_images_in_body_with_count(
                source_body, source_repo, target_repo_name
            )

            # 添加來源引用
            if self.add_source_reference:
                source_reference = f"""---
**來源**: [{source_repo} #{source_number}]({source_url})

---

"""
                new_body = source_reference + processed_body
            else:
                new_body = processed_body

            # 修改標題，加上 [LT#原issue編號] 前綴
            new_title = f"[LT#{source_number}] {source_title}"

            # 創建新 issue
            new_issue = target_repo.create_issue(
                title=new_title,
                body=new_body
            )

            self.logger.info(f"已創建 issue: {new_issue.html_url}")

            # Assign 給 IS-LilithChang
            try:
                new_issue.add_to_assignees("IS-LilithChang")
                self.logger.info("已 assign 給 IS-LilithChang")
            except Exception as e:
                self.logger.error(f"Assign 給 IS-LilithChang 失敗: {e}")

            # 新增評論請更新圖片/附件
            try:
                new_issue.create_comment("@IS-LilithChang 更新一下圖片/附件")
                self.logger.info("已新增圖片/附件更新提醒評論")
            except Exception as e:
                self.logger.error(f"新增評論失敗: {e}")

            # 複製 labels（如果啟用）
            if self.copy_labels and source_labels:
                try:
                    # 只添加目標 repo 中存在的 labels
                    target_repo_labels = {label.name for label in target_repo.get_labels()}
                    labels_to_add = [label for label in source_labels if label in target_repo_labels]

                    if labels_to_add:
                        new_issue.set_labels(*labels_to_add)
                        self.logger.info(f"已添加 labels: {', '.join(labels_to_add)}")

                    # 對於不存在的 labels，記錄警告
                    missing_labels = [label for label in source_labels if label not in target_repo_labels]
                    if missing_labels:
                        self.logger.warning(f"以下 labels 在目標 repo 中不存在，已跳過: {', '.join(missing_labels)}")

                except Exception as e:
                    self.logger.error(f"添加 labels 失敗: {e}")

            # 更新資料庫記錄為成功
            if self.db and record_id:
                self.db.update_copy_record(record_id, {
                    'status': 'success',
                    'target_issue_number': new_issue.number,
                    'target_issue_url': new_issue.html_url,
                    'images_count': images_count
                })

            return {
                'url': new_issue.html_url,
                'number': new_issue.number,
                'images_count': images_count
            }

        except Exception as e:
            self.logger.error(f"複製 issue 失敗: {e}")

            # 更新資料庫記錄為失敗
            if self.db and record_id:
                self.db.update_copy_record(record_id, {
                    'status': 'failed',
                    'error_message': str(e)
                })

            return None

    def _process_images_in_body_with_count(self, body: str, source_repo: str, target_repo: str) -> tuple:
        """處理 issue body 中的圖片並返回圖片數量

        Returns:
            (處理後的 body, 圖片數量)
        """
        processed_body = self.process_images_in_body(body, source_repo, target_repo)

        # 計算原始 body 中的圖片數量
        if not body:
            return processed_body, 0

        # 簡單計算：原始 body 中的圖片數量
        import re
        patterns = [
            r'!\[([^\]]*)\]\(([^\)]+)\)',
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
        ]

        image_count = 0
        for pattern in patterns:
            matches = re.finditer(pattern, body)
            image_count += len(list(matches))

        return processed_body, image_count

    def add_copy_comment_to_source(self, source_repo_name: str, issue_number: int, target_urls: List[str]):
        """在原 issue 添加評論，說明已複製到哪些 repositories

        Args:
            source_repo_name: 來源 repository 名稱
            issue_number: 來源 issue 編號
            target_urls: 新建 issue 的 URL 列表
        """
        try:
            repo = self.github.get_repo(source_repo_name)
            issue = repo.get_issue(issue_number)

            # 構建評論內容
            comment_lines = ["## 🤖 Issue 已自動複製", ""]
            comment_lines.append("此 issue 已自動複製到以下 repositories：")
            comment_lines.append("")

            for url in target_urls:
                # 從 URL 中提取 repo 和 issue 號碼
                # URL 格式: https://github.com/owner/repo/issues/123
                parts = url.split("/")
                if len(parts) >= 7:
                    owner_repo = f"{parts[3]}/{parts[4]}"
                    issue_num = parts[6]
                    comment_lines.append(f"- [{owner_repo} #{issue_num}]({url})")
                else:
                    comment_lines.append(f"- {url}")

            comment_lines.append("")
            comment_lines.append("---")
            comment_lines.append("*由 Issue Auto-Copier 自動產生*")

            comment_body = "\n".join(comment_lines)

            # 發布評論
            issue.create_comment(comment_body)
            self.logger.info(f"已在原 issue 添加複製通知評論")

        except Exception as e:
            self.logger.error(f"添加評論失敗: {e}")

    def process_issue_event(self, event_type: str, payload: Dict) -> Dict:
        """處理 issue webhook 事件

        Args:
            event_type: 事件類型（應為 "issues"）
            payload: Webhook payload

        Returns:
            處理結果字典
        """
        try:
            action = payload.get("action", "")
            issue = payload.get("issue", {})
            repository = payload.get("repository", {})
            repo_full_name = repository.get("full_name", "")

            self.logger.info(f"收到 issue 事件: {event_type} - {action} - {repo_full_name}#{issue.get('number')}")

            # 檢查是否是目標來源 repository
            if repo_full_name != self.source_repo:
                self.logger.info(f"非目標來源 repository，跳過處理（期望: {self.source_repo}，實際: {repo_full_name}）")
                return {"status": "skipped", "reason": "not source repository"}

            # 檢查是否是觸發動作
            triggers = self.config.get("triggers", ["opened", "labeled"])
            if action not in triggers:
                self.logger.info(f"動作 '{action}' 不在觸發列表中，跳過處理")
                return {"status": "skipped", "reason": "action not in triggers"}

            # 注意：移除了 30 秒等待時間以避免 webhook 超時
            # 如果需要等待標籤自動添加，應該使用 labeled 觸發器而非 opened

            # 獲取 issue labels
            labels = [label['name'] for label in issue.get('labels', [])]

            # 根據 labels 獲取目標 repositories（沒有 labels 時會使用默認目標）
            target_repos = self.get_target_repos_by_labels(labels)

            if not target_repos:
                label_info = f"labels: {', '.join(labels)}" if labels else "沒有 labels"
                self.logger.info(f"沒有找到匹配的目標 repository（{label_info}），且未設定默認目標")
                return {"status": "skipped", "reason": "no matching target repositories"}

            # 準備 issue 數據
            issue_data = {
                'repository': repo_full_name,
                'number': issue.get('number'),
                'title': issue.get('title', ''),
                'body': issue.get('body'),
                'labels': labels,
                'html_url': issue.get('html_url', '')
            }

            # 複製到所有目標 repositories
            copied_urls = []
            total_images = 0
            for target_repo in target_repos:
                result = self.copy_issue(issue_data, target_repo)
                if result:
                    copied_urls.append(result['url'])
                    total_images += result.get('images_count', 0)

            # 在原 issue 添加評論
            if copied_urls and self.add_copy_comment:
                self.add_copy_comment_to_source(repo_full_name, issue.get('number'), copied_urls)

            return {
                "status": "success",
                "source_issue": f"{repo_full_name}#{issue.get('number')}",
                "target_repos": target_repos,
                "copied_urls": copied_urls,
                "copied_count": len(copied_urls),
                "total_images": total_images
            }

        except Exception as e:
            self.logger.error(f"處理 issue 事件失敗: {e}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e)
            }

    def process_comment_event(self, event_type: str, payload: Dict) -> Dict:
        """處理 issue comment webhook 事件

        Args:
            event_type: 事件類型（應為 "issue_comment"）
            payload: Webhook payload

        Returns:
            處理結果字典
        """
        try:
            action = payload.get("action", "")
            comment = payload.get("comment", {})
            issue = payload.get("issue", {})
            repository = payload.get("repository", {})
            repo_full_name = repository.get("full_name", "")
            issue_number = issue.get("number")

            self.logger.info(f"收到評論事件: {event_type} - {action} - {repo_full_name}#{issue_number}")

            # 只處理新建評論
            if action != "created":
                self.logger.info(f"動作 '{action}' 不是 created，跳過處理")
                return {"status": "skipped", "reason": "not created action"}

            # 檢查是否是目標來源 repository
            if repo_full_name != self.source_repo:
                self.logger.info(f"非目標來源 repository，跳過處理")
                return {"status": "skipped", "reason": "not source repository"}

            # 從資料庫查詢此 issue 複製出去的目標 issues
            target_issues = []

            try:
                if self.db:
                    # 從資料庫查詢複製記錄
                    copy_records = self.db.search_copy_records(
                        source_repo=repo_full_name,
                        source_issue_number=issue_number
                    )

                    # 只選擇成功複製的記錄
                    for record in copy_records:
                        if record.get('status') == 'success':
                            target_issues.append({
                                'repo': record.get('target_repo'),
                                'number': record.get('target_issue_number'),
                                'url': record.get('target_issue_url')
                            })
                            self.logger.info(f"找到複製的 issue: {record.get('target_repo')}#{record.get('target_issue_number')}")
                else:
                    self.logger.warning("資料庫未初始化，無法查詢複製記錄")

            except Exception as e:
                self.logger.error(f"查詢複製記錄失敗: {e}")
                return {"status": "error", "reason": f"Failed to query copy records: {str(e)}"}

            if not target_issues:
                self.logger.info(f"找不到 {repo_full_name}#{issue_number} 的複製記錄，跳過評論同步")
                return {"status": "skipped", "reason": "no copied issues found"}

            # 獲取評論內容
            comment_body = comment.get("body", "")
            comment_author = comment.get("user", {}).get("login", "unknown")
            comment_url = comment.get("html_url", "")

            # 構建評論內容（包含原作者資訊和原始評論連結）
            synced_comment = f"**{comment_author}** 在原始 issue 留言：\n\n{comment_url}\n\n---\n\n{comment_body}"

            # 檢測評論內容是否包含圖片或附件
            import re
            # 檢測 Markdown 圖片語法、HTML img 標籤、或附件連結
            has_media = bool(
                re.search(r'!\[([^\]]*)\]\(([^\)]+)\)', comment_body) or  # Markdown 圖片
                re.search(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', comment_body) or  # HTML img
                re.search(r'https://github\.com/.*?/files/', comment_body)  # GitHub 附件
            )

            # 只在有圖片/附件時才加上更新提醒
            if has_media:
                synced_comment += f"\n\n---\n\n如果有圖片/附件的話，請 @IS-LilithChang 幫忙更新一下圖片/附件，謝謝！"

            # 同步評論到所有目標 issues
            synced_count = 0
            for target in target_issues:
                try:
                    target_repo = self.github.get_repo(target['repo'])
                    target_issue = target_repo.get_issue(target['number'])
                    target_issue.create_comment(synced_comment)

                    self.logger.info(f"已同步評論到 {target['repo']}#{target['number']}")
                    synced_count += 1

                except Exception as e:
                    self.logger.error(f"同步評論到 {target['repo']}#{target['number']} 失敗: {e}")

            # 記錄到資料庫
            if self.db:
                from datetime import datetime
                sync_id = f"{repo_full_name}#{issue_number}-comment@{datetime.now().timestamp()}"

                self.db.create_comment_sync_record({
                    'sync_id': sync_id,
                    'source_repo': repo_full_name,
                    'source_issue_number': issue_number,
                    'source_issue_url': issue.get('html_url', ''),
                    'comment_author': comment_author,
                    'comment_body': comment_body[:500],  # 限制長度
                    'synced_to_repos': [f"{t['repo']}#{t['number']}" for t in target_issues],
                    'synced_count': synced_count,
                    'total_targets': len(target_issues),
                    'status': 'success',
                    'created_at': datetime.now().isoformat()
                })

            return {
                "status": "success",
                "source_issue": f"{repo_full_name}#{issue_number}",
                "synced_to": [f"{t['repo']}#{t['number']}" for t in target_issues],
                "synced_count": synced_count,
                "total_targets": len(target_issues)
            }

        except Exception as e:
            self.logger.error(f"處理評論事件失敗: {e}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e)
            }
