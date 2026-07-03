"""
快速测试服务启动
"""
import os
os.environ["USE_TESTER"] = "true"

print("=" * 60)
print("区块链众筹系统启动中...")
print("=" * 60)

# 导入服务
from backend.app.main import app
from backend.app.service import service

print(f"USE_TESTER = {os.getenv('USE_TESTER')}")
print(f"Service ready = {service.ready}")
print(f"Contract address = {service.contract_address}")

print("=" * 60)
print("启动 Uvicorn 服务...")
print("请访问: http://127.0.0.1:8000")
print("=" * 60)

# 这里不启动服务，只是测试初始化
print("\n初始化测试完成！")
