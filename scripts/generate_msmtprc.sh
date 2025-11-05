#!/bin/bash
# 从环境变量生成 msmtprc 配置文件

set -e

MSMTPRC_PATH="${MSMTP_CONFIG:-/etc/msmtprc}"

# 检查必需的环境变量
if [ -z "$SMTP_HOST" ] || [ -z "$SMTP_USER" ] || [ -z "$EMAIL_FROM" ]; then
    echo "错误：缺少必需的环境变量"
    echo "需要: SMTP_HOST, SMTP_USER, EMAIL_FROM"
    exit 1
fi

# 生成 msmtprc 配置
cat > "$MSMTPRC_PATH" <<EOF
# msmtp 配置 - 由脚本自动生成
# 生成时间: $(date)

defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /var/log/github-monitor/msmtp.log

account        default
host           ${SMTP_HOST}
port           ${SMTP_PORT:-587}
from           ${EMAIL_FROM}
user           ${SMTP_USER}
EOF

# 添加密码配置
if [ -n "$SMTP_PASSWORD" ]; then
    echo "password       ${SMTP_PASSWORD}" >> "$MSMTPRC_PATH"
elif [ -f "/run/secrets/smtp_password" ]; then
    echo 'passwordeval   "cat /run/secrets/smtp_password"' >> "$MSMTPRC_PATH"
else
    echo "警告：未找到 SMTP 密码配置"
fi

# 设置正确的权限
chmod 600 "$MSMTPRC_PATH"

echo "msmtprc 配置已生成: $MSMTPRC_PATH"

# 测试配置
if command -v msmtp &> /dev/null; then
    echo "测试 msmtp 配置..."
    if msmtp -C "$MSMTPRC_PATH" --serverinfo 2>&1 | grep -q "successfully"; then
        echo "✓ msmtp 配置正确"
    else
        echo "⚠ msmtp 配置可能有问题，请检查"
    fi
fi
