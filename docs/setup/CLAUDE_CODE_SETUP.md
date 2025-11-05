# GitHub PR Auto-Reviewer - 使用 Claude Code CLI

这个工具使用 **Claude Code CLI** 在 Docker 容器内审查 PR，无需 API key。

## 🎯 架构

```
GitHub Webhook → Flask 服务器 → Claude Code CLI → PR 审查评论
                     ↓
                Docker 容器
                (已安装 Claude Code)
```

## 🚀 快速开始

### 1. 准备环境

```bash
# 克隆或进入项目目录
cd github_monitor

# 初始化配置
make -f Makefile.reviewer init

# 编辑 .env
vim .env
```

设置必要的环境变量：

```bash
# GitHub Token（必需）
GITHUB_TOKEN=ghp_your_github_token

# Webhook 密钥（推荐）
WEBHOOK_SECRET=your-random-secret

# Claude Code 路径（容器内已设置，通常不需要改）
CLAUDE_CODE_PATH=claude-code
```

**注意**：不需要 `ANTHROPIC_API_KEY`！

### 2. 构建 Docker 镜像

```bash
# 构建镜像（包含 Claude Code CLI）
docker-compose -f docker-compose.reviewer.yml build
```

这会创建一个包含以下组件的镜像：
- Python 3.11
- Flask
- Claude Code CLI
- 所有必要的依赖

### 3. 登录 Claude Code

**重要**：在运行服务之前，需要在容器内登录 Claude Code。

#### 方法 1：交互式登录（推荐用于首次设置）

```bash
# 启动临时容器进行登录
docker-compose -f docker-compose.reviewer.yml run --rm pr-reviewer /bin/bash

# 在容器内运行
claude-code auth login

# 按照提示完成登录
# 登录成功后退出
exit
```

#### 方法 2：使用已有的认证配置

如果你在主机上已经登录了 Claude Code：

```bash
# 找到 Claude Code 配置目录
ls ~/.config/claude-code/

# 在 docker-compose.reviewer.yml 中挂载配置
# 添加到 volumes:
#   - ~/.config/claude-code:/home/appuser/.config/claude-code:ro
```

修改 `docker-compose.reviewer.yml`：

```yaml
services:
  pr-reviewer:
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - pr-reviewer-logs:/var/log/github-monitor
      # 添加这一行
      - ~/.config/claude-code:/home/appuser/.config/claude-code:ro
```

### 4. 启动服务

```bash
# 启动服务
docker-compose -f docker-compose.reviewer.yml up -d

# 查看日志
docker-compose -f docker-compose.reviewer.yml logs -f

# 检查健康状态
curl http://localhost:5000/health
```

### 5. 配置 GitHub Webhook

在你的 GitHub 仓库设置中：

1. 进入 `Settings` → `Webhooks` → `Add webhook`

2. 配置：
   - **Payload URL**: `http://your-server:5000/webhook`
   - **Content type**: `application/json`
   - **Secret**: 你的 `WEBHOOK_SECRET`
   - **Which events**: 选择 `Pull requests`

3. 保存

### 6. 测试

创建一个测试 PR：

```bash
git checkout -b test-auto-review
echo "# Test" > test.md
git add test.md
git commit -m "test: Claude Code auto review"
git push origin test-auto-review
```

在 GitHub 上创建 PR，几秒钟后应该会看到 Claude Code 的自动审查评论。

## 📋 详细配置

### Claude Code 相关配置

在 `config.yaml` 中：

```yaml
review:
  # 触发审查的动作
  triggers:
    - opened       # PR 创建时
    - synchronize  # PR 更新时
    - reopened     # PR 重新开启时

  # 跳过 draft PR
  skip_draft: true

  # 自动添加标签
  auto_label: true

  # 审查重点
  focus_areas:
    - "代码质量和可读性"
    - "潜在的 bug 和错误处理"
    - "性能问题和优化建议"
    - "安全漏洞和最佳实践"
    - "测试覆盖率"
    - "文档和注释完整性"

  # 回复语言
  language: "zh-TW"
```

### 环境变量

```bash
# .env 文件

# GitHub（必需）
GITHUB_TOKEN=ghp_xxx

# Webhook（推荐）
WEBHOOK_SECRET=your-secret
WEBHOOK_PORT=5000

# Claude Code（可选）
CLAUDE_CODE_PATH=claude-code  # 默认值

# 日志
LOG_LEVEL=INFO
```

## 🔧 运维命令

### 使用 Makefile

```bash
# 查看所有命令
make -f Makefile.reviewer help

# 一键部署
make -f Makefile.reviewer deploy

# 查看日志
make -f Makefile.reviewer logs

# 重启服务
make -f Makefile.reviewer restart

# 进入容器调试
make -f Makefile.reviewer shell
```

### 使用 Docker Compose

```bash
# 启动
docker-compose -f docker-compose.reviewer.yml up -d

# 停止
docker-compose -f docker-compose.reviewer.yml down

# 查看日志
docker-compose -f docker-compose.reviewer.yml logs -f pr-reviewer

# 进入容器
docker exec -it pr-reviewer /bin/bash
```

## 🔍 故障排查

### 1. Claude Code 未登录

**症状**：日志显示 "Claude Code 执行失败" 或认证错误

**解决**：

```bash
# 进入容器
docker exec -it pr-reviewer /bin/bash

# 检查登录状态
claude-code auth status

# 如果未登录，执行登录
claude-code auth login

# 退出容器
exit

# 重启服务
docker-compose -f docker-compose.reviewer.yml restart
```

### 2. Webhook 未触发

**症状**：创建 PR 后没有收到审查评论

**检查**：

```bash
# 查看服务日志
docker-compose -f docker-compose.reviewer.yml logs pr-reviewer

# 检查 webhook 端点
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"test"}'

# 在 GitHub webhook 设置页面查看 "Recent Deliveries"
```

### 3. Claude Code 执行超时

**症状**：大型 PR 审查时超时

**解决**：

修改 `pr_reviewer.py` 中的超时时间：

```python
# 在 review_pr_with_claude 方法中
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=600,  # 改为 10 分钟
    encoding='utf-8'
)
```

### 4. 权限问题

**症状**：无法写入日志或配置

**解决**：

```bash
# 检查文件权限
ls -la logs/

# 修复权限
sudo chown -R 1000:1000 logs/
```

### 5. Claude Code 命令不存在

**症状**：`claude-code: command not found`

**解决**：

```bash
# 重新构建镜像
docker-compose -f docker-compose.reviewer.yml build --no-cache

# 确认 Claude Code 已安装
docker-compose -f docker-compose.reviewer.yml run --rm pr-reviewer which claude-code
```

## 💡 高级用法

### 自定义审查提示词

编辑 `pr_reviewer.py` 中的 `_build_review_prompt` 方法：

```python
def _build_review_prompt(self, context: Dict, diff: str, config: Dict) -> str:
    # 自定义你的提示词
    prompt = f"""
    你是一位资深的 [你的技术栈] 专家...

    请审查以下 PR:
    {diff}

    重点关注:
    - [自定义关注点 1]
    - [自定义关注点 2]
    """
    return prompt
```

### 限制审查的文件

在 `get_pr_diff` 中添加过滤：

```python
def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
    files = pr.get_files()

    # 只审查特定类型的文件
    allowed_extensions = ['.py', '.js', '.ts', '.go']

    for file in files:
        # 跳过不需要审查的文件
        if not any(file.filename.endswith(ext) for ext in allowed_extensions):
            continue

        # ... 处理文件
```

### 持久化 Claude Code 配置

在 `docker-compose.reviewer.yml` 中添加命名卷：

```yaml
volumes:
  claude-code-config:
    driver: local

services:
  pr-reviewer:
    volumes:
      - claude-code-config:/home/appuser/.config/claude-code
```

## 🔒 安全建议

1. **使用 Webhook Secret**：防止未授权的请求
2. **使用 HTTPS**：在生产环境使用反向代理（Nginx/Traefik）
3. **限制访问**：配置防火墙只允许 GitHub IP
4. **定期更新**：保持 Claude Code CLI 和依赖最新

## 📊 性能优化

### 减少审查大小

```python
# 限制审查的文件数量
MAX_FILES = 20
MAX_DIFF_SIZE = 50000  # 字符

def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
    files = list(pr.get_files())[:MAX_FILES]

    diff_content = []
    total_size = 0

    for file in files:
        if total_size > MAX_DIFF_SIZE:
            diff_content.append("\n... (剩余文件已省略)")
            break

        # 添加 diff
        total_size += len(file.patch or "")
```

### 并发处理

目前每次 webhook 调用都会阻塞处理。如果需要处理大量 PR，可以：

1. 使用消息队列（如 Redis + Celery）
2. 使用异步处理（async/await）
3. 使用多个 worker 容器

## 📝 与 API 版本的区别

| 特性 | Claude Code CLI | Anthropic API |
|------|----------------|---------------|
| 需要 API Key | ❌ | ✅ |
| 认证方式 | 命令行登录 | API Key |
| 成本 | 免费/订阅 | 按使用量付费 |
| 灵活性 | 中等 | 高 |
| 响应速度 | 较慢 | 快 |
| 适用场景 | 个人/小团队 | 企业/高频使用 |

## 🎓 最佳实践

1. **定期检查登录状态**：Claude Code 会话可能过期
2. **监控资源使用**：Claude Code 可能消耗较多内存
3. **备份配置**：定期备份 Claude Code 认证配置
4. **测试环境**：先在测试仓库验证功能
5. **日志监控**：关注错误日志及时处理

## 🔗 相关资源

- [Claude Code 文档](https://docs.anthropic.com/claude-code)
- [GitHub Webhooks](https://docs.github.com/en/webhooks)
- [Docker 最佳实践](https://docs.docker.com/develop/dev-best-practices/)

## 📞 获取帮助

如有问题：

1. 查看日志：`make -f Makefile.reviewer logs`
2. 检查配置：`make -f Makefile.reviewer check`
3. 健康检查：`make -f Makefile.reviewer health`

---

**Happy Reviewing with Claude Code! 🚀**
