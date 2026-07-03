"""
模式一：Python 内置测试链模式
无需启动外部区块链，使用 Python eth_tester 模拟本地链
适合快速演示和测试

启动方式：
    conda activate ai_env
    python start_tester_mode.py
"""

import os
import subprocess

# 设置使用内置测试链
os.environ["USE_TESTER"] = "true"

print("=" * 60)
print("模式一：Python 内置测试链")
print("=" * 60)
print("特点：")
print("  - 无需启动外部区块链")
print("  - 使用 Python eth_tester 模拟本地链")
print("  - 每次启动自动部署合约")
print("  - 适合快速演示和测试")
print("=" * 60)
print("启动服务...")
print("")

python_path = r"C:\Users\efzzz\miniconda3\envs\ai_env\python.exe"

# 使用 --reload 自动重载
subprocess.run([
    python_path, "-m", "uvicorn",
    "backend.app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
])