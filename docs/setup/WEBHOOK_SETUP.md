# GitHub PR Auto-Reviewer - Webhook 设置指南

这个工具会在收到 GitHub webhook 时自动使用 Claude AI 审查 Pull Request。

## 📋 功能特性

- ✅ **自动 PR 审查**：收到 webhook 时自动触发 Claude AI 审查
- ✅ **智能分析**：分析代码质量、潜在 bug、性能问题、安全漏洞等
- ✅ **自动评论**：将审查结果自动发布为 PR 评论
- ✅ **安全验证**：支持 GitHub webhook 签名验证
- ✅ **灵活配置**：可自定义审查重点、触发条件等

## 🚀 快速开始

### 1. 环境配置

复制并编辑环境变量文件：

```bash
cp .env.example .env
vim .env
```

必须设置的环境变量：

```bash
# GitHub Token（需要 repo 权限）
GITHUB_TOKEN=ghp_your_github_token

# Webhook 密钥（可选但推荐）
WEBHOOK_SECRET=your-random-secret-string

# Webhook 服务端口
WEBHOOK_PORT=5000
```

**注意**：本项目使用 **Claude Code CLI** 而非 Anthropic API，无需 API Key。详见 `CLAUDE_CODE_SETUP.md`。

### 2. 配置审查规则

编辑 `config.yaml`：

```yaml
review:
  # Claude 模型
  model: "claude-3-5-sonnet-20241022"

  # 触发审查的 PR 动作
  triggers:
    - opened       # PR 被创建
    - synchronize  # PR 有新提交
    - reopened     # PR 被重新开启

  # 是否跳过 draft PR
  skip_draft: true

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

### 3. 启动服务

使用 Docker Compose 启动：

```bash
# 构建镜像
docker-compose -f docker-compose.reviewer.yml build

# 启动服务
docker-compose -f docker-compose.reviewer.yml up -d

# 查看日志
docker-compose -f docker-compose.reviewer.yml logs -f

# 检查服务状态
curl http://localhost:5000/health
```

### 4. 配置 GitHub Webhook

#### 4.1 在 GitHub 仓库设置 Webhook

1. 进入仓库的 `Settings` → `Webhooks` → `Add webhook`

2. 配置 webhook：
   - **Payload URL**: `http://your-server:5000/webhook`
   - **Content type**: `application/json`
   - **Secret**: 填入你在 `.env` 中设置的 `WEBHOOK_SECRET`
   - **SSL verification**: 如果使用 HTTPS，启用此选项

3. 选择触发事件：
   - 勾选 `Pull requests`

4. 点击 `Add webhook`

#### 4.2 使用 ngrok 本地测试（可选）

如果在本地测试，可以使用 ngrok：

```bash
# 安装 ngrok
# https://ngrok.com/download

# 启动 ngrok
ngrok http 5000

# 将 ngrok 提供的 URL 设置为 webhook URL
# 例如: https://abc123.ngrok.io/webhook
```

### 5. 测试 Webhook

创建一个测试 PR：

```bash
# 在你的仓库中
git checkout -b test-pr-review
echo "test" >> test.txt
git add test.txt
git commit -m "test: trigger PR review"
git push origin test-pr-review

# 在 GitHub 上创建 PR
```

查看服务日志：

```bash
docker-compose -f docker-compose.reviewer.yml logs -f pr-reviewer
```

几秒钟后，你应该会在 PR 中看到 Claude 的自动审查评论。

## 📊 工作流程

```
GitHub PR 事件
    ↓
GitHub Webhook
    ↓
验证签名
    ↓
检查触发条件
    ↓
获取 PR diff
    ↓
调用 Claude API 审查
    ↓
发布审查评论到 PR
```

## ⚙️ 高级配置

### 自定义审查提示词

编辑 `pr_reviewer.py` 中的 `_build_review_prompt` 方法来自定义审查提示词。

### 使用不同的 Claude 模型

在 `config.yaml` 中修改：

```yaml
review:
  model: "claude-3-opus-20240229"  # 更强大但更慢
  # 或
  model: "claude-3-haiku-20240307"  # 更快但能力较弱
```

### 跳过特定文件

可以在代码中添加文件过滤逻辑：

```python
def should_review_file(filename: str) -> bool:
    # 跳过生成的文件
    if filename.endswith('.min.js'):
        return False
    if 'generated' in filename:
        return False
    return True
```

### 限制审查的文件数量

为了避免超出 token 限制，可以限制审查的文件：

```python
# 在 get_pr_diff 中
max_files = 20
for i, file in enumerate(files):
    if i >= max_files:
        break
    # ...
```

## 🔒 安全最佳实践

### 1. 使用 Webhook Secret

**强烈建议**设置 `WEBHOOK_SECRET` 来验证请求来自 GitHub：

```bash
# 生成随机密钥
openssl rand -hex 32

# 设置到 .env
WEBHOOK_SECRET=your-generated-secret
```

### 2. 使用 HTTPS

在生产环境中，使用 Nginx 或 Traefik 提供 HTTPS：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /webhook {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 限制访问

使用防火墙限制只有 GitHub 的 IP 可以访问 webhook 端点：

```bash
# GitHub webhook IP 范围
# https://api.github.com/meta

# 使用 iptables 或云服务商的安全组
```

### 4. 保护敏感信息

- 不要将 `.env` 文件提交到 Git
- 使用 Docker Secrets 或密钥管理服务
- 定期轮换 API keys

## 🛠️ 故障排查

### Webhook 未触发

```bash
# 检查 GitHub webhook 配置页面的 "Recent Deliveries"
# 查看是否有错误信息

# 检查服务日志
docker-compose -f docker-compose.reviewer.yml logs pr-reviewer

# 测试 webhook 端点
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"test"}'
```

### 签名验证失败

```bash
# 检查 WEBHOOK_SECRET 是否一致
docker exec pr-reviewer env | grep WEBHOOK_SECRET

# 在 GitHub webhook 设置中检查 Secret
```

### Claude API 调用失败

```bash
# 检查 API key
docker exec pr-reviewer env | grep ANTHROPIC_API_KEY

# 检查 API 配额
# https://console.anthropic.com/

# 查看详细错误
docker-compose -f docker-compose.reviewer.yml logs pr-reviewer | grep -i error
```

### 无法发布评论

```bash
# 检查 GitHub Token 权限
# 需要 repo 权限

# 测试 Token
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/user
```

## 📈 监控和日志

### 查看实时日志

```bash
docker-compose -f docker-compose.reviewer.yml logs -f pr-reviewer
```

### 日志文件位置

```bash
# 容器内
/var/log/github-monitor/app.log

# 主机上
./logs/app.log
```

### 性能监控

```bash
# 查看资源使用
docker stats pr-reviewer

# 查看请求响应时间
# 在日志中搜索 "审查完成" 相关信息
```

## 🔧 运维命令

```bash
# 启动服务
docker-compose -f docker-compose.reviewer.yml up -d

# 停止服务
docker-compose -f docker-compose.reviewer.yml down

# 重启服务
docker-compose -f docker-compose.reviewer.yml restart

# 查看状态
docker-compose -f docker-compose.reviewer.yml ps

# 更新代码并重启
git pull
docker-compose -f docker-compose.reviewer.yml build
docker-compose -f docker-compose.reviewer.yml up -d

# 进入容器调试
docker exec -it pr-reviewer /bin/bash
```

## 📝 API 端点

### `GET /health`

健康检查端点

**响应：**
```json
{
  "status": "healthy",
  "service": "PR Auto-Reviewer",
  "timestamp": "2024-03-15T10:00:00"
}
```

### `POST /webhook`

GitHub webhook 端点

**请求头：**
- `X-GitHub-Event`: 事件类型（例如 `pull_request`）
- `X-Hub-Signature-256`: 签名

**请求体：**
GitHub webhook payload

**响应：**
```json
{
  "status": "success",
  "pr_number": 123,
  "repo": "owner/repo",
  "review_length": 1500
}
```

## 🎯 使用场景

### 场景 1: 团队协作

在团队中使用，自动审查所有 PR，提高代码质量：

```yaml
review:
  triggers:
    - opened
    - synchronize
  skip_draft: false  # 也审查 draft PR
```

### 场景 2: 开源项目

审查外部贡献者的 PR：

```yaml
review:
  triggers:
    - opened  # 只在创建时审查
  focus_areas:
    - "安全漏洞和最佳实践"
    - "代码风格一致性"
    - "文档完整性"
```

### 场景 3: 个人项目

快速获得代码反馈：

```yaml
review:
  triggers:
    - synchronize  # 每次提交都审查
  language: "zh-CN"
```

## 💡 最佳实践

1. **合理设置触发条件**：避免过于频繁的审查消耗 API 配额
2. **审查重点明确**：根据项目需求自定义 `focus_areas`
3. **结合人工审查**：AI 审查作为辅助，不应完全替代人工审查
4. **定期更新模型**：使用最新的 Claude 模型获得更好的审查质量
5. **监控成本**：关注 API 使用量和成本

## 🔗 相关资源

- [Claude API 文档](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [GitHub Webhooks 文档](https://docs.github.com/en/webhooks)
- [PyGithub 文档](https://pygithub.readthedocs.io/)

## 📞 支持

如有问题或建议，请提交 Issue。

---

**Happy Reviewing! 🚀**
