# GitHub Webhook 测试指南

快速测试 GitHub webhook 是否正常工作的完整指南。

## 🎯 测试方法

### 方法 1：使用测试服务器（推荐）

#### 1. 启动测试服务器

```bash
python test_webhook.py
```

输出示例：
```
================================================================================
🚀 GitHub Webhook 测试服务器
================================================================================

📡 监听地址: http://0.0.0.0:8080
🔗 Webhook URL: http://your-server-ip:8080/webhook
🔐 Webhook Secret: 已设置

💡 提示:
   - 使用 Ctrl+C 停止服务器
   - 在 GitHub 仓库设置 webhook 指向上述 URL
   - 触发事件后查看此终端的输出

================================================================================
```

#### 2. 配置 GitHub Webhook

在 GitHub 仓库中：
1. 进入 `Settings` → `Webhooks` → `Add webhook`
2. 配置：
   - **Payload URL**: `http://your-server-ip:8080/webhook`
   - **Content type**: `application/json`
   - **Secret**: 填入你的 `WEBHOOK_SECRET`
   - **Which events**: 选择 `Let me select individual events` → 勾选 `Pull requests`
3. 点击 `Add webhook`

#### 3. 测试接收

**方法 A：发送测试 ping**
- 在 GitHub webhook 设置页面，点击刚创建的 webhook
- 滚动到底部，点击 `Redeliver` 按钮重新发送 ping 事件

**方法 B：创建测试 PR**
```bash
# 在你的仓库中
git checkout -b test-webhook
echo "test" >> test.txt
git add test.txt
git commit -m "test: webhook test"
git push origin test-webhook

# 在 GitHub 上创建 PR
```

#### 4. 查看输出

测试服务器终端会显示：
```
================================================================================
📨 收到 GitHub Webhook!
================================================================================
⏰ 时间: 2024-03-15 10:30:45
📦 Delivery ID: 12345678-1234-1234-1234-123456789abc
🏷️  事件类型: pull_request
🔐 签名: sha256=abc123...
✅ 签名验证通过

📋 事件详情:
--------------------------------------------------------------------------------
🔄 动作: opened
🏢 仓库: your-org/your-repo
📝 PR #123: Add new feature
👤 作者: username
🌿 分支: feature-branch → main
🔗 URL: https://github.com/your-org/your-repo/pull/123
================================================================================
✅ Webhook 处理成功
```

### 方法 2：使用 curl 模拟请求

#### 1. 启动测试服务器

```bash
python test_webhook.py
```

#### 2. 在另一个终端运行测试脚本

```bash
./test_webhook_curl.sh
```

或指定自定义 URL：
```bash
./test_webhook_curl.sh http://localhost:8080/webhook
```

输出示例：
```
==========================================
🧪 GitHub Webhook 测试工具
==========================================

目标 URL: http://localhost:8080/webhook
Secret: 已设置

📡 测试 1: Ping 事件
------------------------------------------
{"status":"success","event":"ping","delivery_id":"test-delivery-1234567890"}

📡 测试 2: Pull Request Opened 事件
------------------------------------------
{"status":"success","event":"pull_request","delivery_id":"test-delivery-1234567891"}

✅ 测试完成！
```

### 方法 3：使用 ngrok 进行本地测试

如果 GitHub 无法直接访问你的服务器，可以使用 ngrok：

#### 1. 安装 ngrok

```bash
# 从 https://ngrok.com/download 下载
# 或使用包管理器
brew install ngrok  # macOS
snap install ngrok  # Linux
```

#### 2. 启动测试服务器

```bash
python test_webhook.py
```

#### 3. 启动 ngrok

```bash
ngrok http 8080
```

输出：
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8080
```

#### 4. 在 GitHub 中使用 ngrok URL

- Payload URL: `https://abc123.ngrok.io/webhook`

### 方法 4：使用 GitHub CLI 测试

```bash
# 安装 GitHub CLI (如果还没安装)
# https://cli.github.com/

# 触发 webhook
gh api repos/your-org/your-repo/hooks/12345/tests -X POST
```

## 🔍 故障排查

### 问题 1：连接超时

**症状**：GitHub 显示 "We couldn't deliver this payload"

**原因**：
- 服务器防火墙阻止了连接
- 端口未开放
- 服务器地址错误

**解决**：
```bash
# 检查服务器是否可访问
curl http://your-server-ip:8080/health

# 检查防火墙
sudo ufw allow 8080
# 或
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload

# 检查服务是否运行
ps aux | grep test_webhook
```

### 问题 2：签名验证失败

**症状**：测试服务器显示 "❌ 签名验证失败!"

**原因**：
- WEBHOOK_SECRET 不一致
- GitHub 中的 Secret 设置错误

**解决**：
```bash
# 检查环境变量
echo $WEBHOOK_SECRET

# 确保 .env 文件中的值与 GitHub 设置一致
cat .env | grep WEBHOOK_SECRET

# 在 GitHub webhook 设置中更新 Secret
```

### 问题 3：无法接收 webhook

**症状**：GitHub 显示发送成功，但服务器没有输出

**检查清单**：
```bash
# 1. 确认服务正在运行
curl http://localhost:8080/health

# 2. 检查端口
netstat -tulpn | grep 8080

# 3. 查看服务器日志
# 如果用 Docker 运行，查看容器日志
docker logs pr-reviewer

# 4. 检查 GitHub webhook 配置
# 在 GitHub webhook 页面，点击 "Recent Deliveries" 查看详情
```

### 问题 4：502 Bad Gateway

**原因**：服务器未响应

**解决**：
```bash
# 重启测试服务器
pkill -f test_webhook.py
python test_webhook.py

# 检查是否有其他服务占用端口
lsof -i :8080
```

## 📊 验证检查清单

测试完成后，确保以下都正常：

- [ ] 测试服务器成功启动
- [ ] 能访问 `http://localhost:8080/health`
- [ ] curl 模拟请求成功
- [ ] GitHub webhook 配置正确
- [ ] GitHub 能成功发送 ping 事件
- [ ] 接收到 ping 事件并正确解析
- [ ] 签名验证通过（如果启用）
- [ ] 创建测试 PR 后能接收到 pull_request 事件
- [ ] 事件数据正确解析和显示

## 💡 高级测试

### 保存 Payload 到文件

```bash
# 启动时启用保存
SAVE_PAYLOAD=true python test_webhook.py
```

这会将每个接收到的 webhook payload 保存为 JSON 文件，方便调试。

### 测试不同的事件类型

修改 `test_webhook_curl.sh` 来测试其他事件：

```bash
# 测试 push 事件
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"ref":"refs/heads/main","commits":[...]}'

# 测试 issue 事件
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -d '{"action":"opened","issue":{...}}'
```

### 压力测试

```bash
# 发送多个请求
for i in {1..10}; do
  ./test_webhook_curl.sh
  sleep 1
done
```

## 🚀 切换到生产服务器

测试通过后，切换到实际的 PR reviewer 服务：

```bash
# 停止测试服务器
# Ctrl+C

# 启动生产服务器
docker-compose -f docker-compose.reviewer.yml up -d

# 更新 GitHub webhook URL
# http://your-server:5000/webhook (注意端口改为 5000)
```

## 📝 测试记录模板

```
测试日期: YYYY-MM-DD
测试人员:
服务器地址:
WEBHOOK_SECRET: 已设置/未设置

测试结果:
- [ ] 健康检查通过
- [ ] Ping 事件接收成功
- [ ] Pull Request 事件接收成功
- [ ] 签名验证通过
- [ ] 数据解析正确

问题记录:
-

备注:
-
```

---

**测试愉快！🎉**
