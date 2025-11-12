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

    def extract_image_urls(self, text: str) -> List[str]:
        """
        從文本中提取圖片 URL

        Args:
            text: Markdown 或 HTML 文本

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

        # 過濾掉已經在 GitHub 的圖片
        filtered_urls = []
        for url in image_urls:
            parsed = urlparse(url)
            # 跳過已經在 github.com 或 githubusercontent.com 的圖片
            if 'github' not in parsed.netloc:
                filtered_urls.append(url)

        return filtered_urls

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
                   filename: str, commit_message: str = None) -> Optional[str]:
        """
        上傳檔案到 GitHub

        Args:
            repo_full_name: Repository 完整名稱 (owner/repo)
            file_content: 檔案內容 (bytes)
            filename: 檔案名稱
            commit_message: Commit 訊息

        Returns:
            GitHub URL 或 None
        """
        try:
            # 確保 assets 分支存在
            if not self.ensure_assets_branch(repo_full_name):
                return None

            repo = self.github.get_repo(repo_full_name)
            file_path = f"images/{filename}"

            # Base64 編碼檔案內容
            content_base64 = base64.b64encode(file_content).decode('utf-8')

            # 預設 commit 訊息
            if not commit_message:
                commit_message = f"Upload image: {filename}"

            # 檢查檔案是否已存在
            try:
                existing_file = repo.get_contents(file_path, ref=self.assets_branch)
                # 檔案存在，更新它
                repo.update_file(
                    path=file_path,
                    message=f"Update {commit_message}",
                    content=content_base64,
                    sha=existing_file.sha,
                    branch=self.assets_branch
                )
                self.logger.info(f"✅ 已更新檔案: {file_path}")
            except:
                # 檔案不存在，創建新檔案
                repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content_base64,
                    branch=self.assets_branch
                )
                self.logger.info(f"✅ 已上傳檔案: {file_path}")

            # 返回圖片的 raw URL
            url = f"https://github.com/{repo_full_name}/blob/{self.assets_branch}/{file_path}?raw=true"
            return url

        except Exception as e:
            self.logger.error(f"上傳檔案失敗: {e}", exc_info=True)
            return None

    def process_text_images(self, repo_full_name: str, text: str,
                           issue_number: int = None) -> str:
        """
        處理文本中的圖片：下載並重新上傳到 GitHub

        Args:
            repo_full_name: Repository 完整名稱
            text: 包含圖片的 Markdown/HTML 文本
            issue_number: Issue 編號（用於 commit 訊息）

        Returns:
            處理後的文本（圖片 URL 已替換為 GitHub URL）
        """
        if not text:
            return text

        # 提取圖片 URL
        image_urls = self.extract_image_urls(text)

        if not image_urls:
            self.logger.debug("未找到需要處理的圖片")
            return text

        self.logger.info(f"找到 {len(image_urls)} 個圖片需要處理")

        processed_text = text
        upload_count = 0

        for url in image_urls:
            # 下載圖片
            result = self.download_image(url)
            if not result:
                self.logger.warning(f"跳過無法下載的圖片: {url}")
                continue

            file_content, filename = result

            # 上傳到 GitHub
            commit_msg = f"Add image for issue #{issue_number}" if issue_number else f"Upload image"
            github_url = self.upload_file(repo_full_name, file_content, filename, commit_msg)

            if github_url:
                # 替換原始 URL 為 GitHub URL
                processed_text = processed_text.replace(url, github_url)
                upload_count += 1
                self.logger.info(f"✅ 圖片已處理: {url} -> {github_url}")
            else:
                self.logger.warning(f"圖片上傳失敗: {url}")

        self.logger.info(f"✅ 成功處理 {upload_count}/{len(image_urls)} 個圖片")
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
