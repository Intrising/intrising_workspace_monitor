# msmtp 邮件通知配置指南

PR Monitor 使用 msmtp 发送邮件通知。这是一个轻量级的 SMTP 客户端，非常适合在 Docker 容器中使用。

## 📋 功能特性

- ✅ **轻量级**：比传统 SMTP 库更轻量
- ✅ **灵活配置**：支持多个 SMTP 账户
- ✅ **安全**：支持 TLS/SSL 加密
- ✅ **Docker 友好**：容器化部署简单

## 🚀 快速开始

### 1. 配置 msmtp

#### 方法 1：使用配置文件（推荐）

创建 `msmtprc` 文件：

```bash
# 复制示例配置
cp msmtprc.example msmtprc

# 编辑配置
vim msmtprc
```

基本配置：

```conf
# 默认设置
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /var/log/github-monitor/msmtp.log

# Gmail 配置
account        gmail
host           smtp.gmail.com
port           587
from           your-email@gmail.com
user           your-email@gmail.com
password       your-app-password

# 设置默认账户
account default : gmail
```

**Gmail 用户注意**：
1. 需要启用"两步验证"
2. 生成"应用专用密码"：https://myaccount.google.com/apppasswords
3. 使用应用密码，而非 Gmail 密码

#### 方法 2：使用环境变量

在 `docker-compose.yml` 中使用环境变量替换：

```yaml
services:
  github-monitor:
    environment:
      - SMTP_HOST=smtp.gmail.com
      - SMTP_PORT=587
      - SMTP_USER=your-email@gmail.com
      - SMTP_PASSWORD=your-app-password
      - EMAIL_FROM=github-monitor@example.com
```

然后使用脚本在启动时生成配置文件。

### 2. 更新 .env 文件

```bash
# Email 配置
EMAIL_FROM=github-monitor@example.com
MSMTP_CONFIG=/etc/msmtprc

# SMTP 服务器配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. 启用邮件通知

在 `config.yaml` 中：

```yaml
notifications:
  email:
    enabled: true
    recipients:
      - "team@example.com"
      - "dev@example.com"
```

### 4. 部署配置

#### Docker Compose 配置

在 `docker-compose.yml` 中挂载 msmtp 配置：

```yaml
services:
  github-monitor:
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./msmtprc:/etc/msmtprc:ro  # 挂载 msmtp 配置
      - github-monitor-logs:/var/log/github-monitor
```

### 5. 测试邮件发送

```bash
# 进入容器
docker exec -it github-monitor /bin/bash

# 测试 msmtp
echo "Test email from PR Monitor" | msmtp -C /etc/msmtprc recipient@example.com

# 查看日志
tail -f /var/log/github-monitor/msmtp.log
```

## 📧 常见 SMTP 服务器配置

### Gmail

```conf
account        gmail
host           smtp.gmail.com
port           587
from           your-email@gmail.com
user           your-email@gmail.com
password       your-app-password
```

### Outlook/Office 365

```conf
account        outlook
host           smtp.office365.com
port           587
from           your-email@outlook.com
user           your-email@outlook.com
password       your-password
```

### Yahoo Mail

```conf
account        yahoo
host           smtp.mail.yahoo.com
port           587
from           your-email@yahoo.com
user           your-email@yahoo.com
password       your-app-password
```

### 自定义 SMTP 服务器

```conf
account        custom
host           smtp.your-domain.com
port           587  # 或 465 (SSL)
from           noreply@your-domain.com
user           smtp-user
password       smtp-password
```

### 使用 SSL (端口 465)

```conf
account        ssl-smtp
host           smtp.example.com
port           465
tls            on
tls_starttls   off  # 465 端口不需要 STARTTLS
from           noreply@example.com
user           smtp-user
password       smtp-password
```

## 🔒 安全最佳实践

### 1. 使用 Docker Secrets（生产环境推荐）

#### 创建 secret

```bash
# 创建密码 secret
echo "your-smtp-password" | docker secret create smtp_password -

# 创建完整的 msmtprc secret
docker secret create msmtprc msmtprc
```

#### 在 docker-compose.yml 中使用

```yaml
version: '3.8'

services:
  github-monitor:
    secrets:
      - msmtprc
      - smtp_password
    environment:
      - MSMTP_CONFIG=/run/secrets/msmtprc

secrets:
  msmtprc:
    file: ./msmtprc
  smtp_password:
    external: true
```

#### 在 msmtprc 中使用 passwordeval

```conf
account        default
host           smtp.gmail.com
port           587
from           your-email@gmail.com
user           your-email@gmail.com
# 从 Docker secret 读取密码
passwordeval   "cat /run/secrets/smtp_password"
```

### 2. 文件权限保护

```bash
# msmtprc 文件应该只有所有者可读
chmod 600 msmtprc

# 在 Dockerfile 中
RUN chmod 600 /etc/msmtprc && \
    chown prmonitor:prmonitor /etc/msmtprc
```

### 3. 不要提交敏感信息到 Git

```bash
# 添加到 .gitignore
echo "msmtprc" >> .gitignore
echo ".env" >> .gitignore
```

## 🛠️ 故障排查

### 问题 1：msmtp: account default not found

**原因**：配置文件中没有定义默认账户

**解决**：

```conf
# 添加这一行到 msmtprc
account default : gmail
```

### 问题 2：msmtp: authentication failed

**原因**：用户名或密码错误

**解决**：
1. 检查 SMTP 用户名和密码
2. Gmail 用户确保使用应用专用密码
3. 检查是否启用了两步验证

### 问题 3：msmtp: TLS certificate verification failed

**原因**：SSL/TLS 证书验证失败

**解决**：

```conf
# 方法 1：指定正确的证书文件
tls_trust_file /etc/ssl/certs/ca-certificates.crt

# 方法 2：跳过证书验证（不推荐）
tls_certcheck  off
```

### 问题 4：msmtp: cannot connect to smtp.gmail.com, port 587

**原因**：网络连接问题或端口被阻止

**解决**：
1. 检查防火墙设置
2. 尝试使用端口 465（SSL）
3. 检查 DNS 解析

```bash
# 测试连接
telnet smtp.gmail.com 587

# 或使用 curl
curl -v smtp://smtp.gmail.com:587
```

### 问题 5：找不到 msmtp 命令

**原因**：msmtp 未安装

**解决**：

```bash
# Debian/Ubuntu
apt-get install msmtp msmtp-mta

# Alpine
apk add msmtp

# 在 Dockerfile 中已包含
```

### 调试模式

启用详细日志：

```bash
# 使用 -d 参数查看详细信息
echo "Test" | msmtp -C /etc/msmtprc -d recipient@example.com

# 查看日志
tail -f /var/log/github-monitor/msmtp.log
```

## 📝 高级配置

### 使用多个 SMTP 账户

```conf
# Gmail 账户
account        gmail
host           smtp.gmail.com
port           587
from           alerts@gmail.com
user           alerts@gmail.com
password       gmail-password

# 企业邮箱账户
account        work
host           smtp.company.com
port           587
from           github-monitor@company.com
user           smtp-user
password       work-password

# 根据发件人自动选择账户
account default : gmail
```

在代码中指定账户：

```python
# 修改 _send_email_via_msmtp 方法
process = subprocess.Popen(
    ['msmtp', '-C', self.msmtp_config, '-a', 'work', '-t'],
    # -a work 指定使用 work 账户
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
```

### 邮件模板自定义

修改 `pr_monitor.py` 中的邮件模板：

```python
def send_email_notification(self, pr, issues: List[Dict]):
    # 自定义 HTML 邮件
    body = f"""
    <html>
    <body>
        <h2>PR Alert</h2>
        <p><strong>PR #{pr.number}</strong>: {pr.title}</p>
        <ul>
            {''.join([f'<li>{issue["message"]}</li>' for issue in issues])}
        </ul>
        <a href="{pr.html_url}">查看 PR</a>
    </body>
    </html>
    """

    # 修改 Content-Type
    email_content = f"""From: {self.email_from}
To: {to}
Subject: {subject}
Content-Type: text/html; charset=UTF-8

{body}
"""
```

### 邮件发送频率限制

防止邮件轰炸：

```python
import time
from collections import defaultdict

class PRMonitor:
    def __init__(self):
        # ...
        self.email_sent_time = defaultdict(float)
        self.email_cooldown = 3600  # 1小时冷却

    def send_email_notification(self, pr, issues: List[Dict]):
        # 检查冷却时间
        pr_key = f"{pr.base.repo.full_name}#{pr.number}"
        now = time.time()

        if now - self.email_sent_time[pr_key] < self.email_cooldown:
            self.logger.info(f"PR {pr_key} 邮件冷却中，跳过")
            return

        # 发送邮件
        # ...

        # 记录发送时间
        self.email_sent_time[pr_key] = now
```

## 📊 监控邮件发送

### 查看 msmtp 日志

```bash
# 实时查看
tail -f /var/log/github-monitor/msmtp.log

# 查看最近的错误
grep -i error /var/log/github-monitor/msmtp.log

# 统计发送数量
grep "mail sent successfully" /var/log/github-monitor/msmtp.log | wc -l
```

### 日志轮转

添加 logrotate 配置：

```conf
# /etc/logrotate.d/msmtp
/var/log/github-monitor/msmtp.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

## 🔗 相关资源

- [msmtp 官方文档](https://marlam.de/msmtp/)
- [Gmail 应用专用密码](https://myaccount.google.com/apppasswords)
- [Outlook SMTP 设置](https://support.microsoft.com/en-us/office/pop-imap-and-smtp-settings-8361e398-8af4-4e97-b147-6c6c4ac95353)

---

**配置完成后，记得测试邮件发送功能！**
