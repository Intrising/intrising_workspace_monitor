#!/usr/bin/env python3
"""
测试邮件发送功能
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

# 载入环境变量
load_dotenv()

def test_msmtp():
    """测试 msmtp 配置"""
    msmtp_config = os.getenv("MSMTP_CONFIG", "/home/appuser/.msmtprc")
    email_from = os.getenv("EMAIL_FROM", "devops@intrising.com.tw")

    print(f"使用配置文件: {msmtp_config}")
    print(f"发件人: {email_from}")

    # 检查配置文件是否存在
    if not os.path.exists(msmtp_config):
        print(f"错误：配置文件不存在: {msmtp_config}")
        return False

    # 构建测试邮件
    recipient = input("请输入收件人邮箱地址: ").strip()

    if not recipient:
        print("错误：收件人地址为空")
        return False

    email_content = f"""From: {email_from}
To: {recipient}
Subject: PR Monitor 测试邮件
Content-Type: text/plain; charset=UTF-8

这是一封来自 GitHub Monitor 的测试邮件。

如果你收到这封邮件，说明邮件配置成功！

测试时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
GitHub Monitor
"""

    print("\n正在发送测试邮件...")

    try:
        # 调用 msmtp 发送邮件
        process = subprocess.Popen(
            ['msmtp', '-C', msmtp_config, '-t'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate(email_content.encode('utf-8'))

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            print(f"❌ 发送失败: {error_msg}")
            return False

        print(f"✓ 邮件发送成功到 {recipient}")
        print("\n提示：")
        print("1. 检查收件箱（可能在垃圾邮件文件夹）")
        print("2. 查看日志：tail -f /var/log/github-monitor/msmtp.log")
        return True

    except FileNotFoundError:
        print("❌ 错误: msmtp 未安装")
        print("安装方法: sudo apt-get install msmtp msmtp-mta")
        return False
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("GitHub Monitor - 邮件测试工具")
    print("=" * 60)
    print()

    success = test_msmtp()

    sys.exit(0 if success else 1)
