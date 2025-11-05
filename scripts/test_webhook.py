#!/usr/bin/env python3
"""
测试 GitHub Webhook 接收
简单的 Flask 服务器，用于测试 webhook 是否能正常接收
"""

import os
import sys
import hmac
import hashlib
import json
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 载入环境变量
load_dotenv()

app = Flask(__name__)

# Webhook 密钥
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

def verify_signature(payload: bytes, signature: str) -> bool:
    """验证 GitHub webhook 签名"""
    if not WEBHOOK_SECRET:
        print("⚠️  警告: WEBHOOK_SECRET 未设置，跳过签名验证")
        return True

    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "service": "Webhook Test Server",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/webhook', methods=['POST'])
@app.route('/webhook/', methods=['POST'])
def webhook():
    """接收 GitHub webhook"""
    try:
        # 获取事件类型
        event_type = request.headers.get('X-GitHub-Event', 'unknown')
        signature = request.headers.get('X-Hub-Signature-256', '')
        delivery_id = request.headers.get('X-GitHub-Delivery', 'unknown')

        print("\n" + "="*80)
        print(f"📨 收到 GitHub Webhook!")
        print("="*80)
        print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📦 Delivery ID: {delivery_id}")
        print(f"🏷️  事件类型: {event_type}")
        print(f"🔐 签名: {signature[:20]}..." if signature else "🔐 签名: (无)")

        # 验证签名
        if WEBHOOK_SECRET:
            if verify_signature(request.data, signature):
                print("✅ 签名验证通过")
            else:
                print("❌ 签名验证失败!")
                return jsonify({"error": "Invalid signature"}), 401

        # 解析 payload
        payload = request.json

        # 显示详细信息
        print("\n📋 事件详情:")
        print("-" * 80)

        if event_type == 'ping':
            zen = payload.get('zen', '')
            print(f"💬 Ping 消息: {zen}")
            print(f"🏢 仓库: {payload.get('repository', {}).get('full_name', 'N/A')}")

        elif event_type == 'pull_request':
            action = payload.get('action', 'unknown')
            pr = payload.get('pull_request', {})
            repo = payload.get('repository', {})

            print(f"🔄 动作: {action}")
            print(f"🏢 仓库: {repo.get('full_name', 'N/A')}")
            print(f"📝 PR #{pr.get('number', 'N/A')}: {pr.get('title', 'N/A')}")
            print(f"👤 作者: {pr.get('user', {}).get('login', 'N/A')}")
            print(f"🌿 分支: {pr.get('head', {}).get('ref', 'N/A')} → {pr.get('base', {}).get('ref', 'N/A')}")
            print(f"🔗 URL: {pr.get('html_url', 'N/A')}")

        elif event_type == 'push':
            ref = payload.get('ref', 'N/A')
            repo = payload.get('repository', {})
            commits = payload.get('commits', [])

            print(f"🏢 仓库: {repo.get('full_name', 'N/A')}")
            print(f"🌿 分支: {ref}")
            print(f"📦 提交数: {len(commits)}")

        else:
            print(f"📦 事件类型: {event_type}")
            print(f"📄 Payload 键: {list(payload.keys())}")

        # 保存完整 payload 到文件（可选）
        if os.getenv("SAVE_PAYLOAD", "false").lower() == "true":
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"webhook_payload_{event_type}_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Payload 已保存到: {filename}")

        print("="*80)
        print("✅ Webhook 处理成功\n")

        return jsonify({
            "status": "success",
            "event": event_type,
            "delivery_id": delivery_id
        }), 200

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """首页"""
    return """
    <html>
    <head><title>GitHub Webhook 测试服务器</title></head>
    <body>
        <h1>🎯 GitHub Webhook 测试服务器</h1>
        <p>服务器正在运行！</p>
        <ul>
            <li>Webhook 端点: <code>POST /webhook</code></li>
            <li>健康检查: <code>GET /health</code></li>
        </ul>
        <h2>📝 测试步骤:</h2>
        <ol>
            <li>在 GitHub 仓库设置中添加 webhook</li>
            <li>Payload URL: <code>http://your-server:8080/webhook</code></li>
            <li>Content type: <code>application/json</code></li>
            <li>选择触发事件（如 Pull requests）</li>
            <li>查看终端输出验证接收</li>
        </ol>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 GitHub Webhook 测试服务器")
    print("="*80)

    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "8080"))

    print(f"\n📡 监听地址: http://{host}:{port}")
    print(f"🔗 Webhook URL: http://your-server-ip:{port}/webhook")
    print(f"🔐 Webhook Secret: {'已设置' if WEBHOOK_SECRET else '未设置'}")
    print(f"\n💡 提示:")
    print(f"   - 使用 Ctrl+C 停止服务器")
    print(f"   - 在 GitHub 仓库设置 webhook 指向上述 URL")
    print(f"   - 触发事件后查看此终端的输出")
    print("\n" + "="*80 + "\n")

    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)
