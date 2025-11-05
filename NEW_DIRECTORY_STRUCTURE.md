# 新的目录结构设计

## 建议的目录结构

```
github_monitor/
├── README.md                       # 主文档
├── LICENSE
├── requirements.txt
├── config.yaml                     # 主配置文件
├── .env.example
├── .gitignore
│
├── docs/                           # 所有文档
│   ├── QUICKSTART.md
│   ├── DEPLOYMENT.md
│   ├── CONFIGURATION_GUIDE.md
│   ├── FEATURES.md
│   ├── PROJECT_STRUCTURE.md
│   ├── SUMMARY.md
│   ├── FILES_INDEX.md
│   ├── setup/                      # 设置指南
│   │   ├── GITHUB_TOKEN_SETUP.md
│   │   ├── GITHUB_WEBHOOK_CONFIG.md
│   │   ├── CLAUDE_CLI_SETUP.md
│   │   ├── CLAUDE_CODE_SETUP.md
│   │   ├── MSMTP_SETUP.md
│   │   └── GITHUB_USER_INFO_API.md
│   ├── testing/                    # 测试相关文档
│   │   └── WEBHOOK_TEST.md
│   └── migration/                  # 迁移文档
│       ├── CODEX_MIGRATION_SUMMARY.md
│       └── README_REVIEWER.md
│
├── src/                            # 源代码
│   ├── pr_monitor.py              # PR 监控主程序
│   ├── pr_reviewer.py             # PR 审查（Codex CLI 版本）
│   ├── pr_reviewer_api.py         # PR 审查（Claude API 版本）
│   └── healthcheck.py
│
├── scripts/                        # 脚本文件
│   ├── deploy.sh
│   ├── setup_claude_auth.sh
│   ├── test_webhook.py
│   ├── test_webhook_curl.sh
│   ├── test_webhook_simple.sh
│   ├── test_email.py
│   ├── test_github_permissions.py
│   └── test_codex_integration.py
│
├── docker/                         # Docker 相关文件
│   ├── Dockerfile                 # 主 Dockerfile
│   ├── Dockerfile.claude
│   ├── Dockerfile.reviewer
│   ├── docker-compose.yml         # 主 compose 文件
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── docker-compose.pr-reviewer.yml
│   ├── docker-compose.reviewer.yml
│   ├── docker-compose.reviewer-cli.yml
│   ├── docker-compose.webhook-simple.yml
│   └── docker-compose.webhook-test.yml
│
├── config/                         # 配置文件示例和模板
│   ├── msmtprc.example
│   └── .msmtprc.template
│
├── build/                          # 构建相关
│   ├── Makefile
│   └── Makefile.reviewer
│
└── .private/                       # 私有配置（不提交到 git）
    ├── .env
    └── .msmtprc
```

## 文件分类

### 文档类 (docs/)
- 设置指南
- 配置指南
- 测试文档
- 迁移文档

### 源代码 (src/)
- Python 应用程序

### 脚本 (scripts/)
- 部署脚本
- 测试脚本
- 工具脚本

### Docker (docker/)
- Dockerfile
- docker-compose 文件

### 配置 (config/)
- 配置模板
- 示例文件

### 构建 (build/)
- Makefile

### 私有 (.private/)
- 敏感配置文件
- 不提交到版本控制
