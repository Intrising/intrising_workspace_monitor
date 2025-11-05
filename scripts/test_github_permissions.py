#!/usr/bin/env python3
"""
測試 GitHub Token 權限和郵箱獲取
"""

import os
import sys
from github import Github, GithubException
from dotenv import load_dotenv

# 顏色定義
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{BLUE}{'='*80}")
    print(f"{text}")
    print(f"{'='*80}{NC}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{NC}")

def print_error(text):
    print(f"{RED}❌ {text}{NC}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{NC}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{NC}")


def main():
    # 載入環境變數
    load_dotenv()

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token or github_token == "ghp_your_github_personal_access_token_here":
        print_error("GITHUB_TOKEN 未設置或使用默認值")
        print_info("請編輯 .env 文件並設置有效的 GitHub Token")
        sys.exit(1)

    print_header("🔍 GitHub Token 權限測試")

    try:
        g = Github(github_token)

        # 測試 1: 基本認證
        print_info("測試 1: 基本認證...")
        try:
            user = g.get_user()
            print_success(f"認證成功: {user.login}")
            print(f"   用戶名: {user.name or 'N/A'}")
            print(f"   郵箱: {user.email or '未公開'}")
            print(f"   類型: {user.type}")
        except GithubException as e:
            print_error(f"認證失敗: {e.status} - {e.data.get('message', '')}")
            sys.exit(1)

        # 測試 2: 倉庫訪問權限
        print_info("\n測試 2: 倉庫訪問權限...")
        test_repo = input(f"請輸入要測試的倉庫 (格式: owner/repo，預設: Intrising/kh_utils): ").strip()
        if not test_repo:
            test_repo = "Intrising/kh_utils"

        try:
            repo = g.get_repo(test_repo)
            print_success(f"可以訪問倉庫: {repo.full_name}")
            print(f"   描述: {repo.description or 'N/A'}")
            print(f"   私有: {'是' if repo.private else '否'}")
            print(f"   默認分支: {repo.default_branch}")
        except GithubException as e:
            print_error(f"無法訪問倉庫: {e.status} - {e.data.get('message', '')}")
            print_warning("檢查 Token 是否有 'repo' 權限")
            sys.exit(1)

        # 測試 3: PR 訪問權限
        print_info("\n測試 3: Pull Request 訪問權限...")
        try:
            pulls = repo.get_pulls(state='all', sort='created', direction='desc')
            pr_count = pulls.totalCount
            print_success(f"可以訪問 PR，共 {pr_count} 個")

            if pr_count > 0:
                pr = pulls[0]
                print(f"   最新 PR: #{pr.number} - {pr.title}")
                print(f"   狀態: {pr.state}")
                print(f"   作者: {pr.user.login}")
        except GithubException as e:
            print_error(f"無法訪問 PR: {e.status} - {e.data.get('message', '')}")
            print_warning("檢查 Token 是否有 'repo' 權限")

        # 測試 4: 評論發布權限（讀取現有評論）
        print_info("\n測試 4: 評論訪問權限...")
        try:
            if pr_count > 0:
                comments = pr.get_issue_comments()
                comment_count = comments.totalCount
                print_success(f"可以訪問評論，共 {comment_count} 條")

                # 注意：我們不實際發布評論，只測試讀取權限
                print_info("   (未測試寫入權限，避免產生垃圾評論)")
        except GithubException as e:
            print_error(f"無法訪問評論: {e.status}")

        # 測試 5: 用戶郵箱獲取
        print_info("\n測試 5: 用戶郵箱獲取能力...")

        test_users = []

        # 5.1: 當前用戶
        print(f"\n   當前用戶 ({user.login}):")
        if user.email:
            print_success(f"   可以獲取郵箱: {user.email}")
        else:
            print_warning(f"   郵箱未公開")

        # 5.2: PR 作者（如果有 PR）
        if pr_count > 0:
            pr_author = pr.user
            print(f"\n   PR 作者 ({pr_author.login}):")
            if pr_author.email:
                print_success(f"   可以獲取郵箱: {pr_author.email}")
            else:
                print_warning(f"   郵箱未公開")
                print_info(f"   建議: 在 config.yaml 中配置 user_email_mapping")

            # 5.3: PR 審查者
            reviewers = pr.requested_reviewers
            if reviewers:
                print(f"\n   PR 審查者:")
                for reviewer in reviewers:
                    if reviewer.email:
                        print_success(f"   {reviewer.login}: {reviewer.email}")
                    else:
                        print_warning(f"   {reviewer.login}: 郵箱未公開")

            # 5.4: Commits 作者郵箱
            print(f"\n   從 Commits 獲取郵箱:")
            try:
                commits = pr.get_commits()
                emails = set()
                for commit in list(commits)[:5]:  # 只檢查前 5 個 commit
                    if commit.commit.author.email:
                        emails.add(commit.commit.author.email)
                    if commit.commit.committer.email:
                        emails.add(commit.commit.committer.email)

                if emails:
                    print_success(f"   從 commits 找到 {len(emails)} 個郵箱:")
                    for email in emails:
                        print(f"      - {email}")
                else:
                    print_warning(f"   未找到郵箱")
            except Exception as e:
                print_warning(f"   獲取 commits 失敗: {e}")

        # 測試 6: 組織權限（如果是組織倉庫）
        if '/' in test_repo and not test_repo.startswith(user.login + '/'):
            print_info("\n測試 6: 組織訪問權限...")
            org_name = test_repo.split('/')[0]
            try:
                org = g.get_organization(org_name)
                print_success(f"可以訪問組織: {org.login}")
                print(f"   組織名稱: {org.name or 'N/A'}")
                print(f"   成員數: {org.get_members().totalCount}")
            except GithubException as e:
                print_warning(f"無法訪問組織信息: {e.status}")
                print_info("   組織信息不是必需的，PR 審查仍可正常工作")

        # 總結
        print_header("📋 測試總結")

        print_success("✅ 必需權限:")
        print("   - repo (訪問倉庫)")
        print("   - Pull requests 讀寫")

        print(f"\n{YELLOW}⚠️  可選權限:{NC}")
        print("   - read:user (獲取用戶郵箱)")
        print("   - read:org (獲取組織信息)")

        print(f"\n{BLUE}💡 郵箱獲取建議:{NC}")
        print("   1. 如果無法從 GitHub API 獲取郵箱")
        print("   2. 在 config.yaml 中配置 user_email_mapping")
        print("   3. 或使用 default_recipients 作為備用")

        print(f"\n{GREEN}✅ Token 測試完成！{NC}")

    except Exception as e:
        print_error(f"測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
