#!/usr/bin/env python3
"""
GitHub PR Auto-Reviewer - Webhook 驱动的 PR 审查系统
接收 GitHub webhook 並使用 Claude CLI 自動審查 Pull Requests
"""

import os
import sys
import hmac
import hashlib
import logging
import subprocess
import tempfile
import threading
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from github import Github, GithubException
from dotenv import load_dotenv
import yaml
from database import TaskDatabase
from issue_copier import IssueCopier


class PRReviewer:
    """PR 自动审查器"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化审查器"""
        load_dotenv()

        # 载入配置
        self.config = self._load_config(config_path)

        # 设置日志
        self._setup_logging()

        # 初始化 GitHub 客户端
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN 环境变量未设置")

        github_api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
        self.github = Github(github_token, base_url=github_api_url)

        # Claude CLI 路徑（用於 PR 審查）
        self.claude_cli_path = os.getenv("CLAUDE_CLI_PATH", "claude")

        # Webhook 密钥
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")

        # 初始化資料庫（持久化存儲）
        db_path = os.getenv("DATABASE_PATH", "/var/lib/github-monitor/tasks.db")
        self.db = TaskDatabase(db_path)
        self.task_lock = threading.Lock()

        # 初始化 Issue Copier（如果啟用）
        issue_copy_config = self.config.get("issue_copy", {})
        if issue_copy_config.get("enabled", False):
            self.issue_copier = IssueCopier(issue_copy_config, self.github, self.logger, self.db)
            self.logger.info("Issue Copier 已啟用")
        else:
            self.issue_copier = None
            self.logger.info("Issue Copier 未啟用")

        self.logger.info("PR Reviewer 初始化完成")

    def _load_config(self, config_path: str) -> dict:
        """载入 YAML 配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"无法载入配置文件: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """设置日志系统"""
        log_level = os.getenv("LOG_LEVEL", "INFO")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        self.logger = logging.getLogger("PRReviewer")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(handler)

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """验证 GitHub webhook 签名"""
        if not self.webhook_secret:
            self.logger.warning("WEBHOOK_SECRET 未设置，跳过签名验证")
            return True

        expected_signature = 'sha256=' + hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        """获取 PR 的 diff 内容"""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # 获取文件变更
            files = pr.get_files()
            diff_content = []

            for file in files:
                diff_content.append(f"\n{'='*80}")
                diff_content.append(f"文件: {file.filename}")
                diff_content.append(f"状态: {file.status}")
                diff_content.append(f"变更: +{file.additions} -{file.deletions}")
                diff_content.append(f"{'='*80}\n")

                if file.patch:
                    diff_content.append(file.patch)
                else:
                    diff_content.append("(无 diff 内容 - 可能是二进制文件)")

            return "\n".join(diff_content)

        except Exception as e:
            self.logger.error(f"获取 PR diff 失败: {e}")
            return ""

    def get_user_info(self, username: str, repo_full_name: str = None) -> Dict:
        """获取用户详细资讯（ID、email 等）

        参数:
            username: GitHub 用户名
            repo_full_name: 保留参数以保持兼容性（不再使用）

        注意：优先从用户公开设置获取 email，如未公开则从配置文件的映射中查找
        """
        try:
            user = self.github.get_user(username)
            email = user.email  # 可能为 None

            # 如果用户未公开 email，从配置文件的映射中查找
            if not email:
                email_mapping = self.config.get("notifications", {}).get("email", {}).get("user_email_mapping", {})
                email = email_mapping.get(username)

                if email:
                    self.logger.info(f"从配置映射中找到用户 {username} 的 email")
                else:
                    self.logger.debug(f"用户 {username} 未公开 email，且配置中无映射")

            return {
                "id": user.id,
                "login": user.login,
                "name": user.name or username,
                "email": email,
                "company": user.company,
                "location": user.location,
                "bio": user.bio,
                "public_repos": user.public_repos,
                "followers": user.followers,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        except Exception as e:
            self.logger.error(f"获取用户 {username} 资讯失败: {e}")
            return {
                "id": None,
                "login": username,
                "name": username,
                "email": None,
            }

    def _get_email_from_commits(self, username: str, repo_full_name: str) -> Optional[str]:
        """从仓库的 commits 中获取用户的 email

        参数:
            username: GitHub 用户名
            repo_full_name: 仓库全名（如 "owner/repo"）

        返回:
            用户的 email，如果找不到则返回 None
        """
        try:
            repo = self.github.get_repo(repo_full_name)

            # 获取该用户最近的 commits
            commits = repo.get_commits(author=username)

            # 使用迭代器逐个获取，避免 PaginatedList 切片问题
            count = 0
            for commit in commits:
                count += 1
                if count > 30:  # 最多查询 30 个
                    break

                if commit.commit.author and commit.commit.author.email:
                    email = commit.commit.author.email
                    # 过滤掉 GitHub 自动生成的 noreply email
                    if not email.endswith('@users.noreply.github.com'):
                        self.logger.info(f"从 commits 中找到用户 {username} 的 email: {email}")
                        return email

            if count == 0:
                self.logger.warning(f"用户 {username} 在仓库 {repo_full_name} 中没有 commits")
            else:
                self.logger.warning(f"无法从 commits 中找到用户 {username} 的真实 email（查询了 {count} 个 commits，仅找到 noreply email）")

            return None

        except Exception as e:
            self.logger.warning(f"从 commits 中获取 email 失败 ({username} @ {repo_full_name}): {e}")
            return None

    def get_pr_participants(self, repo_full_name: str, pr_number: int) -> Dict:
        """获取 PR 相关人员的详细资讯"""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            participants = {
                "author": self.get_user_info(pr.user.login, repo_full_name),
                "reviewers": [],
                "assignees": [],
                "commenters": []
            }

            # 获取 reviewers
            try:
                for reviewer in pr.get_review_requests()[0]:  # [0] 是 users, [1] 是 teams
                    participants["reviewers"].append(self.get_user_info(reviewer.login, repo_full_name))
            except:
                pass

            # 获取 assignees
            for assignee in pr.assignees:
                participants["assignees"].append(self.get_user_info(assignee.login, repo_full_name))

            # 获取评论者
            try:
                commenters_set = set()
                for comment in pr.get_issue_comments():
                    if comment.user.login not in commenters_set:
                        commenters_set.add(comment.user.login)
                        participants["commenters"].append(self.get_user_info(comment.user.login, repo_full_name))
            except:
                pass

            self.logger.info(f"PR #{pr_number} 参与者: 作者={participants['author']['login']}, "
                           f"审查者={len(participants['reviewers'])}, "
                           f"分配者={len(participants['assignees'])}, "
                           f"评论者={len(participants['commenters'])}")

            return participants

        except Exception as e:
            self.logger.error(f"获取 PR 参与者资讯失败: {e}")
            return {
                "author": {},
                "reviewers": [],
                "assignees": [],
                "commenters": []
            }

    def get_pr_context(self, repo_full_name: str, pr_number: int) -> Dict:
        """获取 PR 的上下文信息"""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # 获取作者详细资讯（包含从 commits 获取的 email）
            author_info = self.get_user_info(pr.user.login, repo_full_name)

            return {
                "title": pr.title,
                "description": pr.body or "(无描述)",
                "author": pr.user.login,
                "author_info": author_info,  # 新增：作者详细资讯
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "files_changed": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "commits": pr.commits,
            }

        except Exception as e:
            self.logger.error(f"获取 PR 上下文失败: {e}")
            return {}

    def review_pr_with_claude(self, repo_full_name: str, pr_number: int) -> Optional[str]:
        """使用 Claude CLI 審查 PR"""
        try:
            # 获取 PR 上下文和 diff
            context = self.get_pr_context(repo_full_name, pr_number)
            diff = self.get_pr_diff(repo_full_name, pr_number)

            if not diff:
                self.logger.warning(f"PR #{pr_number} 没有 diff 内容")
                return None

            # 构建审查提示词
            review_config = self.config.get("review", {})
            prompt = self._build_review_prompt(context, diff, review_config)

            # 調用 Claude CLI
            self.logger.info(f"正在使用 Claude CLI 審查 PR #{pr_number}...")

            # 調用 Claude CLI（使用 --print 進行非交互式輸出）
            cmd = [
                self.claude_cli_path,
                '--print',
                prompt
            ]

            self.logger.debug(f"執行 Claude CLI...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10分钟超时（首次可能较慢）
                encoding='utf-8'
            )

            if result.returncode != 0:
                self.logger.error(f"Claude CLI 執行失敗 (返回碼: {result.returncode})")
                self.logger.error(f"stderr: {result.stderr[:500]}")  # 只顯示前500字符
                return None

            review_content = result.stdout.strip()

            if not review_content:
                self.logger.warning("Claude CLI 返回空內容")
                return None

            self.logger.info(f"Claude 審查完成: {len(review_content)} 字符")
            return review_content

        except subprocess.TimeoutExpired:
            self.logger.error("Claude CLI 執行超時")
            return None
        except Exception as e:
            self.logger.error(f"Claude 審查失敗: {e}")
            return None

    def _extract_score_from_review(self, review_content: str) -> Optional[int]:
        """從審查內容中提取評分（0-100）

        優先提取 "總分：XX/100" 格式的評分
        """
        try:
            import re

            # 優先匹配「總分」格式
            patterns = [
                r'總分[：:]\s*\*?\*?(\d+)\s*/\s*100',           # 總分：85/100
                r'總分[：:]\s*\*?\*?(\d+)',                     # 總分：85
                r'評分[：:]\s*\*?\*?(\d+)\s*/\s*100',           # 評分：85/100
                r'Score[：:]\s*(\d+)\s*/\s*100',                # Score: 85/100
                r'評分[：:]\s*\*?\*?(\d+)\s*分',                # 評分：85分
            ]

            for pattern in patterns:
                match = re.search(pattern, review_content, re.IGNORECASE)
                if match:
                    score = int(match.group(1))

                    # 確保分數在 0-100 範圍內
                    if 0 <= score <= 100:
                        self.logger.info(f"從審查內容中提取到總分: {score}/100")
                        return score
                    else:
                        self.logger.warning(f"提取到的評分超出範圍: {score}")

            self.logger.warning("無法從審查內容中提取評分")
            return None

        except Exception as e:
            self.logger.error(f"解析評分失敗: {e}")
            return None

    def _get_score_description(self, score: int) -> str:
        """根據評分返回評分說明"""
        if score >= 90:
            return "⭐⭐⭐⭐⭐ 優秀 - 程式碼品質高，無重大問題"
        elif score >= 80:
            return "⭐⭐⭐⭐ 良好 - 有少量改進空間"
        elif score >= 70:
            return "⭐⭐⭐ 尚可 - 有一些問題需要修改"
        elif score >= 60:
            return "⭐⭐ 需要改進 - 存在較多問題"
        else:
            return "⭐ 不建議合併 - 需要重大修改"

    def _build_review_prompt(self, context: Dict, diff: str, config: Dict) -> str:
        """构建审查提示词（包含作者歷史）"""
        focus_areas = config.get("focus_areas", [
            "代码质量",
            "潜在 bug",
            "性能问题",
            "安全漏洞",
            "最佳实践"
        ])

        language = config.get("language", "zh-TW")

        # 獲取作者歷史統計
        author = context.get('author', '')
        author_history = self.db.get_author_pr_history(author, limit=10)
        author_stats = author_history['stats']
        common_issues = self.db.get_common_issues_by_author(author, repo=context.get('repo', ''))

        # 構建作者歷史資訊區塊
        author_history_text = ""
        if author_stats['total_prs'] > 0:
            trend_text = {
                'improving': '📈 進步中（最近表現優於過去）',
                'declining': '📉 需加強（最近表現不如過去）',
                'stable': '➡️ 穩定'
            }.get(author_stats['trend'], '')

            author_history_text = f"""

## 作者歷史表現

**作者**: {author}
- **過去 PR 總數**: {author_stats['total_prs']} 個（其中 {author_stats['scored_prs']} 個有評分）
- **平均評分**: {author_stats['avg_score']}/100 (最低: {author_stats['min_score']}, 最高: {author_stats['max_score']})
- **趨勢**: {trend_text}
- **最近5次評分**: {', '.join(map(str, author_stats['recent_scores']))}

"""
            # 加入常見問題分析
            if common_issues:
                author_history_text += "**該作者過去常見問題**：\n"
                for issue in common_issues:
                    author_history_text += f"  - {issue['issue_type']} (出現 {issue['occurrence_count']} 次)\n"
                author_history_text += "\n⚠️ **審查重點**：請特別注意上述該作者過去常犯的問題是否在此 PR 中再次出現。\n"

        # 檢查 PR 描述是否完整
        description = context.get('description', '').strip()
        has_description = description and description != "(无描述)" and len(description) > 10

        # 如果缺少描述，添加額外的指示
        description_guide = ""
        if not has_description:
            description_guide = """

## 特別注意：此 PR 缺少描述

由於此 PR 缺少或僅有極簡描述，請在審查報告中：
1. 根據程式碼變更，生成一份完整的建議 PR 描述
2. 建議描述應包含：
   - **變更摘要**：簡要說明做了什麼變更
   - **變更原因**：為什麼需要這些變更
   - **變更內容**：詳細列出主要變更項目
   - **測試說明**（如適用）：如何測試這些變更
   - **影響範圍**（如適用）：可能影響的功能或模組

請將建議的 PR 描述放在「改進建議」區塊的開頭。
"""

        # 構建關注方面列表
        focus_areas_text = '\n'.join(f"- {area}" for area in focus_areas)

        # 根據是否有描述，構建改進建議模板
        improvement_template = ""
        if not has_description:
            improvement_template = """[首先提供建議的 PR 描述，格式如下：]

**📝 建議補充 PR 描述**
請將以下內容加入 PR 描述中：

```
[根據程式碼變更生成的完整 PR 描述，包含：變更摘要、變更原因、變更內容、測試說明、影響範圍]
```

[然後列出其他改進建議]"""
        else:
            improvement_template = "[提供具體的改進建議]"

        prompt = f"""你是一位專業的程式碼審查專家。請仔細審查以下 Pull Request 的程式碼變更。

## PR 資訊
- **標題**: {context.get('title', 'N/A')}
- **作者**: {context.get('author', 'N/A')}
- **分支**: {context.get('head_branch', 'N/A')} → {context.get('base_branch', 'N/A')}
- **檔案變更**: {context.get('files_changed', 0)} 個檔案
- **程式碼變更**: +{context.get('additions', 0)} -{context.get('deletions', 0)} 行
{author_history_text}
## PR 描述
{context.get('description', '(無描述)')}
{description_guide}

## 程式碼變更
{diff}

## 審查要求
請重點關注以下方面：
{focus_areas_text}

## 輸出格式要求

請直接提供審查報告內容，使用以下格式（使用 {language}）：

### 總體評分

**⚠️ 重要：所有評分必須使用 0-100 分制，不要使用 X/10 或 X/5 格式！**

請提供以下評分項目（每項 0-100 分）：

| 評分項目 | 分數 (0-100) | 說明 |
|---------|-------------|------|
| 代碼質量 | XX/100 | [簡要說明] |
| 安全性 | XX/100 | [簡要說明] |
| 可維護性 | XX/100 | [簡要說明] |

**總分：XX/100** (上述三項的平均分，四捨五入取整數)

評分標準參考：
- 90-100：優秀，程式碼品質高，無重大問題
- 80-89：良好，有少量改進空間
- 70-79：尚可，有一些問題需要修改
- 60-69：需要改進，存在較多問題
- 0-59：不建議合併，需要重大修改

### 總體評價
[簡要總結這個 PR 的整體質量和主要變更]

### 發現的問題
[列出發現的問題，按嚴重程度排序]
- **嚴重**: [嚴重問題，如果有的話]
- **中等**: [中等問題，如果有的話]
- **輕微**: [輕微問題，如果有的話]

### 改進建議
{improvement_template}

### 優點
[指出程式碼的優點]

### 審查結論
[給出總體建議：建議批准 / 建議修改後批准 / 需要重大修改]

---

**重要指示**：
1. 請直接輸出審查報告內容，不要包含任何分析過程或思考步驟
2. 不要在回覆中再次包含程式碼變更的 diff 內容
3. 不要輸出任何命令執行過程或文件搜尋過程
4. 只輸出最終的審查報告
5. **所有評分（包含分項評分和總分）必須使用 0-100 分制，格式為 "XX/100"**
6. **總分必須是各分項評分的平均值（四捨五入取整數）**
"""
        return prompt

    def get_pr_recipients(self, repo_full_name: str, pr_number: int) -> list:
        """获取 PR 的邮件收件人列表"""
        recipients = []

        # 添加配置文件中的固定收件人
        config_recipients = self.config.get("notifications", {}).get("email", {}).get("recipients", [])
        recipients.extend(config_recipients)
        self.logger.info(f"配置文件中的固定收件人: {', '.join(config_recipients) if config_recipients else '(无)'}")

        # 根据配置决定是否添加 PR 参与者
        email_config = self.config.get("notifications", {}).get("email", {})
        include_author = email_config.get("include_pr_author", True)
        include_reviewers = email_config.get("include_reviewers", False)
        include_assignees = email_config.get("include_assignees", False)

        self.logger.info(f"Email 配置: include_author={include_author}, include_reviewers={include_reviewers}, include_assignees={include_assignees}")

        if include_author or include_reviewers or include_assignees:
            participants = self.get_pr_participants(repo_full_name, pr_number)

            # 添加 PR 作者的 email
            if include_author and participants.get("author"):
                author_login = participants["author"].get("login", "未知")
                author_email = participants["author"].get("email")

                if author_email:
                    if author_email not in recipients:
                        recipients.append(author_email)
                        self.logger.info(f"✓ 添加 PR 作者 email: {author_login} <{author_email}>")
                    else:
                        self.logger.info(f"⊙ PR 作者 email 已在列表中: {author_login} <{author_email}>")
                else:
                    self.logger.debug(f"PR 作者 {author_login} 未公开 email，跳过邮件通知")

            # 添加审查者的 email
            if include_reviewers:
                for reviewer in participants.get("reviewers", []):
                    reviewer_login = reviewer.get("login", "未知")
                    reviewer_email = reviewer.get("email")
                    if reviewer_email and reviewer_email not in recipients:
                        recipients.append(reviewer_email)
                        self.logger.info(f"✓ 添加审查者 email: {reviewer_login} <{reviewer_email}>")
                    elif not reviewer_email:
                        self.logger.debug(f"审查者 {reviewer_login} 未公开 email，跳过邮件通知")

            # 添加分配者的 email
            if include_assignees:
                for assignee in participants.get("assignees", []):
                    assignee_login = assignee.get("login", "未知")
                    assignee_email = assignee.get("email")
                    if assignee_email and assignee_email not in recipients:
                        recipients.append(assignee_email)
                        self.logger.info(f"✓ 添加分配者 email: {assignee_login} <{assignee_email}>")
                    elif not assignee_email:
                        self.logger.debug(f"分配者 {assignee_login} 未公开 email，跳过邮件通知")

        # 去除空值
        recipients = [r for r in recipients if r]

        self.logger.info(f"PR #{pr_number} 最终邮件收件人列表 ({len(recipients)} 人): {', '.join(recipients) if recipients else '(无)'}")
        return recipients

    def send_email_notification(self, repo_full_name: str, pr_number: int, review_content: str, recipients: list):
        """發送郵件通知 PR 審查結果"""
        try:
            email_from = os.getenv("EMAIL_FROM", "devops@intrising.com.tw")
            pr_url = f"https://github.com/{repo_full_name}/pull/{pr_number}"

            # 構建郵件內容
            subject = f"[PR 審查通知] {repo_full_name} #{pr_number}"

            email_body = f"""您好，

這是關於 Pull Request #{pr_number} 的自動程式碼審查通知。

儲存庫: {repo_full_name}
PR 連結: {pr_url}

審查內容:
{'-' * 60}
{review_content}
{'-' * 60}

此郵件由自動化系統產生，請勿直接回覆。
查看完整 PR: {pr_url}

---
PR Auto-Reviewer @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            # 使用 msmtp 发送邮件
            for recipient in recipients:
                try:
                    # 构建邮件头
                    email_message = f"""From: {email_from}
To: {recipient}
Subject: {subject}
Content-Type: text/plain; charset=utf-8

{email_body}
"""

                    # 调用 msmtp 发送
                    msmtp_cmd = ["msmtp", "-t"]

                    # 如果指定了 msmtp 配置文件路径
                    msmtp_config = os.getenv("MSMTP_CONFIG")
                    if msmtp_config and os.path.exists(msmtp_config):
                        msmtp_cmd.extend(["-C", msmtp_config])

                    result = subprocess.run(
                        msmtp_cmd,
                        input=email_message.encode('utf-8'),
                        capture_output=True,
                        timeout=30
                    )

                    if result.returncode == 0:
                        self.logger.info(f"成功发送邮件到: {recipient}")
                    else:
                        self.logger.error(f"发送邮件到 {recipient} 失败: {result.stderr.decode('utf-8', errors='ignore')}")

                except subprocess.TimeoutExpired:
                    self.logger.error(f"发送邮件到 {recipient} 超时")
                except Exception as e:
                    self.logger.error(f"发送邮件到 {recipient} 时出错: {e}")

        except Exception as e:
            self.logger.error(f"邮件通知失败: {e}")

    def send_slack_notification(self, repo_full_name: str, pr_number: int, review_content: str, pr_title: str, pr_author: str):
        """發送 Slack 通知 PR 審查結果"""
        try:
            import requests

            slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            if not slack_webhook_url:
                self.logger.debug("SLACK_WEBHOOK_URL 未設置，跳過 Slack 通知")
                return

            pr_url = f"https://github.com/{repo_full_name}/pull/{pr_number}"

            # 截斷審查內容以適應 Slack 的字數限制
            max_length = 2000
            summary = review_content[:max_length]
            if len(review_content) > max_length:
                summary += "\n...(內容過長，請查看 GitHub PR 評論獲取完整審查報告)"

            # 構建 Slack 訊息
            slack_message = {
                "text": f"🤖 PR 自動審查完成",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🤖 Pull Request 自動審查完成"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*儲存庫:*\n{repo_full_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*PR 編號:*\n#{pr_number}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*標題:*\n{pr_title}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*作者:*\n@{pr_author}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*審查摘要:*\n```{summary}```"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "查看完整 PR"
                                },
                                "url": pr_url,
                                "style": "primary"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"由 Claude AI 自動產生 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }

            # 發送到 Slack
            response = requests.post(
                slack_webhook_url,
                json=slack_message,
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info(f"成功發送 Slack 通知到頻道")
            else:
                self.logger.error(f"發送 Slack 通知失敗: HTTP {response.status_code}, {response.text}")

        except requests.exceptions.Timeout:
            self.logger.error("Slack 通知發送超時")
        except Exception as e:
            self.logger.error(f"Slack 通知失敗: {e}")

    def _clean_review_content(self, content: str) -> str:
        """清理審查內容，移除 Claude CLI 的調試信息和程式碼變更區塊"""
        import re

        # 第一步：移除「程式碼變更」區塊
        # 匹配從「程式碼變更」或「## 程式碼變更」開始，到下一個「##」標題之前的所有內容
        content = re.sub(
            r'(?:##\s*)?程式碼變更\s*\n={80,}\n.*?(?=\n##\s|\Z)',
            '',
            content,
            flags=re.DOTALL
        )

        # 第二步：過濾行級調試信息
        lines = content.split('\n')
        cleaned_lines = []

        skip_patterns = [
            r'^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]',  # 时间戳开头
            r'^(thinking|exec|bash|claude|tokens used:)',  # Claude 內部命令
            r'Analyzing code changes',
            r'Checking file location',
            r'Listing top-level directories',
            r'Highlighting potential improvements',
            r'Evaluating comment change risks',
            r'Searching for .* file',
            r'Considering fallback search methods',
            r'Checking access and repo location',
            r'Preparing PR review and suggestions',
            r'^find:.*Permission denied',
            r'^sed:.*No such file or directory',
            r'^config\.yaml$',
            r'^msmtprc\.example$',
            r'^pr_monitor\.py$',
            r'^pr_reviewer\.py$',
            r'^\s*={80,}\s*$',  # 80個等號的分隔線
            r'^文件:\s+[\w/.-]+$',  # 文件名行（例如：文件: cpss/port.pb.go）
            r'^状态:\s+\w+$',  # 狀態行（例如：状态: modified）
            r'^变更:\s+\+\d+\s+-\d+$',  # 變更統計行（例如：变更: +262 -88）
        ]

        in_diff_block = False
        for line in lines:
            line_stripped = line.strip()

            # 檢測 diff 區塊的開始（以 @@ 開頭的行）
            if line_stripped.startswith('@@'):
                in_diff_block = True
                continue

            # 如果在 diff 區塊中，跳過直到遇到非 diff 內容
            if in_diff_block:
                # diff 內容通常以 +、-、空格開頭，或是空行
                if line and not line[0] in ['+', '-', ' ', '\t']:
                    in_diff_block = False
                else:
                    continue

            # 检查是否匹配任何跳过模式
            should_skip = any(re.match(pattern, line_stripped) for pattern in skip_patterns)

            if not should_skip:
                cleaned_lines.append(line)

        # 移除開頭和結尾的空行，但保留內容中的空行
        result = '\n'.join(cleaned_lines).strip()

        # 移除多餘的連續空行（超過2個）
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result

    def post_review_comment(self, repo_full_name: str, pr_number: int, review_content: str):
        """发布审查评论到 PR"""
        try:
            repo = self.github.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # 清理审查内容，移除调试信息
            cleaned_content = self._clean_review_content(review_content)

            # 提取評分（0-100）
            score = self._extract_score_from_review(review_content)

            # 獲取 PR 作者和 URL
            pr_author = pr.user.login
            pr_url = pr.html_url

            # 構建評分表格（加上總分）
            score_section = ""
            if score is not None:
                score_section = f"""
## 📊 總體評分

| 總分 | 評分說明 |
|------|----------|
| **{score}/100** | {self._get_score_description(score)} |

"""

            # 构建评论(不包含 diff 详情)
            # 注意：此時 comment 尚未創建，所以無法在此處獲取 comment_url
            # 我們需要在創建 comment 後再編輯它，或者在評論末尾添加「待補充」提示
            comment_body = f"""@{pr_author}

## 🤖 自動程式碼審查

**審查來源**: {pr_url}

{score_section}{cleaned_content}

---

<details>
<summary>📋 <b>程式碼變更摘要</b> (點擊展開)</summary>

此 PR 包含 {pr.changed_files} 個檔案變更 (+{pr.additions} -{pr.deletions} 行)

完整程式碼變更請至 GitHub PR 頁面查看。

</details>

---
*由 Claude AI 自動產生 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            # 創建評論
            comment = pr.create_issue_comment(comment_body)
            comment_url = comment.html_url
            self.logger.info(f"已发布审查评论到 PR #{pr_number} (作者: @{pr_author}), URL: {comment_url}")

            # 更新評論，添加 comment link
            updated_comment_body = f"""@{pr_author}

## 🤖 自動程式碼審查

**審查來源**: {pr_url}
**評論連結**: {comment_url}

{score_section}{cleaned_content}

---

<details>
<summary>📋 <b>程式碼變更摘要</b> (點擊展開)</summary>

此 PR 包含 {pr.changed_files} 個檔案變更 (+{pr.additions} -{pr.deletions} 行)

完整程式碼變更請至 GitHub PR 頁面查看。

</details>

---
*由 Claude AI 自動產生 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            comment.edit(updated_comment_body)
            self.logger.info(f"已更新評論，添加 comment link: {comment_url}")

            # 返回 comment URL
            return comment_url

            # 可选：添加审查标签
            auto_label = self.config.get("review", {}).get("auto_label", True)
            if auto_label:
                try:
                    pr.add_to_labels("auto-reviewed")
                except Exception as e:
                    self.logger.debug(f"添加标签失败: {e}")

            # 发送邮件通知（如果启用）
            email_config = self.config.get("notifications", {}).get("email", {})
            if email_config.get("enabled", False):
                recipients = self.get_pr_recipients(repo_full_name, pr_number)
                if recipients:
                    self.logger.info(f"邮件功能已启用，收件人: {', '.join(recipients)}")
                    # 邮件中发送清理后的内容
                    self.send_email_notification(repo_full_name, pr_number, cleaned_content, recipients)
                else:
                    self.logger.warning("未找到有效的邮件收件人")

            # 发送 Slack 通知（总是尝试发送，如果环境变数未设置会自动跳过）
            self.send_slack_notification(
                repo_full_name,
                pr_number,
                cleaned_content,
                pr.title,
                pr.user.login
            )

        except Exception as e:
            self.logger.error(f"发布审查评论失败: {e}")

    def _update_task_status(self, pr_id: str, status: str, progress: int, message: str):
        """更新任务状态"""
        self.db.update_task(pr_id, {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.now().isoformat()
        })

    def _process_pr_event_async(self, event_type: str, payload: Dict):
        """异步处理 PR 事件（在后台线程中执行）"""
        pr_id = None
        try:
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            repo_full_name = payload.get("repository", {}).get("full_name", "")
            pr_number = pr.get("number", 0)
            pr_id = f"{repo_full_name}#{pr_number}"

            self.logger.info(f"[后台线程] 开始处理 PR #{pr_number}")
            self._update_task_status(pr_id, "processing", 10, "開始獲取 PR 資訊")

            # 获取 PR 上下文
            self._update_task_status(pr_id, "processing", 20, "獲取 PR 變更和差異")
            context = self.get_pr_context(repo_full_name, pr_number)

            # 获取参与者信息（包含 email）
            self._update_task_status(pr_id, "processing", 30, "收集參與者 Email")

            # 执行审查
            self._update_task_status(pr_id, "processing", 40, "使用 Claude AI 審查程式碼（這可能需要 3-5 分鐘）")
            review_content = self.review_pr_with_claude(repo_full_name, pr_number)

            if review_content:
                # 提取評分
                score = self._extract_score_from_review(review_content)

                # 发布审查评论
                self._update_task_status(pr_id, "processing", 80, "發布審查評論到 GitHub")
                comment_url = self.post_review_comment(repo_full_name, pr_number, review_content)

                # 更新任務狀態並保存評分和評論連結
                update_data = {
                    'status': 'completed',
                    'progress': 100,
                    'message': f"審查完成{f' (評分: {score}/100)' if score else ''}",
                    'completed_at': datetime.now().isoformat(),
                    'review_content': review_content
                }
                if score is not None:
                    update_data['score'] = score
                if comment_url:
                    update_data['review_comment_url'] = comment_url

                # 使用 database 模組更新任務
                self.db.update_task(pr_id, update_data)

                self.logger.info(f"[后台线程] PR #{pr_number} 处理完成{f' (評分: {score}/100)' if score else ''}")
            else:
                self._update_task_status(pr_id, "failed", 0, "審查生成失敗")
                self.logger.error(f"[后台线程] PR #{pr_number} 审查生成失败")

        except Exception as e:
            self.logger.error(f"[后台线程] 处理 PR 事件失败: {e}", exc_info=True)
            if pr_id:
                self._update_task_status(pr_id, "failed", 0, f"處理失敗: {str(e)}")

    def process_pr_event(self, event_type: str, payload: Dict) -> Dict:
        """处理 PR 事件（快速验证并启动后台处理）"""
        try:
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            repo_full_name = payload.get("repository", {}).get("full_name", "")
            pr_number = pr.get("number", 0)
            pr_id = f"{repo_full_name}#{pr_number}"

            self.logger.info(f"收到 PR 事件: {event_type} - {action} - {pr_id}")

            # 检查是否应该审查
            review_triggers = self.config.get("review", {}).get("triggers", ["opened", "synchronize"])

            if action not in review_triggers:
                self.logger.info(f"动作 '{action}' 不在触发列表中，跳过审查")
                return {"status": "skipped", "reason": "action not in triggers"}

            # 检查是否是 draft PR
            if pr.get("draft", False):
                skip_draft = self.config.get("review", {}).get("skip_draft", True)
                if skip_draft:
                    self.logger.info("跳过 draft PR")
                    return {"status": "skipped", "reason": "draft PR"}

            # 初始化任务状态並保存到資料庫
            task_data = {
                "pr_id": pr_id,
                "pr_number": pr_number,
                "repo": repo_full_name,
                "pr_title": pr.get("title", ""),
                "pr_author": pr.get("user", {}).get("login", ""),
                "pr_url": pr.get("html_url", ""),
                "status": "queued",
                "progress": 0,
                "message": "等待處理",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.db.create_task(task_data)

            # 启动后台线程处理审查（避免 webhook 超时）
            thread = threading.Thread(
                target=self._process_pr_event_async,
                args=(event_type, payload),
                daemon=True
            )
            thread.start()

            self.logger.info(f"PR #{pr_number} 已加入后台处理队列")

            # 立即返回响应给 GitHub（避免超时）
            return {
                "status": "accepted",
                "message": "PR review request accepted and processing in background",
                "pr_number": pr_number,
                "repo": repo_full_name,
                "task_id": pr_id
            }

        except Exception as e:
            self.logger.error(f"处理 PR 事件失败: {e}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e)
            }


# Flask 应用
app = Flask(__name__)
auth = HTTPBasicAuth()
reviewer = None

# 用户认证数据（从环境变量读取）
users = {}

def init_auth():
    """初始化认证用户"""
    global users
    # 从环境变量读取用户名和密码
    web_username = os.getenv("WEB_USERNAME", "admin")
    web_password = os.getenv("WEB_PASSWORD", "")

    if web_password:
        # 使用密码哈希存储
        users[web_username] = generate_password_hash(web_password)
        app.logger.info(f"Web 认证已启用，用户名: {web_username}")
    else:
        app.logger.warning("WEB_PASSWORD 未设置，Web UI 将不需要认证（不安全）")

@auth.verify_password
def verify_password(username, password):
    """验证用户名和密码"""
    if not users:
        # 如果没有设置密码，允许所有访问
        return True

    if username in users and check_password_hash(users[username], password):
        return username
    return None


@app.route('/', methods=['GET'])
@auth.login_required
def index():
    """主页 - 显示任务列表（HTML）"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PR Auto-Reviewer - 任務監控</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                margin-top: 5px;
            }
            .task-list {
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .task-item {
                padding: 20px;
                border-bottom: 1px solid #eee;
                transition: background 0.3s;
            }
            .task-item:hover {
                background: #f5f5f5;
            }
            .task-item:last-child {
                border-bottom: none;
            }
            .task-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .task-title {
                font-size: 1.2em;
                font-weight: bold;
                color: #333;
            }
            .task-meta {
                color: #666;
                font-size: 0.9em;
            }
            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: bold;
            }
            .status-queued { background: #ffd700; color: #000; }
            .status-processing { background: #4169e1; color: white; }
            .status-completed { background: #32cd32; color: white; }
            .status-failed { background: #dc143c; color: white; }
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #eee;
                border-radius: 4px;
                margin: 10px 0;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transition: width 0.3s;
            }
            .task-message {
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: #666;
            }
            .refresh-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #667eea;
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 50px;
                font-size: 1em;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: all 0.3s;
            }
            .refresh-btn:hover {
                background: #764ba2;
                transform: translateY(-2px);
                box-shadow: 0 6px 8px rgba(0,0,0,0.3);
            }
        </style>
        <script>
            // 使用局部更新而不是整頁刷新，避免閃爍
            setInterval(loadTasks, 5000);
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🤖 PR Auto-Reviewer</h1>

            <div class="nav" style="text-align: center; margin-bottom: 20px;">
                <a href="/" style="color: white; text-decoration: none; padding: 10px 20px; margin: 0 10px; background: rgba(255,255,255,0.2); border-radius: 5px;">PR 審查任務</a>
                <a href="/issue-copies" style="color: white; text-decoration: none; padding: 10px 20px; margin: 0 10px; background: rgba(255,255,255,0.2); border-radius: 5px;">Issue 複製記錄</a>
            </div>

            <div class="stats" id="stats"></div>
            <div class="task-list" id="taskList"></div>
        </div>
        <button class="refresh-btn" onclick="loadTasks()">🔄 重新整理</button>

        <script>
            async function loadTasks() {
                try {
                    const response = await fetch('/api/tasks');
                    const data = await response.json();

                    // 更新統計
                    const stats = document.getElementById('stats');
                    stats.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-number">${data.total}</div>
                            <div class="stat-label">總任務數</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.queued + data.stats.processing}</div>
                            <div class="stat-label">處理中</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.completed}</div>
                            <div class="stat-label">已完成</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.stats.failed}</div>
                            <div class="stat-label">失敗</div>
                        </div>
                    `;

                    // 更新任務列表
                    const taskList = document.getElementById('taskList');
                    if (data.tasks.length === 0) {
                        taskList.innerHTML = '<div class="empty-state">目前沒有任務</div>';
                    } else {
                        taskList.innerHTML = data.tasks.map(task => {
                            // 決定狀態文字 (如果已完成且有分數,顯示分數)
                            let statusText = '';
                            if (task.status === 'queued') {
                                statusText = '等待中';
                            } else if (task.status === 'processing') {
                                statusText = '處理中';
                            } else if (task.status === 'completed') {
                                statusText = task.score ? `${task.score}/100 已完成` : '已完成';
                            } else {
                                statusText = '失敗';
                            }

                            // PR 連結顯示 (優先使用 review_comment_url)
                            const prLink = task.review_comment_url
                                ? `<a href="${task.review_comment_url}" target="_blank" style="color: #667eea; text-decoration: none;" title="查看審查評論">#${task.pr_number} 📝</a>`
                                : `<a href="${task.pr_url}" target="_blank" style="color: #667eea; text-decoration: none;">#${task.pr_number}</a>`;

                            return `
                                <div class="task-item">
                                    <div class="task-header">
                                        <div>
                                            <div class="task-title">
                                                <a href="${task.pr_url}" target="_blank" style="color: #667eea; text-decoration: none;">
                                                    ${task.pr_title || 'PR #' + task.pr_number}
                                                </a>
                                            </div>
                                            <div class="task-meta">
                                                ${task.repo} | PR: ${prLink} | 作者: ${task.pr_author} | 創建時間: ${new Date(task.created_at).toLocaleString('zh-TW')}
                                            </div>
                                        </div>
                                        <span class="status-badge status-${task.status}">
                                            ${statusText}
                                        </span>
                                    </div>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${task.progress}%"></div>
                                    </div>
                                    <div class="task-message">
                                        ${task.message} (${task.progress}%)
                                    </div>
                                </div>
                            `;
                        }).join('');
                    }
                } catch (error) {
                    console.error('載入任務失敗:', error);
                }
            }

            // 頁面載入時執行
            loadTasks();
        </script>
    </body>
    </html>
    """
    return html

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "service": "PR Auto-Reviewer",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/tasks', methods=['GET'])
@auth.login_required
def get_tasks():
    """获取所有任务状态（API）"""
    # 從資料庫讀取任務
    tasks = reviewer.db.get_all_tasks(limit=200)

    # 獲取統計數據
    stats = reviewer.db.get_task_stats()

    return jsonify({
        "total": len(tasks),
        "stats": stats,
        "tasks": tasks
    })

@app.route('/api/task/<path:task_id>', methods=['GET'])
@auth.login_required
def get_task(task_id):
    """获取单个任务状态（API）"""
    # 從資料庫讀取任務
    task = reviewer.db.get_task(task_id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify(task)


@app.route('/api/pr/<repo_owner>/<repo_name>/<int:pr_number>/participants', methods=['GET'])
@auth.login_required
def get_pr_participants_api(repo_owner: str, repo_name: str, pr_number: int):
    """获取 PR 参与者信息的 API endpoint

    示例: GET /api/pr/Intrising/my-repo/123/participants
    """
    try:
        repo_full_name = f"{repo_owner}/{repo_name}"
        participants = reviewer.get_pr_participants(repo_full_name, pr_number)

        return jsonify({
            "status": "success",
            "repo": repo_full_name,
            "pr_number": pr_number,
            "participants": participants
        }), 200

    except Exception as e:
        reviewer.logger.error(f"API 获取参与者失败: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/user/<username>', methods=['GET'])
@auth.login_required
def get_user_info_api(username: str):
    """获取用户信息的 API endpoint

    示例: GET /api/user/octocat
    """
    try:
        user_info = reviewer.get_user_info(username)

        return jsonify({
            "status": "success",
            "user": user_info
        }), 200

    except Exception as e:
        reviewer.logger.error(f"API 获取用户信息失败: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/issue-copies', methods=['GET'])
@auth.login_required
def get_issue_copies():
    """獲取 issue 複製記錄列表（API）

    Query parameters:
      - limit: 返回數量限制（默認 100）
      - status: 狀態過濾（success, failed, pending）
    """
    try:
        limit = int(request.args.get('limit', 100))
        status = request.args.get('status')

        # 從資料庫讀取複製記錄
        records = reviewer.db.get_copy_records(limit=limit, status=status)

        # 獲取統計數據
        stats = reviewer.db.get_copy_stats()

        return jsonify({
            "status": "success",
            "total": len(records),
            "stats": stats,
            "records": records
        }), 200

    except Exception as e:
        reviewer.logger.error(f"API 獲取複製記錄失敗: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/issue-copies/stats', methods=['GET'])
@auth.login_required
def get_issue_copy_stats():
    """獲取 issue 複製統計（API）"""
    try:
        stats = reviewer.db.get_copy_stats()

        return jsonify({
            "status": "success",
            "stats": stats
        }), 200

    except Exception as e:
        reviewer.logger.error(f"API 獲取統計失敗: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/comment-syncs', methods=['GET'])
@auth.login_required
def get_comment_syncs():
    """獲取評論同步記錄列表（API）

    Query parameters:
      - limit: 返回數量限制（默認 100）
      - status: 狀態過濾（success, error）
    """
    try:
        limit = int(request.args.get('limit', 100))
        status = request.args.get('status')

        # 從資料庫讀取評論同步記錄
        records = reviewer.db.get_comment_sync_records(limit=limit, status=status)

        # 獲取統計數據
        stats = reviewer.db.get_comment_sync_stats()

        return jsonify({
            "status": "success",
            "total": len(records),
            "stats": stats,
            "records": records
        }), 200

    except Exception as e:
        reviewer.logger.error(f"API 獲取評論同步記錄失敗: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/issue-copies', methods=['GET'])
@auth.login_required
def issue_copies_page():
    """Issue 複製記錄頁面（HTML）"""
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Issue Auto-Copier - 複製記錄</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 20px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 10px 20px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
            }
            .nav a:hover {
                background: rgba(255,255,255,0.3);
            }
            .tabs {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-bottom: 20px;
            }
            .tab-btn {
                padding: 10px 30px;
                border: none;
                background: rgba(255,255,255,0.2);
                color: white;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1em;
                transition: all 0.3s;
            }
            .tab-btn:hover {
                background: rgba(255,255,255,0.3);
            }
            .tab-btn.active {
                background: white;
                color: #667eea;
                font-weight: bold;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                margin-top: 5px;
            }
            .filters {
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .filter-group {
                display: inline-block;
                margin-right: 20px;
            }
            .filter-group label {
                margin-right: 10px;
                font-weight: bold;
            }
            .filter-group select {
                padding: 5px 10px;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
            .record-list {
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .record-item {
                padding: 20px;
                border-bottom: 1px solid #eee;
                transition: background 0.3s;
            }
            .record-item:hover {
                background: #f5f5f5;
            }
            .record-item:last-child {
                border-bottom: none;
            }
            .record-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .record-title {
                font-size: 1.1em;
                font-weight: bold;
                color: #333;
            }
            .record-meta {
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }
            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: bold;
            }
            .status-success { background: #32cd32; color: white; }
            .status-failed { background: #dc143c; color: white; }
            .status-pending { background: #ffd700; color: #000; }
            .labels {
                margin-top: 10px;
            }
            .label-tag {
                display: inline-block;
                padding: 3px 10px;
                margin-right: 5px;
                background: #e0e0e0;
                border-radius: 3px;
                font-size: 0.85em;
            }
            .copy-info {
                margin-top: 10px;
                padding: 10px;
                background: #f9f9f9;
                border-radius: 5px;
                font-size: 0.9em;
            }
            .copy-arrow {
                color: #667eea;
                font-weight: bold;
                margin: 0 10px;
            }
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: #666;
            }
            .refresh-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #667eea;
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 50px;
                font-size: 1em;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: all 0.3s;
            }
            .refresh-btn:hover {
                background: #764ba2;
                transform: translateY(-2px);
                box-shadow: 0 6px 8px rgba(0,0,0,0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Issue Auto-Copier</h1>

            <div class="nav">
                <a href="/">PR 審查任務</a>
                <a href="/issue-copies" class="active">Issue 複製記錄</a>
            </div>

            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('copies')">📋 Issue 複製</button>
                <button class="tab-btn" onclick="switchTab('comments')">💬 評論同步</button>
            </div>

            <div class="stats" id="stats"></div>

            <div class="filters">
                <div class="filter-group">
                    <label>狀態篩選:</label>
                    <select id="statusFilter" onchange="loadRecords()">
                        <option value="">全部</option>
                        <option value="success">成功</option>
                        <option value="failed">失敗</option>
                        <option value="pending">進行中</option>
                    </select>
                </div>
            </div>

            <div class="record-list" id="recordList"></div>
        </div>

        <button class="refresh-btn" onclick="loadRecords()">🔄 重新整理</button>

        <script>
            let currentTab = 'copies';

            function switchTab(tab) {
                currentTab = tab;

                // 更新按鈕樣式
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');

                // 載入資料
                loadRecords();
            }

            async function loadRecords() {
                try {
                    const status = document.getElementById('statusFilter').value;

                    // 根據選項卡選擇不同的 API
                    let url;
                    if (currentTab === 'comments') {
                        url = status ? `/api/comment-syncs?status=${status}` : '/api/comment-syncs';
                    } else {
                        url = status ? `/api/issue-copies?status=${status}` : '/api/issue-copies';
                    }

                    const response = await fetch(url);
                    const data = await response.json();

                    // 更新統計
                    const stats = document.getElementById('stats');

                    if (currentTab === 'comments') {
                        // 評論同步統計
                        stats.innerHTML = `
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.total}</div>
                                <div class="stat-label">總同步數</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.success}</div>
                                <div class="stat-label">成功</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.failed}</div>
                                <div class="stat-label">失敗</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.total_synced}</div>
                                <div class="stat-label">總同步目標數</div>
                            </div>
                        `;
                    } else {
                        // Issue 複製統計
                        stats.innerHTML = `
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.total}</div>
                                <div class="stat-label">總複製數</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.success}</div>
                                <div class="stat-label">成功</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.failed}</div>
                                <div class="stat-label">失敗</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.pending}</div>
                                <div class="stat-label">進行中</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.stats.total_images}</div>
                                <div class="stat-label">總圖片數</div>
                            </div>
                        `;
                    }

                    // 更新記錄列表
                    const recordList = document.getElementById('recordList');
                    if (data.records.length === 0) {
                        const emptyMessage = currentTab === 'comments' ? '目前沒有評論同步記錄' : '目前沒有複製記錄';
                        recordList.innerHTML = `<div class="empty-state">${emptyMessage}</div>`;
                    } else if (currentTab === 'comments') {
                        // 顯示評論同步記錄
                        recordList.innerHTML = data.records.map(record => {
                            const statusText = {
                                'success': '成功',
                                'error': '失敗'
                            }[record.status] || record.status;

                            const targetsHtml = record.synced_to_repos && record.synced_to_repos.length > 0
                                ? record.synced_to_repos.map(target => `<span class="label-tag">${target}</span>`).join(' ')
                                : '';

                            const errorInfo = record.status === 'error' && record.error_message
                                ? `<div style="color: #dc143c; margin-top: 10px;">錯誤: ${record.error_message}</div>`
                                : '';

                            const commentPreview = record.comment_body
                                ? (record.comment_body.length > 100
                                    ? record.comment_body.substring(0, 100) + '...'
                                    : record.comment_body)
                                : '';

                            return `
                                <div class="record-item">
                                    <div class="record-header">
                                        <div>
                                            <div class="record-title">💬 ${record.comment_author} 的評論</div>
                                            <div class="record-meta">
                                                ${new Date(record.created_at).toLocaleString('zh-TW')}
                                            </div>
                                        </div>
                                        <span class="status-badge status-${record.status}">${statusText}</span>
                                    </div>
                                    <div class="copy-info">
                                        <a href="${record.source_issue_url}" target="_blank">${record.source_repo} #${record.source_issue_number}</a>
                                        <span class="copy-arrow">→</span>
                                        <span>${record.synced_count} / ${record.total_targets} 個目標</span>
                                    </div>
                                    <div style="margin-top: 10px; padding: 8px; background: #f5f5f5; border-radius: 4px; color: #666; font-size: 13px;">
                                        ${commentPreview}
                                    </div>
                                    <div class="labels" style="margin-top: 8px;">
                                        同步到: ${targetsHtml}
                                    </div>
                                    ${errorInfo}
                                </div>
                            `;
                        }).join('');
                    } else {
                        // 顯示 Issue 複製記錄
                        recordList.innerHTML = data.records.map(record => {
                            const statusText = {
                                'success': '成功',
                                'failed': '失敗',
                                'pending': '進行中'
                            }[record.status] || record.status;

                            const labelsHtml = record.source_labels && record.source_labels.length > 0
                                ? `<div class="labels">
                                    Labels: ${record.source_labels.map(l => `<span class="label-tag">${l}</span>`).join('')}
                                   </div>`
                                : '';

                            const targetInfo = record.status === 'success' && record.target_issue_url
                                ? `<a href="${record.target_issue_url}" target="_blank">${record.target_repo} #${record.target_issue_number}</a>`
                                : record.target_repo;

                            const errorInfo = record.status === 'failed' && record.error_message
                                ? `<div style="color: #dc143c; margin-top: 10px;">錯誤: ${record.error_message}</div>`
                                : '';

                            const imagesInfo = record.images_count > 0
                                ? `<span style="margin-left: 20px;">📷 ${record.images_count} 張圖片</span>`
                                : '';

                            return `
                                <div class="record-item">
                                    <div class="record-header">
                                        <div>
                                            <div class="record-title">${record.source_issue_title || 'Issue #' + record.source_issue_number}</div>
                                            <div class="record-meta">
                                                ${new Date(record.created_at).toLocaleString('zh-TW')}
                                            </div>
                                        </div>
                                        <span class="status-badge status-${record.status}">${statusText}</span>
                                    </div>
                                    <div class="copy-info">
                                        <a href="${record.source_issue_url}" target="_blank">${record.source_repo} #${record.source_issue_number}</a>
                                        <span class="copy-arrow">→</span>
                                        ${targetInfo}
                                        ${imagesInfo}
                                    </div>
                                    ${labelsHtml}
                                    ${errorInfo}
                                </div>
                            `;
                        }).join('');
                    }
                } catch (error) {
                    console.error('載入記錄失敗:', error);
                }
            }

            // 頁面載入時執行
            loadRecords();

            // 自動刷新（每 10 秒）
            setInterval(loadRecords, 10000);
        </script>
    </body>
    </html>
    """
    return html


@app.route('/webhook', methods=['POST'])
@app.route('/webhook/', methods=['POST'])
def webhook():
    """GitHub webhook 端點"""
    try:
        # 验证签名
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not reviewer.verify_webhook_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 401

        # 获取事件类型
        event_type = request.headers.get('X-GitHub-Event', '')
        payload = request.json

        # 記錄收到的事件類型
        repo_name = payload.get('repository', {}).get('full_name', 'unknown')
        reviewer.logger.info(f"收到 webhook: 事件類型={event_type}, repository={repo_name}")

        # 处理 PR 事件
        if event_type == 'pull_request':
            result = reviewer.process_pr_event(event_type, payload)
            return jsonify(result), 200

        # 处理 Issue 事件
        elif event_type == 'issues':
            if reviewer.issue_copier:
                result = reviewer.issue_copier.process_issue_event(event_type, payload)
                return jsonify(result), 200
            else:
                return jsonify({"status": "ignored", "reason": "issue copier not enabled"}), 200

        # 处理 Issue Comment 事件（同步評論）
        elif event_type == 'issue_comment':
            if reviewer.issue_copier:
                result = reviewer.issue_copier.process_comment_event(event_type, payload)
                return jsonify(result), 200
            else:
                return jsonify({"status": "ignored", "reason": "issue copier not enabled"}), 200

        # 其他事件忽略
        else:
            return jsonify({"status": "ignored", "event": event_type}), 200

    except Exception as e:
        reviewer.logger.error(f"Webhook 处理失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def main():
    """主程序入口"""
    global reviewer

    try:
        # 初始化审查器
        reviewer = PRReviewer()

        # 初始化认证
        init_auth()

        # 获取配置
        host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
        port = int(os.getenv("WEBHOOK_PORT", "5000"))
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

        reviewer.logger.info(f"启动 webhook 服务器: {host}:{port}")

        # 启动 Flask 应用
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        print(f"启动失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
