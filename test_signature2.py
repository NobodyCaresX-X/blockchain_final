import os
os.environ['USE_TESTER'] = 'true'

from web3 import Web3
from eth_account.messages import encode_defunct
import json

# 使用用户提供的真实数据
address = '0x11b1add05c234a7c1b399bdf3d09b037c9bc2cf1'
signature = '0xcb801b83554fd4937038967c8c8f2b264c83dde1e7ea1ae937d10d1fdc80bea2480ec54341d6791600996bb8f5f830c6b4ef32902497e9850b83e1e9912d7d0f1b'
nonce = 'b52f0d1aeae55a504a5b7ba164537aa9c9ab029a6857d3bb3625308a949e6465'
timestamp = 1782107737

# 构造消息 - 确保与前端完全一致
message = f'请签名以登录区块链众筹系统\n地址: {address}\n随机数: {nonce}\n时间戳: {timestamp}'
print(f'Message: {repr(message)}')
print(f'Message length: {len(message)}')

w3 = Web3()

# 方法1: 使用 encode_defunct
print('\n--- Method 1: encode_defunct ---')
try:
    message_encoded = encode_defunct(text=message)
    print(f'Message encoded: {message_encoded}')
    
    recovered = w3.eth.account.recover_message(message_encoded, signature=signature)
    print(f'Recovered: {recovered}')
    print(f'Match: {recovered.lower() == address.lower()}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

# 方法2: 手动构造EIP-191消息
print('\n--- Method 2: Manual EIP-191 ---')
try:
    # personal_sign 添加的前缀: "\x19Ethereum Signed Message:\n" + len(message) + message
    prefix = f"\x19Ethereum Signed Message:\n{len(message)}"
    full_message = prefix + message
    print(f'Full message (repr): {repr(full_message)}')
    print(f'Full message length: {len(full_message)}')
    
    message_hash = w3.keccak(text=full_message)
    print(f'Message hash: {message_hash.hex()}')
    
    recovered = w3.eth.account.recoverHash(message_hash, signature=signature)
    print(f'Recovered: {recovered}')
    print(f'Match: {recovered.lower() == address.lower()}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

# 方法3: 尝试不同的签名格式
print('\n--- Method 3: Different signature formats ---')
try:
    # 移除0x前缀
    sig_no_prefix = signature[2:] if signature.startswith('0x') else signature
    
    # 转换为字节
    sig_bytes = bytes.fromhex(sig_no_prefix)
    print(f'Signature bytes length: {len(sig_bytes)}')
    
    # 检查v值
    v = sig_bytes[64]
    print(f'v value: {v}')
    
    # 如果v是0或1，转换为27或28
    if v == 0:
        sig_bytes = sig_bytes[:64] + bytes([27])
    elif v == 1:
        sig_bytes = sig_bytes[:64] + bytes([28])
    
    print(f'Adjusted v value: {sig_bytes[64]}')
    
    message_encoded = encode_defunct(text=message)
    recovered = w3.eth.account.recover_message(message_encoded, signature=sig_bytes)
    print(f'Recovered: {recovered}')
    print(f'Match: {recovered.lower() == address.lower()}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()