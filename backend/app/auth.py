from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    username: str
    password_hash: str
    address: str
    nickname: str
    external_balance: float = 0.0  # 钱包余额
    metamask_address: str = ""     # Metamask地址

class AuthService:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._address_to_user: dict[str, User] = {}
        self._session_tokens: dict[str, str] = {}
        self._initialized = False
        self._metamask_nonces: dict[str, dict] = {}

    def _ensure_initialized(self):
        if not self._initialized:
            from .service import service
            service._ensure_initialized()
            self._initialize_default_users()
            self._initialized = True

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _initialize_default_users(self):
        from .service import service
        accounts = service.accounts
        
        # 使用前10个账户作为内置用户，分配随机外置钱包余额
        import random
        for i, address in enumerate(accounts[:10], 1):
            username = f"user{i:02d}"
            password = "123456"
            nickname = f"用户{i:02d}"
            # 随机外置钱包余额：50-500 ETH
            external_balance = random.uniform(50, 500)
            
            self._users[username] = User(
                username=username,
                password_hash=self._hash_password(password),
                address=address,
                nickname=nickname,
                external_balance=external_balance
            )
            self._address_to_user[address.lower()] = self._users[username]

    def register(self, username: str, password: str, nickname: str = "") -> Optional[User]:
        if username in self._users:
            return None
        
        from .service import service
        service._ensure_initialized()
        
        # 创建新账户
        new_account = service.w3.eth.account.create()
        new_address = new_account.address
        
        # 随机外置钱包余额：50-500 ETH
        import random
        external_balance = random.uniform(50, 500)
        
        # 在测试链上为用户账户分配余额（从默认账户转账）
        try:
            # 使用默认账户给新账户转账100 ETH用于支付gas
            transfer_amount = service.w3.to_wei(100, "ether")
            tx_hash = service.w3.eth.send_transaction({
                "from": service.accounts[0],
                "to": new_address,
                "value": transfer_amount
            })
            service.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            print(f"转账失败: {e}")
        
        user = User(
            username=username,
            password_hash=self._hash_password(password),
            address=new_address,
            nickname=nickname if nickname else username,
            external_balance=external_balance
        )
        
        self._users[username] = user
        self._address_to_user[new_address.lower()] = user
        
        return user

    def login(self, username: str, password: str) -> Optional[str]:
        self._ensure_initialized()
        
        user = self._users.get(username)
        if not user:
            return None
        
        if user.password_hash != self._hash_password(password):
            return None
        
        token = hashlib.sha256(f"{username}{os.urandom(16)}".encode()).hexdigest()
        self._session_tokens[token] = username
        
        return token

    def validate_token(self, token: str) -> Optional[User]:
        self._ensure_initialized()
        username = self._session_tokens.get(token)
        if not username:
            return None
        return self._users.get(username)

    def logout(self, token: str):
        if token in self._session_tokens:
            del self._session_tokens[token]

    def get_user_by_address(self, address: str) -> Optional[User]:
        return self._address_to_user.get(address.lower())

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self._users.get(username)

    def list_users(self) -> list[dict]:
        return [
            {
                "username": user.username,
                "nickname": user.nickname,
                "address": user.address,
                "balance": user.external_balance
            }
            for user in self._users.values()
        ]

    def get_metamask_nonce(self, address: str) -> dict:
        """获取Metamask登录随机数"""
        self._ensure_initialized()
        address = address.lower()
        nonce = os.urandom(32).hex()
        timestamp = int(time.time())
        self._metamask_nonces[address] = {
            "nonce": nonce,
            "timestamp": timestamp
        }
        return {"nonce": nonce, "timestamp": timestamp}

    def verify_metamask_signature(self, address: str, signature: str) -> bool:
        """验证Metamask签名"""
        self._ensure_initialized()
        address = address.lower()
        
        print(f"[DEBUG] 验证签名 - 地址: {address}")
        print(f"[DEBUG] 现有nonce地址: {list(self._metamask_nonces.keys())}")
        
        if address not in self._metamask_nonces:
            print(f"[DEBUG] 地址不在nonce列表中")
            return False
        
        nonce_data = self._metamask_nonces[address]
        message = f"请签名以登录区块链众筹系统\n地址: {address}\n随机数: {nonce_data['nonce']}\n时间戳: {nonce_data['timestamp']}"
        
        print(f"[DEBUG] 原始消息: {message}")
        print(f"[DEBUG] 签名: {signature}")
        
        try:
            from web3 import Web3
            from eth_account.messages import encode_defunct
            
            w3 = Web3()
            
            # personal_sign 使用 EIP-191 格式，需要使用 encode_defunct 编码
            message_encoded = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                message_encoded,
                signature=signature
            ).lower()
            
            print(f"[DEBUG] 恢复的地址: {recovered_address}")
            print(f"[DEBUG] 期望的地址: {address}")
            
            if recovered_address == address:
                del self._metamask_nonces[address]
                print(f"[DEBUG] 签名验证成功")
                return True
        except Exception as e:
            print(f"验证签名失败: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"[DEBUG] 签名验证失败")
        return False

    def login_with_metamask(self, address: str, signature: str) -> Optional[str]:
        """使用Metamask登录"""
        self._ensure_initialized()
        address = address.lower()
        
        if not self.verify_metamask_signature(address, signature):
            return None
        
        user = self.get_user_by_metamask_address(address)
        
        # 如果用户不存在，自动创建新账户
        if not user:
            from .service import service
            
            # 使用Metamask地址作为区块链地址
            blockchain_address = address
            
            # Metamask用户的外置钱包余额从区块链查询（真实余额）
            external_balance = 0.0
            try:
                external_balance = service.get_balance(blockchain_address)
            except Exception as e:
                print(f"[DEBUG] 获取区块链余额失败: {e}")
            
            # 如果余额为0，为用户分配初始余额（测试链）
            if external_balance == 0:
                try:
                    print(f"[DEBUG] 为Metamask用户 {address} 分配初始余额")
                    # 使用测试链的第一个账户作为资金来源
                    deployer = service.w3.eth.accounts[0]
                    print(f"[DEBUG] 使用账户 {deployer} 作为转账来源")
                    
                    deployer_balance = service.w3.eth.get_balance(deployer)
                    print(f"[DEBUG] 部署者余额: {service.w3.from_wei(deployer_balance, 'ether')} ETH")
                    
                    transfer_amount = service.w3.to_wei(100, "ether")
                    tx_hash = service.w3.eth.send_transaction({
                        "from": deployer,
                        "to": blockchain_address,
                        "value": transfer_amount
                    })
                    service.w3.eth.wait_for_transaction_receipt(tx_hash)
                    external_balance = 100.0
                    print(f"[DEBUG] 转账成功，tx_hash: {tx_hash.hex()}")
                except Exception as e:
                    print(f"[DEBUG] 转账失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 生成用户名
            username = f"metamask_{address[:8]}"
            
            user = User(
                username=username,
                password_hash="",
                address=blockchain_address,
                nickname=f"Metamask用户",
                external_balance=external_balance,
                metamask_address=address
            )
            
            self._users[username] = user
            self._address_to_user[address] = user
        else:
            # 更新外置钱包余额为真实余额
            from .service import service
            try:
                user.external_balance = service.get_balance(address)
            except Exception as e:
                print(f"[DEBUG] 更新区块链余额失败: {e}")
        
        token = hashlib.sha256(f"{user.username}{os.urandom(16)}".encode()).hexdigest()
        self._session_tokens[token] = user.username
        return token

    def get_user_by_metamask_address(self, address: str) -> Optional[User]:
        """根据Metamask地址查找用户"""
        self._ensure_initialized()
        address = address.lower()
        for user in self._users.values():
            if user.metamask_address.lower() == address:
                return user
        return None

    def link_metamask_address(self, username: str, metamask_address: str) -> dict:
        """关联Metamask地址"""
        self._ensure_initialized()
        user = self._users.get(username)
        if not user:
            return {"success": False, "message": "用户不存在"}
        
        metamask_address = metamask_address.lower()
        
        existing_user = self.get_user_by_metamask_address(metamask_address)
        if existing_user and existing_user.username != username:
            return {"success": False, "message": "该Metamask地址已关联其他账户"}
        
        user.metamask_address = metamask_address
        return {"success": True, "message": "Metamask地址关联成功"}

auth_service = AuthService()
