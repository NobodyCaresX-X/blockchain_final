import os
os.environ['USE_TESTER'] = 'true'

from backend.app.auth import auth_service
from web3 import Web3

# 测试地址和签名
address = '0x11b1add05c234a7c1b399bdf3d09b037c9bc2cf1'
signature = '0x642dba7da2489eb7d5522489638fb3197f9257e50e768ae90df2be0152b5ae9f7fd2f087b1243d2707ab7412662d54adbb3a54550545feb23ec691f5a15bf9421c'

# 获取nonce
nonce = auth_service.get_metamask_nonce(address)
print(f'Nonce: {nonce}')

# 构造消息
message = f'请签名以登录区块链众筹系统\n地址: {address}\n随机数: {nonce["nonce"]}\n时间戳: {nonce["timestamp"]}'
print(f'Message: {message}')

# 验证签名
result = auth_service.verify_metamask_signature(address, signature)
print(f'Verification result: {result}')

# 测试Web3签名恢复
w3 = Web3()
from eth_account.messages import encode_defunct
try:
    message_encoded = encode_defunct(text=message)
    recovered = w3.eth.account.recover_message(
        message_encoded,
        signature=signature
    )
    print(f'Recovered address: {recovered}')
    print(f'Expected address: {address}')
    print(f'Match: {recovered.lower() == address.lower()}')
except Exception as e:
    print(f'Recovery error: {e}')
    import traceback
    traceback.print_exc()