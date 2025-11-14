#!/usr/bin/env python3
"""
GitHub Asset Uploader
自動上傳圖片和附件到 GitHub Repository 的 assets 分支
"""

import os
import base64
import logging
import re
import requests
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse
from github import Github


class GitHubAssetUploader:
    """GitHub 資產上傳器"""

    def __init__(self, github_token: str, logger: logging.Logger = None):
        """
        初始化上傳器

        Args:
            github_token: GitHub Personal Access Token
            logger: Logger 實例
        """
        self.github = Github(github_token)
        self.github_token = github_token
        self.logger = logger or logging.getLogger(__name__)
        self.assets_branch = "assets"

    def extract_image_urls(self, text: str, target_repo: str = None) -> List[str]:
        """
        從文本中提取圖片 URL

        Args:
            text: Markdown 或 HTML 文本
            target_repo: 目標 repository 名稱 (owner/repo)，用於判斷是否跳過已在目標 repo 的圖片

        Returns:
            圖片 URL 列表
        """
        image_urls = []

        # Markdown 圖片: ![alt](url)
        markdown_pattern = r'!\[.*?\]\((https?://[^\)]+)\)'
        image_urls.extend(re.findall(markdown_pattern, text))

        # HTML img 標籤: <img src="url">
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        image_urls.extend(re.findall(html_pattern, text))

        # 過濾圖片 URL
        filtered_urls = []
        for url in image_urls:
            parsed = urlparse(url)

            # 跳過已經在目標 repo assets 分支的圖片
            if target_repo and f"github.com/{target_repo}/blob/{self.assets_branch}" in url:
                self.logger.debug(f"跳過已在目標 repo assets 分支的圖片: {url}")
                continue

            # user-attachments 的圖片需要重新上傳（沒有權限的人看不到）
            if 'user-attachments' in parsed.netloc or 'github.com/user-attachments' in url:
                filtered_urls.append(url)
                continue

            # 其他 GitHub 圖片（非 user-attachments）也需要處理，因為可能來自其他 repo
            if 'github' in parsed.netloc:
                # 只跳過已經在目標 repo 的圖片
                if target_repo and target_repo in url:
                    self.logger.debug(f"跳過已在目標 repo 的圖片: {url}")
                    continue
                else:
                    # 來自其他 repo 的圖片需要重新上傳
                    filtered_urls.append(url)
                    continue

            # 非 GitHub 的外部圖片也需要上傳
            filtered_urls.append(url)

        return filtered_urls

    def extract_attachment_urls(self, text: str, target_repo: str = None) -> List[Tuple[str, str]]:
        """
        從文本中提取附件 URL（如 .zip, .pdf 等）

        Args:
            text: Markdown 文本
            target_repo: 目標 repository 名稱 (owner/repo)

        Returns:
            [(url, filename), ...] 列表
        """
        attachments = []

        # Markdown 連結: [filename](url)
        # 匹配常見的附件格式
        attachment_pattern = r'\[([^\]]*\.(?:zip|pdf|doc|docx|xls|xlsx|ppt|pptx|txt|log|tar|gz|7z|rar))\]\((https?://[^\)]+)\)'
        matches = re.findall(attachment_pattern, text, re.IGNORECASE)

        for filename, url in matches:
            # 跳過已經在目標 repo assets 分支的附件
            if target_repo and f"github.com/{target_repo}/blob/{self.assets_branch}" in url:
                self.logger.debug(f"跳過已在目標 repo assets 分支的附件: {url}")
                continue

            # user-attachments 的附件需要重新上傳（沒有權限的人看不到）
            if 'user-attachments' in url or 'github.com/user-attachments' in url:
                attachments.append((url, filename))
                continue

            # 其他 GitHub 附件也需要處理
            if 'github.com' in url:
                if target_repo and target_repo in url:
                    self.logger.debug(f"跳過已在目標 repo 的附件: {url}")
                    continue
                else:
                    attachments.append((url, filename))
                    continue

            # 外部附件
            attachments.append((url, filename))

        return attachments

    def download_image(self, url: str) -> Optional[Tuple[bytes, str]]:
        """
        下載圖片

        Args:
            url: 圖片 URL

        Returns:
            (圖片內容, 檔案名稱) 或 None
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # 從 URL 獲取檔案名稱
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)

            # 如果沒有副檔名，根據 Content-Type 添加
            if '.' not in filename:
                content_type = response.headers.get('Content-Type', '')
                ext_map = {
                    'image/png': '.png',
                    'image/jpeg': '.jpg',
                    'image/gif': '.gif',
                    'image/webp': '.webp',
                    'image/svg+xml': '.svg'
                }
                ext = ext_map.get(content_type, '.png')
                filename = f'image_{hash(url) % 100000}{ext}'

            return (response.content, filename)

        except Exception as e:
            self.logger.error(f"下載圖片失敗: {url}, 錯誤: {e}")
            return None

    def ensure_assets_branch(self, repo_full_name: str) -> bool:
        """
        確保 assets 分支存在

        Args:
            repo_full_name: Repository 完整名稱 (owner/repo)

        Returns:
            成功返回 True
        """
        try:
            repo = self.github.get_repo(repo_full_name)

            # 檢查分支是否存在
            try:
                repo.get_branch(self.assets_branch)
                self.logger.info(f"Assets 分支已存在: {repo_full_name}/{self.assets_branch}")
                return True
            except:
                # 分支不存在，創建它
                self.logger.info(f"創建 assets 分支: {repo_full_name}/{self.assets_branch}")

                # 獲取預設分支的 SHA
                try:
                    default_branch = repo.default_branch
                    ref = repo.get_git_ref(f"heads/{default_branch}")
                except:
                    # 嘗試 main
                    try:
                        ref = repo.get_git_ref("heads/main")
                    except:
                        # 嘗試 master
                        ref = repo.get_git_ref("heads/master")

                sha = ref.object.sha

                # 創建新分支
                repo.create_git_ref(f"refs/heads/{self.assets_branch}", sha)
                self.logger.info(f"✅ Assets 分支已創建")
                return True

        except Exception as e:
            self.logger.error(f"確保 assets 分支失敗: {e}")
            return False

    def upload_file(self, repo_full_name: str, file_content: bytes,
                   filename: str, commit_message: str = None, is_attachment: bool = False) -> Optional[str]:
        """
        上傳檔案到 GitHub 主分支的 docs/ 目錄

        Args:
            repo_full_name: Repository 完整名稱 (owner/repo)
            file_content: 檔案內容 (bytes)
            filename: 檔案名稱
            commit_message: Commit 訊息
            is_attachment: 是否為附件（True: 存放在 attachments/，False: 存放在 images/）

        Returns:
            GitHub URL 或 None
        """
        try:
            repo = self.github.get_repo(repo_full_name)

            # 獲取主分支名稱
            default_branch = repo.default_branch

            # 根據檔案類型決定存放路徑（存放在主分支的 docs/ 目錄下）
            folder = "attachments" if is_attachment else "images"
            file_path = f"docs/{folder}/{filename}"

            # Base64 編碼檔案內容
            content_base64 = base64.b64encode(file_content).decode('utf-8')

            # 預設 commit 訊息
            if not commit_message:
                commit_message = f"Upload {'attachment' if is_attachment else 'image'}: {filename}"

            # 檢查檔案是否已存在
            try:
                existing_file = repo.get_contents(file_path, ref=default_branch)
                # 檔案存在，更新它
                repo.update_file(
                    path=file_path,
                    message=f"Update {commit_message}",
                    content=content_base64,
                    sha=existing_file.sha,
                    branch=default_branch
                )
                self.logger.info(f"✅ 已更新檔案: {file_path}")
            except:
                # 檔案不存在，創建新檔案
                repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content_base64,
                    branch=default_branch
                )
                self.logger.info(f"✅ 已上傳檔案: {file_path}")

            # 返回 /raw/ URL（GitHub 會在 issue 內自動處理私有 repo 的認證）
            url = f"https://github.com/{repo_full_name}/raw/{default_branch}/{file_path}"
            return url

        except Exception as e:
            self.logger.error(f"上傳檔案失敗: {e}", exc_info=True)
            return None

    def process_text_images(self, repo_full_name: str, text: str,
                           issue_number: int = None) -> str:
        """
        處理文本中的圖片和附件：下載並重新上傳到 GitHub

        Args:
            repo_full_name: Repository 完整名稱
            text: 包含圖片和附件的 Markdown/HTML 文本
            issue_number: Issue 編號（用於 commit 訊息）

        Returns:
            處理後的文本（圖片和附件 URL 已替換為 GitHub URL）
        """
        if not text:
            return text

        processed_text = text
        total_processed = 0

        # 1. 處理圖片
        image_urls = self.extract_image_urls(text, target_repo=repo_full_name)

        if image_urls:
            self.logger.info(f"找到 {len(image_urls)} 個圖片需要處理")
            image_count = 0

            for url in image_urls:
                # 下載圖片
                result = self.download_image(url)
                if not result:
                    self.logger.warning(f"跳過無法下載的圖片: {url}")
                    continue

                file_content, filename = result

                # 上傳到 GitHub（圖片放在 images/ 目錄）
                commit_msg = f"Add image for issue #{issue_number}" if issue_number else f"Upload image"
                github_url = self.upload_file(repo_full_name, file_content, filename, commit_msg, is_attachment=False)

                if github_url:
                    # 替換原始 URL 為 GitHub URL
                    processed_text = processed_text.replace(url, github_url)
                    image_count += 1
                    self.logger.info(f"✅ 圖片已處理: {url} -> {github_url}")
                else:
                    self.logger.warning(f"圖片上傳失敗: {url}")

            self.logger.info(f"✅ 成功處理 {image_count}/{len(image_urls)} 個圖片")
            total_processed += image_count

        # 2. 處理附件
        attachments = self.extract_attachment_urls(processed_text, target_repo=repo_full_name)

        if attachments:
            self.logger.info(f"找到 {len(attachments)} 個附件需要處理")
            attachment_count = 0

            for url, original_filename in attachments:
                # 下載附件
                result = self.download_image(url)  # 使用同樣的下載方法
                if not result:
                    self.logger.warning(f"跳過無法下載的附件: {url}")
                    continue

                file_content, _ = result
                # 使用原始檔名（從 Markdown 連結中提取的）
                filename = original_filename

                # 上傳到 GitHub（附件放在 attachments/ 目錄）
                commit_msg = f"Add attachment for issue #{issue_number}" if issue_number else f"Upload attachment"
                github_url = self.upload_file(repo_full_name, file_content, filename, commit_msg, is_attachment=True)

                if github_url:
                    # 替換原始 URL 為 GitHub URL
                    processed_text = processed_text.replace(url, github_url)
                    attachment_count += 1
                    self.logger.info(f"✅ 附件已處理: {url} -> {github_url}")
                else:
                    self.logger.warning(f"附件上傳失敗: {url}")

            self.logger.info(f"✅ 成功處理 {attachment_count}/{len(attachments)} 個附件")
            total_processed += attachment_count

        if total_processed == 0:
            self.logger.debug("未找到需要處理的圖片或附件")

        return processed_text

    def upload_local_file(self, repo_full_name: str, local_path: str,
                         issue_number: int = None) -> Optional[str]:
        """
        上傳本地檔案到 GitHub

        Args:
            repo_full_name: Repository 完整名稱
            local_path: 本地檔案路徑
            issue_number: Issue 編號

        Returns:
            GitHub URL 或 None
        """
        try:
            if not os.path.exists(local_path):
                self.logger.error(f"檔案不存在: {local_path}")
                return None

            with open(local_path, 'rb') as f:
                file_content = f.read()

            filename = os.path.basename(local_path)
            commit_msg = f"Add file for issue #{issue_number}" if issue_number else f"Upload {filename}"

            return self.upload_file(repo_full_name, file_content, filename, commit_msg)

        except Exception as e:
            self.logger.error(f"上傳本地檔案失敗: {e}")
            return None
