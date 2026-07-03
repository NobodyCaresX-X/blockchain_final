from dataclasses import dataclass
from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    rpc_url: str = "http://127.0.0.1:8545"
    deployment_file: Path = ROOT_DIR / "hardhat" / "deployments" / "localhost.json"
    artifact_file: Path = ROOT_DIR / "hardhat" / "artifacts" / "contracts" / "Crowdfunding.sol" / "Crowdfunding.json"
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
