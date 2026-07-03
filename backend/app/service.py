from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from .config import settings

load_dotenv()

# 全局测试链实例（用于 Python 内置测试链模式）
_tester_provider = None


def _get_web3_provider():
    """获取 Web3 提供者，使用 HTTP RPC 连接 Hardhat"""
    print(f"[DEBUG] Using HTTPProvider: {settings.rpc_url}")
    return Web3.HTTPProvider(settings.rpc_url)


def _to_int(value: Any) -> int:
    if hasattr(value, "item"):
        return int(value.item())
    return int(value)


def _wei_to_eth(value: int) -> float:
    return float(Web3.from_wei(value, "ether"))


def _iso_from_timestamp(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()


@dataclass
class ProjectSnapshot:
    id: int
    creator: str
    name: str
    description: str
    goalWei: int
    goalEth: float
    deadline: int
    deadlineIso: str
    pledgedWei: int
    pledgedEth: float
    balanceWei: int
    balanceEth: float
    totalWithdrawnWei: int
    totalWithdrawnEth: float
    totalRefundedWei: int
    totalRefundedEth: float
    status: str
    ended: bool
    creatorWithdrawn: bool
    donorCount: int
    hasStages: bool
    hasMonthlySupport: bool
    stageCount: int
    rewardCount: int
    timeLeftSeconds: int
    donors: list[dict[str, Any]] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)
    rewards: list[dict[str, Any]] = field(default_factory=list)


class CrowdfundingService:
    def __init__(self) -> None:
        self.w3 = None
        self.ready = False
        self.contract_address = None
        self.contract = None
        self.chain_id = None
        self.accounts: list[str] = []
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """延迟初始化，确保在环境变量设置后再初始化"""
        if self._initialized:
            return
        
        self.w3 = Web3(_get_web3_provider())
        self._load_contract()
        self._initialized = True

    def _load_contract(self) -> None:
        use_tester = False
        
        if not settings.artifact_file.exists():
            return

        artifact = json.loads(settings.artifact_file.read_text(encoding="utf-8"))
        
        if use_tester:
            # 在测试模式下，每次都重新部署合约
            self._deploy_contract(artifact)
        else:
            # 在外部链模式下，使用已有的部署文件
            if not settings.deployment_file.exists():
                return
            deployment = json.loads(settings.deployment_file.read_text(encoding="utf-8"))
            self.contract_address = Web3.to_checksum_address(deployment["address"])
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=artifact["abi"])
            self.chain_id = deployment.get("chainId")
            self.accounts = [Web3.to_checksum_address(account) for account in self.w3.eth.accounts]
            
            self._sync_chain_time()
            
            self.ready = True

    def _sync_chain_time(self) -> None:
        """同步链上时间与系统时间，确保时间一致"""
        chain_time = self.w3.eth.get_block('latest').timestamp
        system_time = int(datetime.now(tz=timezone.utc).timestamp())
        time_diff = system_time - chain_time
        
        if time_diff > 1:
            self.w3.provider.make_request("evm_increaseTime", [time_diff])
            self.w3.provider.make_request("evm_mine", [])
            new_chain_time = self.w3.eth.get_block('latest').timestamp
            print(f"[TIME_SYNC] 链上时间已同步: 链上{chain_time} -> 现在{new_chain_time} (目标{system_time})")
        elif time_diff < -300:
            print(f"[TIME_SYNC] 链上时间比系统时间快{abs(time_diff)}秒，无法向后调整")

    def _deploy_contract(self, artifact: dict) -> None:
        """在测试链上部署合约"""
        print("正在部署合约到测试链...")
        accounts = self.w3.eth.accounts
        deployer = accounts[0]
        
        bytecode = artifact.get("bytecode", "")
        if not bytecode:
            # 从 Hardhat artifacts 获取 bytecode
            bytecode = artifact.get("bytecode", "")
        
        Crowdfunding = self.w3.eth.contract(abi=artifact["abi"], bytecode=bytecode)
        tx_hash = Crowdfunding.constructor().transact({"from": deployer})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.contract_address = tx_receipt.contractAddress
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=artifact["abi"])
        self.chain_id = self.w3.eth.chain_id
        self.accounts = [Web3.to_checksum_address(account) for account in accounts]
        self.ready = True
        print(f"合约已部署到: {self.contract_address}")

    def ensure_ready(self) -> None:
        if not self.ready or self.contract is None:
            raise RuntimeError("合约尚未部署，先运行 Hardhat 部署脚本")

    def _status_label(self, status_value: int) -> str:
        return {0: "Active", 1: "Successful", 2: "Failed"}.get(int(status_value), f"Unknown({status_value})")

    def _format_project(self, project_id: int) -> ProjectSnapshot:
        self._ensure_initialized()
        self.ensure_ready()
        data = self.contract.functions.getProject(project_id).call()
        donors = self.contract.functions.getDonors(project_id).call()
        
        # 获取阶段点列表
        stages = []
        stage_count = _to_int(data[16])  # stageCount在返回数据的第16位
        for index in range(stage_count):
            stage = self.contract.functions.getStage(project_id, index).call()
            stages.append(
                {
                    "index": index,
                    "description": stage[0],
                    "completionThresholdBps": _to_int(stage[1]),
                    "completionThresholdPercent": _to_int(stage[1]) / 100,  # 转换为百分比
                    "releaseBps": _to_int(stage[2]),
                    "releasePercent": _to_int(stage[2]) / 100,
                    "completed": bool(stage[3]),
                    "released": bool(stage[4]),
                }
            )
        
        # 获取里程碑（奖励）列表
        rewards = []
        reward_count = _to_int(data[17])  # rewardCount在返回数据的第17位
        for index in range(reward_count):
            reward = self.contract.functions.getReward(project_id, index).call()
            rewards.append(
                {
                    "index": index,
                    "fundingThresholdWei": _to_int(reward[0]),
                    "fundingThresholdEth": _wei_to_eth(_to_int(reward[0])),
                    "promise": reward[1],
                    "expectedMonth": _to_int(reward[2]),
                    "backersCount": _to_int(reward[3]),
                }
            )

        donor_rows = []
        for donor in donors:
            donation = self.contract.functions.getDonation(project_id, donor).call()
            is_monthly = bool(self.contract.functions.isMonthlySupporter(project_id, donor).call())
            donor_rows.append(
                {
                    "address": Web3.to_checksum_address(donor),
                    "donationWei": _to_int(donation),
                    "donationEth": _wei_to_eth(_to_int(donation)),
                    "earlySupporter": bool(self.contract.functions.isEarlySupporter(project_id, donor).call()),
                    "monthlySupporter": is_monthly,
                }
            )

        deadline = _to_int(data[5])
        now = int(datetime.now(tz=timezone.utc).timestamp())

        return ProjectSnapshot(
            id=_to_int(data[0]),
            creator=Web3.to_checksum_address(data[1]),
            name=data[2],
            description=data[3],
            goalWei=_to_int(data[4]),
            goalEth=_wei_to_eth(_to_int(data[4])),
            deadline=deadline,
            deadlineIso=_iso_from_timestamp(deadline),
            pledgedWei=_to_int(data[6]),
            pledgedEth=_wei_to_eth(_to_int(data[6])),
            balanceWei=_to_int(data[7]),
            balanceEth=_wei_to_eth(_to_int(data[7])),
            totalWithdrawnWei=_to_int(data[8]),
            totalWithdrawnEth=_wei_to_eth(_to_int(data[8])),
            totalRefundedWei=_to_int(data[9]),
            totalRefundedEth=_wei_to_eth(_to_int(data[9])),
            status=self._status_label(_to_int(data[10])),
            ended=bool(data[11]),
            creatorWithdrawn=bool(data[12]),
            donorCount=_to_int(data[13]),
            hasStages=bool(data[14]),
            hasMonthlySupport=bool(data[15]),
            stageCount=_to_int(data[16]),
            rewardCount=_to_int(data[17]),
            timeLeftSeconds=max(0, deadline - now),
            donors=donor_rows,
            stages=stages,
            rewards=rewards,
        )

    def list_projects(self) -> list[ProjectSnapshot]:
        self._ensure_initialized()
        self.ensure_ready()
        
        project_ids = self.contract.functions.getProjectIds().call()
        projects = []
        
        has_expired = False
        for project_id in project_ids:
            pid = _to_int(project_id)
            project = self._format_project(pid)
            if project.status == "Active" and project.timeLeftSeconds <= 0:
                has_expired = True
            projects.append(project)
        
        if has_expired:
            try:
                chain_time = self.w3.eth.get_block('latest').timestamp
                system_time = int(datetime.now(tz=timezone.utc).timestamp())
                if system_time > chain_time:
                    self.w3.provider.make_request("evm_increaseTime", [system_time - chain_time])
                    self.w3.provider.make_request("evm_mine", [])
                self._transact(self.contract.functions.checkAndFinishExpired(), self.accounts[0])
            except Exception as e:
                print(f"自动处理到期项目失败: {e}")
        
        updated_projects = []
        for project_id in project_ids:
            pid = _to_int(project_id)
            project = self._format_project(pid)
            updated_projects.append(project)
        
        return updated_projects

    def get_project(self, project_id: int) -> ProjectSnapshot:
        self._ensure_initialized()
        return self._format_project(project_id)

    def get_balance(self, address: str) -> float:
        self._ensure_initialized()
        balance_wei = self.w3.eth.get_balance(address)
        return _wei_to_eth(balance_wei)

    def bootstrap(self) -> dict[str, Any]:
        self._ensure_initialized()
        if not self.ready:
            return {
                "ready": False,
                "rpcUrl": settings.rpc_url,
                "accounts": [],
                "projects": [],
                "contractAddress": None,
                "chainId": None,
                "message": "请先启动本地链并执行 Hardhat 部署脚本",
            }

        use_tester = False
        rpc_display = settings.rpc_url

        return {
            "ready": True,
            "rpcUrl": rpc_display,
            "accounts": self.accounts,
            "projects": self.list_projects(),
            "contractAddress": self.contract_address,
            "chainId": self.chain_id,
        }

    def _transact(self, function_call: Any, sender: str, value_wei: int = 0) -> str:
        self._ensure_initialized()
        self.ensure_ready()
        self._sync_chain_time()
        sender = Web3.to_checksum_address(sender)
        tx_options: dict[str, Any] = {"from": sender}
        if value_wei > 0:
            tx_options["value"] = int(value_wei)
        tx_hash = function_call.transact(tx_options)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        
        # 阶段点参数
        has_stages = payload.get("hasStages", False)
        stage_descriptions = payload.get("stageDescriptions", [])
        stage_thresholds = payload.get("stageThresholdsBps", [])
        stage_release_bps = payload.get("stageReleaseBps", [])
        
        # 月度支持参数
        has_monthly_support = payload.get("hasMonthlySupport", False)
        
        # 里程碑（奖励）参数
        reward_thresholds = payload.get("rewardThresholds", [])
        reward_promises = payload.get("rewardPromises", [])
        reward_months = payload.get("rewardMonths", [])
        
        deadline = int(payload["deadline"])
        
        # 使用用户自己的地址创建项目
        tx_hash = self._transact(
            self.contract.functions.createProject(
                payload["name"],
                payload["description"],
                Web3.to_wei(payload["goalEth"], "ether"),
                deadline,
                has_stages,
                stage_descriptions,
                stage_thresholds,
                stage_release_bps,
                has_monthly_support,
                reward_thresholds,
                reward_promises,
                reward_months,
            ),
            payload["from"],
        )
        return {"txHash": tx_hash}

    def donate(self, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(
            self.contract.functions.donate(project_id),
            payload["from"],
            Web3.to_wei(payload["amountEth"], "ether"),
        )
        return {"txHash": tx_hash}

    def check_and_finish_expired(self) -> dict[str, Any]:
        """自动检查并结束所有到期的项目"""
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(self.contract.functions.checkAndFinishExpired(), self.accounts[0])
        return {"txHash": tx_hash}

    def finish_project(self, project_id: int, sender: str) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(self.contract.functions.finishProject(project_id), sender)
        return {"txHash": tx_hash}

    def creator_withdraw(self, project_id: int, sender: str) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(self.contract.functions.creatorWithdraw(project_id), sender)
        return {"txHash": tx_hash}

    def refund(self, project_id: int, sender: str) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(self.contract.functions.refund(project_id), sender)
        return {"txHash": tx_hash}

    def complete_milestone(self, project_id: int, index: int, sender: str) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(self.contract.functions.completeStage(project_id, index), sender)
        return {"txHash": tx_hash}

    def release_milestone(self, project_id: int, index: int, sender: str) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(self.contract.functions.releaseStageFunds(project_id, index), sender)
        return {"txHash": tx_hash}

    def start_monthly_support(self, project_id: int, monthly_amount_eth: float, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(
            self.contract.functions.startMonthlySupport(project_id),
            payload["from"],
            Web3.to_wei(monthly_amount_eth, "ether"),
        )
        return {"txHash": tx_hash}

    def stop_monthly_support(self, project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        tx_hash = self._transact(self.contract.functions.stopMonthlySupport(project_id), payload["from"])
        return {"txHash": tx_hash}

    def get_monthly_support(self, project_id: int, donor: str) -> dict[str, Any]:
        self._ensure_initialized()
        self.ensure_ready()
        result = self.contract.functions.getMonthlySupport(project_id, Web3.to_checksum_address(donor)).call()
        return {
            "monthlyAmountWei": _to_int(result[0]),
            "monthlyAmountEth": _wei_to_eth(_to_int(result[0])),
            "nextBillingTime": _to_int(result[1]),
            "nextBillingTimeIso": _iso_from_timestamp(_to_int(result[1])),
            "active": bool(result[2]),
        }

    def get_user_transactions(self, user_address: str) -> list[dict[str, Any]]:
        self._ensure_initialized()
        self.ensure_ready()
        
        user_addr = Web3.to_checksum_address(user_address)
        transactions = []
        
        events = [
            ("DonationReceived", "donation"),
            ("DonationRefunded", "refund"),
            ("CreatorWithdrawal", "withdrawal"),
            ("StageReleased", "stage_release"),
        ]
        
        for event_name, tx_type in events:
            try:
                event_filter = self.contract.events[event_name].create_filter(
                    fromBlock=0,
                    argument_filters={
                        "donor": user_addr if tx_type in ["donation", "refund"] else None,
                        "creator": user_addr if tx_type in ["withdrawal"] else None,
                    }
                )
                logs = event_filter.get_all_entries()
                for log in logs:
                    args = log["args"]
                    project_id = _to_int(args.get("projectId"))
                    amount = _wei_to_eth(_to_int(args.get("amount", 0)))
                    
                    transactions.append({
                        "type": tx_type,
                        "typeLabel": {
                            "donation": "捐赠",
                            "refund": "退款",
                            "withdrawal": "提款",
                            "stage_release": "阶段点释放",
                        }[tx_type],
                        "projectId": project_id,
                        "amount": amount,
                        "hash": log["transactionHash"].hex(),
                        "timestamp": _iso_from_timestamp(self.w3.eth.get_block(log["blockNumber"]).timestamp),
                    })
            except Exception as e:
                print(f"获取 {event_name} 事件失败: {e}")
        
        transactions.sort(key=lambda t: t["timestamp"], reverse=True)
        return transactions


service = CrowdfundingService()
