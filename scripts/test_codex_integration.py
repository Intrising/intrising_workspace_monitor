#!/usr/bin/env python3
"""
测试 Codex CLI 集成
"""

import os
import sys
import subprocess

def test_codex_cli():
    """测试 Codex CLI 是否可用"""
    print("=" * 60)
    print("测试 1: 检查 Codex CLI 是否安装")
    print("=" * 60)

    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"✓ Codex CLI 已安装: {result.stdout.strip()}")
        else:
            print(f"✗ Codex CLI 检查失败")
            print(f"stderr: {result.stderr}")
            return False

    except FileNotFoundError:
        print("✗ 未找到 codex 命令，请先安装 Codex CLI")
        print("  安装命令: npm install -g @openai/codex")
        return False
    except Exception as e:
        print(f"✗ 检查 Codex CLI 时出错: {e}")
        return False

    print("\n" + "=" * 60)
    print("测试 2: 检查 Codex 认证状态")
    print("=" * 60)

    try:
        result = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"✓ Codex 认证状态: {result.stdout.strip()}")
        else:
            print(f"✗ Codex 未登录")
            print("  请运行: codex login")
            return False

    except Exception as e:
        print(f"✗ 检查认证状态时出错: {e}")
        return False

    print("\n" + "=" * 60)
    print("测试 3: 测试 Codex exec 命令")
    print("=" * 60)

    test_prompt = "请用一句话回答：Python 是什么？"

    try:
        result = subprocess.run(
            ["codex", "exec", test_prompt],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"✓ Codex exec 测试成功")
            print(f"\n响应:\n{result.stdout}")
            return True
        else:
            print(f"✗ Codex exec 测试失败")
            print(f"stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ Codex exec 执行超时")
        return False
    except Exception as e:
        print(f"✗ 测试 Codex exec 时出错: {e}")
        return False


def test_pr_reviewer_import():
    """测试 PR Reviewer 是否可以导入"""
    print("\n" + "=" * 60)
    print("测试 4: 测试 PR Reviewer 导入")
    print("=" * 60)

    try:
        from pr_reviewer import PRReviewer
        print("✓ PR Reviewer 模块导入成功")
        return True
    except Exception as e:
        print(f"✗ PR Reviewer 模块导入失败: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Codex 集成测试")
    print("=" * 60 + "\n")

    success = True

    # 测试 Codex CLI
    if not test_codex_cli():
        success = False

    # 测试 PR Reviewer 导入
    if not test_pr_reviewer_import():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✓ 所有测试通过！")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ 部分测试失败")
        print("=" * 60)
        sys.exit(1)
