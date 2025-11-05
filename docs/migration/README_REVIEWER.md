# GitHub PR Auto-Reviewer

使用 Claude Code CLI 自动审查 GitHub Pull Requests 的 Webhook 服务。

## 🎯 特性

- ✅ **零 API 成本**：使用 Claude Code CLI，无需 Anthropic API Key
- ✅ **自动触发**：收到 GitHub webhook 时自动审查 PR
- ✅ **智能分析**：代码质量、bug、性能、安全等全面审查
- ✅ **Docker 化**：开箱即用的容器化部署
- ✅ **安全可靠**：支持 webhook 签名验证

## 🚀 快速开始（3 步）

```bash
# 1. 构建镜像
docker-compose -f docker-compose.reviewer.yml build

# 2. 登录 Claude Code（首次）
docker-compose -f docker-compose.reviewer.yml run --rm pr-reviewer claude-code auth login

# 3. 启动服务
docker-compose -f docker-compose.reviewer.yml up -d
```

然后在 GitHub 仓库设置 webhook 指向 `http://your-server:5000/webhook`。

## 📚 文档

- **[Claude Code 设置指南](CLAUDE_CODE_SETUP.md)** - 完整的安装和配置教程
- **[Webhook 设置指南](WEBHOOK_SETUP.md)** - GitHub webhook 配置详情
- **[配置指南](CONFIGURATION_GUIDE.md)** - 自定义审查规则

## 🔧 核心配置

### 环境变量 (.env)

```bash
# GitHub（必需）
GITHUB_TOKEN=ghp_xxx

# Webhook
WEBHOOK_SECRET=your-secret
WEBHOOK_PORT=5000

# Claude Code（可选，默认值通常可用）
CLAUDE_CODE_PATH=claude-code
```

### 审查配置 (config.yaml)

```yaml
review:
  triggers:
    - opened       # PR 创建
    - synchronize  # PR 更新
    - reopened     # PR 重开

  skip_draft: true
  auto_label: true

  focus_areas:
    - "代码质量和可读性"
    - "潜在 bug 和错误处理"
    - "性能问题"
    - "安全漏洞"

  language: "zh-TW"
```

## 🎬 使用示例

1. 创建 PR
2. GitHub 发送 webhook 到你的服务器
3. 服务器调用 Claude Code 审查代码
4. 审查结果自动发布为 PR 评论

## 🛠️ 常用命令

```bash
# 使用 Makefile
make -f Makefile.reviewer deploy   # 一键部署
make -f Makefile.reviewer logs     # 查看日志
make -f Makefile.reviewer health   # 健康检查
make -f Makefile.reviewer shell    # 进入容器

# 或使用 Docker Compose
docker-compose -f docker-compose.reviewer.yml up -d
docker-compose -f docker-compose.reviewer.yml logs -f
docker-compose -f docker-compose.reviewer.yml down
```

## 🔍 故障排查

### Claude Code 未登录？

```bash
docker exec -it pr-reviewer claude-code auth login
```

### Webhook 未触发？

```bash
# 检查日志
docker-compose -f docker-compose.reviewer.yml logs pr-reviewer

# 测试端点
curl http://localhost:5000/health
```

### 审查失败？

```bash
# 查看详细日志
docker-compose -f docker-compose.reviewer.yml logs pr-reviewer | grep ERROR
```

## 📊 架构

```
┌─────────────┐
│   GitHub    │
│     PR      │
└──────┬──────┘
       │ webhook
       ▼
┌─────────────────────────┐
│   Flask Webhook 服务器  │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Claude Code CLI        │
│  (Docker 容器内)        │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  审查结果自动发布到 PR  │
└─────────────────────────┘
```

## 🆚 与其他方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Claude Code CLI** | 免费/订阅制，简单 | 需要登录，响应稍慢 |
| Anthropic API | 快速，灵活 | 按使用量付费 |
| GitHub Copilot | 原生集成 | 有限的审查能力 |

## 💡 使用建议

1. **小团队/个人项目**：使用 Claude Code CLI（本项目）
2. **企业/高频使用**：考虑 Anthropic API 版本
3. **测试环境**：先在测试仓库验证

## 🔒 安全性

- ✅ Webhook 签名验证
- ✅ 非 root 用户运行
- ✅ 只读文件系统
- ✅ 资源限制

## 📝 许可证

MIT License

## 🤝 贡献

欢迎 PR 和 Issue！

---

**详细文档请查看 [CLAUDE_CODE_SETUP.md](CLAUDE_CODE_SETUP.md)**
