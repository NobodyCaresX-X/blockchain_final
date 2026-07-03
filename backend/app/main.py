"""
区块链众筹系统 - FastAPI 应用
"""
import os
import sys
from pathlib import Path

# 强制设置环境变量
os.environ["USE_TESTER"] = "false"
os.environ["RPC_URL"] = "http://127.0.0.1:8545"

# 调试：打印路径信息
print(f"Python: {sys.executable}")
print(f"当前工作目录: {os.getcwd()}")
print(f"USE_TESTER: {os.getenv('USE_TESTER', 'not set')}")

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

# 项目路径
# __file__ = 项目根目录/backend/app/main.py
# PROJECT_ROOT = 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "backend" / "templates"
STATIC_DIR = PROJECT_ROOT / "backend" / "static"

print(f"模板目录: {TEMPLATES_DIR}")
print(f"模板目录存在: {TEMPLATES_DIR.exists()}")
print(f"静态目录: {STATIC_DIR}")
print(f"静态目录存在: {STATIC_DIR.exists()}")

app = FastAPI(title="Blockchain Crowdfunding")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 模板
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 静态文件
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    print("静态文件已挂载")

# 导入服务（延迟初始化）
from .service import service
from .auth import auth_service
from .config import settings

# ==================== 页面路由 ====================

@app.get("/")
async def index():
    print("路由: /")
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/projects")
async def projects():
    print("路由: /projects")
    return templates.TemplateResponse("projects.html", {"request": {}})

@app.get("/create")
async def create():
    print("路由: /create")
    return templates.TemplateResponse("create.html", {"request": {}})

@app.get("/my")
async def my_page():
    print("路由: /my")
    return templates.TemplateResponse("my.html", {"request": {}})

@app.get("/login")
async def login_page():
    print("路由: /login")
    return templates.TemplateResponse("login.html", {"request": {}})

@app.get("/register")
async def register_page():
    print("路由: /register")
    return templates.TemplateResponse("register.html", {"request": {}})

# ==================== API 路由 ====================

@app.get("/api/bootstrap")
async def bootstrap():
    print("API: /api/bootstrap")
    try:
        result = service.bootstrap()
        return result
    except Exception as e:
        print(f"API 错误: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/projects")
async def list_projects():
    try:
        return service.list_projects()
    except Exception as e:
        print(f"API 错误: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/api/projects/{project_id}")
async def get_project(project_id: int):
    try:
        return service.get_project(project_id).__dict__
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/api/projects/check-finished")
async def check_and_finish_expired():
    """自动检查并结束所有到期的项目"""
    try:
        return service.check_and_finish_expired()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/api/sync-time")
async def sync_chain_time():
    """同步链上时间与系统时间"""
    try:
        service._ensure_initialized()
        service.ensure_ready()
        service._sync_chain_time()
        chain_time = service.w3.eth.get_block('latest').timestamp
        system_time = int(datetime.now(tz=timezone.utc).timestamp())
        return {"chainTime": chain_time, "systemTime": system_time, "synced": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(request: Request, payload: dict):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    user = auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    try:
        payload["from"] = user.address
        return service.create_project(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/donate")
async def donate(request: Request, project_id: int, payload: dict):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    user = auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    try:
        payload["from"] = user.address
        result = service.donate(project_id, payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/finish")
async def finish(project_id: int, payload: dict):
    try:
        return service.finish_project(project_id, payload["from"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/withdraw")
async def withdraw(project_id: int, payload: dict):
    try:
        return service.creator_withdraw(project_id, payload["from"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/refund")
async def refund(project_id: int, payload: dict):
    from_address = payload.get("from")
    
    # 查找用户
    user = auth_service.get_user_by_address(from_address)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取捐赠金额
    try:
        project = service.get_project(project_id)
        donation = next((d for d in project.donors if d["address"].lower() == from_address.lower()), None)
        if not donation:
            raise HTTPException(status_code=404, detail="未找到捐赠记录")
        
        refund_amount = donation.get("amount", 0)
        
        # 执行退款
        result = service.refund(project_id, from_address)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/milestones/{index}/complete")
async def complete_milestone(project_id: int, index: int, payload: dict):
    try:
        print(f"[DEBUG] complete_milestone called: project_id={project_id}, index={index}, from={payload.get('from')}")
        result = service.complete_milestone(project_id, index, payload["from"])
        print(f"[DEBUG] complete_milestone result: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] complete_milestone failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/milestones/{index}/release")
async def release_milestone(project_id: int, index: int, payload: dict):
    try:
        print(f"[DEBUG] release_milestone called: project_id={project_id}, index={index}, from={payload.get('from')}")
        result = service.release_milestone(project_id, index, payload["from"])
        print(f"[DEBUG] release_milestone result: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] release_milestone failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/monthly-support/start")
async def start_monthly_support(project_id: int, payload: dict):
    try:
        monthly_amount = payload.get("monthlyAmountEth", 0)
        return service.start_monthly_support(project_id, monthly_amount, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/monthly-support/stop")
async def stop_monthly_support(project_id: int, payload: dict):
    try:
        return service.stop_monthly_support(project_id, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/projects/{project_id}/monthly-support/{donor}")
async def get_monthly_support(project_id: int, donor: str):
    try:
        return service.get_monthly_support(project_id, donor)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== 认证 API ====================

@app.post("/api/login")
async def login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    
    token = auth_service.login(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    user = auth_service.get_user_by_username(username)
    return {
        "token": token,
        "user": {
            "username": user.username,
            "nickname": user.nickname,
            "address": user.address,
            "external_balance": user.external_balance
        }
    }

@app.post("/api/metamask/nonce")
async def metamask_nonce(payload: dict):
    address = payload.get("address")
    if not address:
        raise HTTPException(status_code=400, detail="地址不能为空")
    return auth_service.get_metamask_nonce(address)

@app.post("/api/login/metamask")
async def login_metamask(payload: dict):
    address = payload.get("address")
    signature = payload.get("signature")
    
    if not address or not signature:
        raise HTTPException(status_code=400, detail="地址和签名不能为空")
    
    token = auth_service.login_with_metamask(address, signature)
    if not token:
        raise HTTPException(status_code=401, detail="签名验证失败或未关联账户")
    
    user = auth_service.get_user_by_metamask_address(address)
    return {
        "token": token,
        "user": {
            "username": user.username,
            "nickname": user.nickname,
            "address": user.address,
            "external_balance": user.external_balance
        }
    }

@app.post("/api/metamask/link")
async def link_metamask(payload: dict, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    user = auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    metamask_address = payload.get("address")
    if not metamask_address:
        raise HTTPException(status_code=400, detail="Metamask地址不能为空")
    
    result = auth_service.link_metamask_address(user.username, metamask_address)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@app.post("/api/register")
async def register(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    nickname = payload.get("nickname", "")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    
    user = auth_service.register(username, password, nickname)
    if not user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    return {
        "message": "注册成功，请登录",
        "user": {
            "username": user.username,
            "nickname": user.nickname,
            "address": user.address
        }
    }

@app.post("/api/logout")
async def logout(payload: dict):
    token = payload.get("token")
    auth_service.logout(token)
    return {"message": "注销成功"}

@app.get("/api/user/me")
async def get_current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return {"authenticated": False}
    
    user = auth_service.validate_token(token)
    if not user:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "user": {
            "username": user.username,
            "nickname": user.nickname,
            "address": user.address,
            "external_balance": user.external_balance
        }
    }

@app.get("/api/user/balance/{address}")
async def get_balance(address: str):
    try:
        balance = service.get_balance(address)
        return {"balance": balance}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users")
async def list_users():
    return auth_service.list_users()

@app.get("/wallet")
async def wallet_page():
    return templates.TemplateResponse("wallet.html", {"request": {}})

@app.get("/api/user/transactions")
async def user_transactions(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    user = auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    try:
        return service.get_user_transactions(user.address)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contract/info")
async def contract_info():
    print("API: /api/contract/info")
    try:
        service._ensure_initialized()
        
        import json
        
        artifact_file = settings.artifact_file
        if artifact_file.exists():
            with open(artifact_file, 'r', encoding='utf-8') as f:
                artifact = json.load(f)
                abi = artifact.get('abi', [])
        else:
            abi = []
        
        use_tester = False
        
        if use_tester:
            network_config = {
                "chainId": "0x539",
                "chainName": "Localhost 8545",
                "nativeCurrency": {
                    "name": "Ethereum",
                    "symbol": "ETH",
                    "decimals": 18
                },
                "rpcUrls": ["http://127.0.0.1:8545"],
                "blockExplorerUrls": []
            }
        else:
            network_config = {
                "chainId": "0x7a69",
                "chainName": "Hardhat Local",
                "nativeCurrency": {
                    "name": "Ethereum",
                    "symbol": "ETH",
                    "decimals": 18
                },
                "rpcUrls": ["http://127.0.0.1:8545"],
                "blockExplorerUrls": []
            }
        
        return {
            "address": service.contract_address if service.ready else None,
            "abi": abi,
            "networkConfig": network_config,
            "ready": service.ready
        }
    except Exception as e:
        print(f"获取合约信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

print("应用初始化完成")