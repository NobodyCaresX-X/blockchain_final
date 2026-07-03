"""
部署合约到外部本地链
需要先启动 Hardhat 或 Ganache

使用方式：
    1. 先启动 Hardhat: cd hardhat && npx hardhat node
    2. 运行此脚本: python deploy_to_local_chain.py
"""

import json
import sys
from pathlib import Path

from web3 import Web3

# 连接到本地链
RPC_URL = "http://127.0.0.1:8545"

print("=" * 60)
print("部署合约到本地链")
print("=" * 60)

# 检查连接
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 5}))

if not w3.is_connected():
    print(f"✗ 无法连接到本地链: {RPC_URL}")
    print("请先启动 Hardhat 或 Ganache:")
    print("  Hardhat: cd hardhat && npx hardhat node")
    print("  Ganache: 打开 Ganache GUI 应用")
    sys.exit(1)

print(f"✓ 已连接到本地链")
print(f"  Chain ID: {w3.eth.chain_id}")
print(f"  当前区块: #{w3.eth.block_number}")
print(f"  可用账户: {len(w3.eth.accounts)} 个")

# 显示账户
for i, account in enumerate(w3.eth.accounts[:5]):
    balance = w3.from_wei(w3.eth.get_balance(account), 'ether')
    print(f"  [{i}] {account} ({balance} ETH)")

# 加载合约
artifact_path = Path("hardhat/artifacts/contracts/Crowdfunding.sol/Crowdfunding.json")
if not artifact_path.exists():
    print("✗ 合约编译产物不存在")
    print("请先编译合约: cd hardhat && npx hardhat compile")
    sys.exit(1)

artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
abi = artifact["abi"]
bytecode = artifact["bytecode"]

print("")
print("正在部署合约...")

# 使用第一个账户部署
deployer = w3.eth.accounts[0]
Crowdfunding = w3.eth.contract(abi=abi, bytecode=bytecode)

tx_hash = Crowdfunding.constructor().transact({"from": deployer})
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
contract_address = tx_receipt.contractAddress

print(f"✓ 合约已部署")
print(f"  地址: {contract_address}")
print(f"  部署者: {deployer}")
print(f"  Gas 使用: {tx_receipt.gasUsed}")

# 保存部署信息
deployment_dir = Path("hardhat/deployments")
deployment_dir.mkdir(parents=True, exist_ok=True)

deployment_data = {
    "chainId": w3.eth.chain_id,
    "networkName": "localhost",
    "address": contract_address,
    "deployedAt": tx_receipt.blockNumber,
    "deployer": deployer,
}

deployment_file = deployment_dir / "localhost.json"
deployment_file.write_text(json.dumps(deployment_data, indent=2), encoding="utf-8")

print(f"✓ 部署信息已保存: {deployment_file}")
print("")
print("=" * 60)
print("部署完成！现在可以启动后端服务:")
print("  python start_external_chain_mode.py")
print("=" * 60)