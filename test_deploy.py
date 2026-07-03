import os
import json
from pathlib import Path

os.environ['USE_TESTER'] = 'true'

from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

artifact_path = Path('hardhat/artifacts/contracts/Crowdfunding.sol/Crowdfunding.json')
print(f"Artifact path: {artifact_path}")
print(f"Artifact exists: {artifact_path.exists()}")

with open(artifact_path, 'r', encoding='utf-8') as f:
    artifact = json.load(f)

print(f"Artifact keys: {list(artifact.keys())}")
print(f"ABI length: {len(artifact.get('abi', []))}")
bytecode = artifact.get('bytecode', '')
print(f"Bytecode length: {len(bytecode)}")
print(f"Bytecode starts with 0x: {bytecode.startswith('0x')}")

try:
    provider = EthereumTesterProvider()
    w3 = Web3(provider)
    print(f"\nConnected: {w3.is_connected()}")
    print(f"Chain ID: {w3.eth.chain_id}")
    print(f"Accounts: {w3.eth.accounts}")
    
    accounts = w3.eth.accounts
    deployer = accounts[0]
    print(f"\nDeployer balance: {w3.eth.get_balance(deployer)} wei")
    
    if bytecode:
        Crowdfunding = w3.eth.contract(abi=artifact['abi'], bytecode=bytecode)
        print("\nDeploying contract...")
        tx_hash = Crowdfunding.constructor().transact({"from": deployer})
        print(f"TX hash: {tx_hash.hex()}")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.contractAddress
        print(f"Contract deployed to: {contract_address}")
    else:
        print("\nERROR: No bytecode found in artifact!")
        
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
