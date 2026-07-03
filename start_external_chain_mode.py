"""
模式二：外部区块链模式
需要先启动 Hardhat 或 Ganache 本地链
适合课堂演示，展示真实区块链交互

使用步骤：
    1. 先启动 Hardhat 或 Ganache（见下方说明）
    2. 部署合约到本地链
    3. 运行此脚本启动后端服务

启动 Hardhat:
    cd hardhat
    npx hardhat node

启动 Ganache GUI:
    打开 Ganache 应用，点击 Quick Start

部署合约:
    cd hardhat
    npx hardhat run scripts/deploy.js --network localhost

启动服务:
    conda activate ai_env
    python start_external_chain_mode.py
"""

import os
import subprocess
import sys

# 设置使用外部链
os.environ["USE_TESTER"] = "false"

print("=" * 60)
print("模式二：外部区块链模式")
print("=" * 60)
print("")
print("请确保已完成以下步骤：")
print("")
print("【步骤1】启动本地区块链")
print("  Hardhat: cd hardhat && npx hardhat node")
print("  Ganache: 打开 Ganache GUI 应用")
print("")
print("【步骤2】部署合约")
print("  cd hardhat")
print("  npx hardhat run scripts/deploy.js --network localhost")
print("")
print("【步骤3】确认本地链运行在 http://127.0.0.1:8545")
print("")
print("=" * 60)

# 检查本地链是否运行
try:
    import web3
    w3 = web3.Web3(web3.Web3.HTTPProvider("http://127.0.0.1:8545", request_kwargs={"timeout": 3}))
    if w3.is_connected():
        print(f"✓ 已连接到本地链 (Block #{w3.eth.block_number})")
        print(f"  可用账户: {len(w3.eth.accounts)} 个")
    else:
        print("✗ 无法连接到本地链 http://127.0.0.1:8545")
        print("  请先启动 Hardhat 或 Ganache")
        sys.exit(1)
except Exception as e:
    print(f"✗ 连接失败: {e}")
    print("  请先启动 Hardhat 或 Ganache")
    sys.exit(1)

print("")
print("启动后端服务...")
print("访问地址: http://127.0.0.1:8000")
print("=" * 60)

python_path = r"C:\Users\efzzz\miniconda3\envs\ai_env\python.exe"

subprocess.run([
    python_path, "-m", "uvicorn",
    "backend.app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000"
])