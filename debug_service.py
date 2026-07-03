import os
os.environ['USE_TESTER'] = 'true'

from pathlib import Path
print(f"Current working directory: {os.getcwd()}")

ROOT_DIR = Path(__file__).resolve().parent
print(f"ROOT_DIR: {ROOT_DIR}")

artifact_path = ROOT_DIR / "hardhat" / "artifacts" / "contracts" / "Crowdfunding.sol" / "Crowdfunding.json"
print(f"Artifact path: {artifact_path}")
print(f"Artifact exists: {artifact_path.exists()}")

from backend.app.config import settings
print(f"\nConfig artifact_file: {settings.artifact_file}")
print(f"Config artifact_file exists: {settings.artifact_file.exists()}")

print("\n--- Testing service initialization ---")
from backend.app.service import service

print(f"\nService initialized: {service._initialized}")
print(f"Service ready: {service.ready}")
print(f"Service contract: {service.contract}")
print(f"Service contract_address: {service.contract_address}")

try:
    service._ensure_initialized()
    print(f"\nAfter ensure_initialized:")
    print(f"  Service initialized: {service._initialized}")
    print(f"  Service ready: {service.ready}")
    print(f"  Service contract: {service.contract}")
    print(f"  Service contract_address: {service.contract_address}")
    print(f"  Service accounts: {service.accounts}")
    
    result = service.bootstrap()
    print(f"\nBootstrap result:")
    print(f"  ready: {result.get('ready')}")
    print(f"  message: {result.get('message')}")
    
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
