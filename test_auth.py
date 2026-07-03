import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置测试环境
os.environ['USE_TESTER'] = 'true'

try:
    print("Importing auth module...")
    from backend.app.auth import auth_service
    print("OK: auth_service imported successfully")
    
    print("Testing login...")
    token = auth_service.login("user01", "123456")
    if token:
        print(f"OK: Login successful, token: {token[:20]}...")
        
        user = auth_service.get_user_by_username("user01")
        print(f"OK: User info - {user.username}, internal: {user.internal_balance}, external: {user.external_balance:.2f}")
        
        print("Testing topup...")
        result = auth_service.topup("user01", 10)
        print(f"OK: Topup result - {result['message']}")
        
        print("Testing withdraw...")
        result = auth_service.withdraw("user01", 5)
        print(f"OK: Withdraw result - {result['message']}")
        
        print("\nAll tests passed!")
    else:
        print("FAIL: Login failed")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()