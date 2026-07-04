import os
import sys
import time
import subprocess
import webbrowser
import signal

def print_banner():
    print("\n" + "=" * 70)
    print("                    区块链众筹系统")
    print("                  【一键测试启动器】")
    print("=" * 70 + "\n")

def print_step(step, total, text):
    print(f"[{step}/{total}] {text}")

def check_command(cmd, name):
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True
    except:
        print(f"   ✗ {name} 未安装或未添加到 PATH")
        return False

def kill_old_processes():
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline())
                if 'hardhat' in cmdline.lower() or 'uvicorn' in cmdline.lower():
                    proc.kill()
                    time.sleep(1)
            except:
                pass
    except:
        subprocess.run(['taskkill', '/F', '/IM', 'node.exe'], capture_output=True)
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
        time.sleep(2)

def main():
    print_banner()

    print_step(1, 5, "检查环境...")
    
    if not check_command(['conda', '--version'], 'Conda'):
        print("   请安装 Miniconda 并配置环境变量")
        input("\n按回车键退出...")
        return
    
    if not check_command(['node', '--version'], 'Node.js'):
        print("   请安装 Node.js (推荐 LTS 版本)")
        input("\n按回车键退出...")
        return
    
    print("   ✓ 环境检查通过")

    project_dir = os.path.dirname(os.path.abspath(__file__))
    hardhat_dir = os.path.join(project_dir, 'hardhat')

    print_step(2, 5, "启动 Hardhat 本地区块链...")
    
    kill_old_processes()

    hardhat_cmd = ['node', 'node_modules/hardhat/bin/hardhat.js', 'node']
    hardhat_proc = subprocess.Popen(
        hardhat_cmd,
        cwd=hardhat_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(6)
    
    import web3
    w3 = web3.Web3(web3.Web3.HTTPProvider("http://127.0.0.1:8545", request_kwargs={"timeout": 5}))
    if w3.is_connected():
        print(f"   ✓ Hardhat 节点已启动 (Block #{w3.eth.block_number})")
    else:
        print("   ✗ Hardhat 节点启动失败，请检查端口是否被占用")
        hardhat_proc.kill()
        input("\n按回车键退出...")
        return

    print_step(3, 5, "编译并部署智能合约...")
    
    os.chdir(hardhat_dir)
    
    if not os.path.exists('node_modules'):
        print("   正在安装依赖...")
        subprocess.run(['npm', 'install'], check=True)
    
    subprocess.run(['npx', 'hardhat', 'compile'], check=True)
    subprocess.run(['npx', 'hardhat', 'run', 'scripts/deploy.js', '--network', 'localhost'], check=True)
    
    os.chdir(project_dir)
    print("   ✓ 合约编译部署成功")

    print_step(4, 5, "启动后端服务...")
    
    python_path = r"C:\Users\efzzz\miniconda3\envs\ai_env\python.exe"
    
    env = os.environ.copy()
    env['USE_TESTER'] = 'false'
    
    backend_proc = subprocess.Popen(
        [python_path, '-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8000'],
        env=env,
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(8)
    
    try:
        import requests
        r = requests.get("http://127.0.0.1:8000/api/bootstrap", timeout=5)
        if r.status_code == 200:
            print("   ✓ 后端服务已启动")
        else:
            print("   ✗ 后端服务启动异常")
    except:
        print("   ✓ 后端服务已启动（无法自动验证，请手动访问）")

    print_step(5, 5, "打开浏览器...")
    
    webbrowser.open("http://127.0.0.1:8000")
    print("   ✓ 浏览器已打开")

    print("\n" + "=" * 70)
    print("                    启动完成！")
    print("")
    print("   访问地址: http://127.0.0.1:8000")
    print("")
    print("   使用 Metamask 连接:")
    print("     - 网络名称: Hardhat Local")
    print("     - RPC URL: http://127.0.0.1:8545")
    print("     - 链 ID: 31337")
    print("     - 货币符号: ETH")
    print("")
    print("   测试账户私钥 (第一个):")
    print("     0xac0974bec39a17e36ba4a6b4d238ff948bacb478cbed5efcae784d7bf4f2ff80")
    print("")
    print("   按 Ctrl+C 停止服务")
    print("=" * 70 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        backend_proc.terminate()
        hardhat_proc.terminate()
        print("服务已停止")

if __name__ == "__main__":
    main()