# 项目目录结构（已整理）

## 目录结构

```
github_monitor/
├── README.md                       # 主文档
├── LICENSE
├── requirements.txt                # Python 依赖
├── config.yaml                     # 主配置文件
├── .env.example                    # 环境变量示例
├── .gitignore
├── NEW_DIRECTORY_STRUCTURE.md      # 目录结构设计文档
│
├── .env -> .private/.env           # 符号链接（向后兼容）
├── .msmtprc -> .private/.msmtprc   # 符号链接（向后兼容）
├── Dockerfile -> docker/Dockerfile # 符号链接（向后兼容）
├── docker-compose.pr-reviewer.yml -> docker/docker-compose.pr-reviewer.yml
│
├── docs/                           # 📚 所有文档
│   ├── QUICKSTART.md
│   ├── DEPLOYMENT.md
│   ├── CONFIGURATION_GUIDE.md
│   ├── FEATURES.md
│   ├── PROJECT_STRUCTURE.md
│   ├── PROJECT_STRUCTURE_FINAL.md  # 本文件
│   ├── SUMMARY.md
│   ├── FILES_INDEX.md
│   ├── setup/                      # 设置指南
│   │   ├── GITHUB_TOKEN_SETUP.md
│   │   ├── GITHUB_WEBHOOK_CONFIG.md
│   │   ├── CLAUDE_CLI_SETUP.md
│   │   ├── CLAUDE_CODE_SETUP.md
│   │   ├── MSMTP_SETUP.md
│   │   ├── WEBHOOK_SETUP.md
│   │   └── GITHUB_USER_INFO_API.md
│   ├── testing/                    # 测试相关文档
│   │   └── WEBHOOK_TEST.md
│   └── migration/                  # 迁移文档
│       ├── CODEX_MIGRATION_SUMMARY.md
│       └── README_REVIEWER.md
│
├── src/                            # 💻 源代码
│   ├── pr_monitor.py              # PR 监控主程序
│   ├── pr_reviewer.py             # PR 审查（Codex CLI 版本）✨
│   ├── pr_reviewer_api.py         # PR 审查（Claude API 版本）
│   └── healthcheck.py             # 健康检查
│
├── scripts/                        # 🔧 脚本文件
│   ├── deploy.sh
│   ├── setup_claude_auth.sh
│   ├── test_webhook.py
│   ├── test_webhook_curl.sh
│   ├── test_webhook_simple.sh
│   ├── test_email.py
│   ├── test_github_permissions.py
│   └── test_codex_integration.py
│
├── docker/                         # 🐳 Docker 相关文件
│   ├── Dockerfile                 # 主 Dockerfile（已更新路径）
│   ├── Dockerfile.claude
│   ├── Dockerfile.reviewer
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── docker-compose.pr-reviewer.yml  # 当前使用 ✨
│   ├── docker-compose.reviewer.yml
│   ├── docker-compose.reviewer-cli.yml
│   ├── docker-compose.webhook-simple.yml
│   └── docker-compose.webhook-test.yml
│
├── config/                         # ⚙️ 配置文件示例和模板
│   ├── msmtprc.example
│   └── .msmtprc.template
│
├── build/                          # 🏗️ 构建相关
│   ├── Makefile
│   └── Makefile.reviewer
│
└── .private/                       # 🔒 私有配置（不提交到 git）
    ├── .env                        # 实际环境变量
    └── .msmtprc                    # 实际邮件配置

```

## 当前运行配置

### 使用的文件
- **主程序**: `src/pr_reviewer.py` (Codex CLI 版本)
- **Docker 文件**: `docker/Dockerfile`
- **Docker Compose**: `docker/docker-compose.pr-reviewer.yml`
- **配置文件**: `config.yaml`
- **环境变量**: `.private/.env`
- **邮件配置**: `.private/.msmtprc`

### 容器信息
- **容器名**: `pr-reviewer`
- **镜像**: `github-monitor:latest`
- **端口**: 8080
- **AI 模型**: gpt-5-codex (OpenAI Codex)

## 启动命令

### 使用符号链接（推荐，向后兼容）
```bash
# 构建
docker compose -f docker-compose.pr-reviewer.yml build

# 启动
docker compose -f docker-compose.pr-reviewer.yml up -d

# 查看日志
docker compose -f docker-compose.pr-reviewer.yml logs -f

# 停止
docker compose -f docker-compose.pr-reviewer.yml down
```

### 直接使用 docker 目录
```bash
cd docker

docker compose -f docker-compose.pr-reviewer.yml build
docker compose -f docker-compose.pr-reviewer.yml up -d
```

## 文件分类说明

### 📚 docs/ - 文档目录
所有项目文档，按类型分为：
- 主要文档（设置、部署、配置等）
- `setup/` - 各种设置指南
- `testing/` - 测试相关文档
- `migration/` - 迁移和历史文档

### 💻 src/ - 源代码
所有 Python 应用程序源代码

### 🔧 scripts/ - 脚本
部署、测试和工具脚本

### 🐳 docker/ - Docker
所有 Docker 相关配置文件

### ⚙️ config/ - 配置模板
配置文件的示例和模板

### 🏗️ build/ - 构建
Makefile 等构建工具

### 🔒 .private/ - 私有配置
敏感配置文件，已添加到 .gitignore

## 安全配置

### .gitignore 已更新
以下文件/目录不会被提交到 Git：
- `.private/` - 整个私有目录
- `.env` - 环境变量文件
- `.msmtprc` - 邮件配置文件

### .env.example 已清理
- `WEBHOOK_SECRET` 的值已改为占位符
- 所有敏感信息已移除

## 向后兼容性

通过符号链接保持向后兼容：
- `.env` → `.private/.env`
- `.msmtprc` → `.private/.msmtprc`
- `Dockerfile` → `docker/Dockerfile`
- `docker-compose.pr-reviewer.yml` → `docker/docker-compose.pr-reviewer.yml`

这样现有的命令和脚本仍然可以正常工作。

## 测试验证

✅ 所有测试通过：
1. Docker 镜像构建成功
2. 容器启动正常
3. Health 端点响应正常
4. Codex CLI 可用
5. msmtp 配置正确挂载

## 下一步

项目结构已完全整理完成，可以安全地提交到版本控制系统。
