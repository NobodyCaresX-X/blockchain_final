import os
import sys
import time

os.environ['USE_TESTER'] = 'true'

print("=" * 60)
print("区块链众筹系统 - 服务启动器")
print("=" * 60)
print(f"Python: {sys.executable}")
print(f"工作目录: {os.getcwd()}")
print(f"USE_TESTER: {os.environ.get('USE_TESTER')}")
print()

import uvicorn
from backend.app.main import app

print("应用已加载，启动服务器...")
print()

uvicorn.run(
    "backend.app.main:app",
    host="127.0.0.1",
    port=8000,
    log_level="info"
)
