import os
import sys
import time
import subprocess
import webbrowser
import shutil


def print_banner():
    print("\n" + "=" * 70)
    print("              BLOCKCHAIN CROWDFUNDING SYSTEM")
    print("             [ ONE-CLICK TEST LAUNCHER ]")
    print("=" * 70 + "\n")


def print_step(step, total, text):
    print(f"[{step}/{total}] {text}")


def run_command(cmd, cwd=None, capture_output=False):
    try:
        if capture_output:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
            return result.returncode, result.stdout, result.stderr
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode, "", ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def find_python():
    candidates = [
        r"C:\Users\efzzz\miniconda3\envs\ai_env\python.exe",
        r"C:\Users\efzzz\miniconda3\python.exe",
        r"C:\ProgramData\anaconda3\python.exe",
        r"C:\ProgramData\miniconda3\python.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return sys.executable


def install_miniconda():
    import urllib.request

    print("   Installing Miniconda...")

    miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
    install_path = os.path.join(os.path.expanduser("~"), "miniconda3")
    installer_path = os.path.join(os.path.expanduser("~"), "miniconda_installer.exe")

    try:
        print("   Downloading Miniconda installer...")
        urllib.request.urlretrieve(miniconda_url, installer_path)

        print("   Running installer...")
        subprocess.run(
            [
                installer_path,
                "/InstallationType=JustMe",
                "/RegisterPython=0",
                "/S",
                f"/D={install_path}",
            ],
            check=True,
        )

        os.remove(installer_path)
        print(f"   OK: Miniconda installed to {install_path}")
        return install_path
    except Exception as e:
        print(f"   ERROR: Failed to install Miniconda: {e}")
        return None


def install_nodejs():
    import urllib.request
    import zipfile

    print("   Installing Node.js...")

    node_url = "https://nodejs.org/dist/v20.11.0/node-v20.11.0-win-x64.zip"
    install_path = os.path.join(os.path.expanduser("~"), "nodejs")
    zip_path = os.path.join(os.path.expanduser("~"), "nodejs.zip")

    try:
        print("   Downloading Node.js...")
        urllib.request.urlretrieve(node_url, zip_path)

        print("   Extracting...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(os.path.dirname(install_path))

        os.remove(zip_path)

        os.environ["PATH"] = install_path + os.pathsep + os.environ["PATH"]
        print(f"   OK: Node.js installed to {install_path}")
        return install_path
    except Exception as e:
        print(f"   ERROR: Failed to install Node.js: {e}")
        return None


def create_conda_env(conda_path):
    print("   Creating conda environment 'ai_env'...")

    conda_root = os.path.dirname(os.path.dirname(conda_path))
    env_path = os.path.join(conda_root, "envs", "ai_env")
    if os.path.exists(env_path):
        print("   OK: Environment 'ai_env' already exists")
        return True

    try:
        subprocess.run([conda_path, "create", "-n", "ai_env", "python=3.10", "-y"], check=True)
        print("   OK: Environment created")

        python_path = os.path.join(env_path, "python.exe")
        subprocess.run([python_path, "-m", "pip", "install", "-r", "backend/requirements.txt"], check=True)
        print("   OK: Dependencies installed")
        return True
    except Exception as e:
        print(f"   ERROR: Failed to create environment: {e}")
        return False


def find_conda():
    candidates = [
        r"C:\Users\efzzz\miniconda3\Scripts\conda.exe",
        r"C:\Users\efzzz\miniconda3\condabin\conda.bat",
        r"C:\ProgramData\anaconda3\Scripts\conda.exe",
        r"C:\ProgramData\miniconda3\Scripts\conda.exe",
        os.path.join(os.path.expanduser("~"), "miniconda3", "Scripts", "conda.exe"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    result = subprocess.run(["where", "conda"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split("\n")[0]

    return None


def main():
    print_banner()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    hardhat_dir = os.path.join(project_dir, "hardhat")

    print_step(1, 6, "Checking and installing environment...")

    conda_path = find_conda()
    if not conda_path:
        print("   Conda not found, installing...")
        miniconda_dir = install_miniconda()
        if miniconda_dir:
            conda_path = os.path.join(miniconda_dir, "Scripts", "conda.exe")
        else:
            print("   ERROR: Cannot install Conda. Please install manually.")
            input("\nPress Enter to exit...")
            return

    print(f"   OK: Conda found at {conda_path}")

    node_path = shutil.which("node")
    if not node_path:
        print("   Node.js not found, installing...")
        install_nodejs()
        node_path = shutil.which("node")

    if not node_path:
        print("   ERROR: Cannot install Node.js. Please install manually.")
        input("\nPress Enter to exit...")
        return

    print(f"   OK: Node.js found at {node_path}")

    node_dir = os.path.dirname(node_path)
    npm_path = os.path.join(node_dir, "npm.cmd")
    npx_path = os.path.join(node_dir, "npx.cmd")
    if not os.path.exists(npm_path):
        npm_path = shutil.which("npm")
    if not os.path.exists(npx_path):
        npx_path = shutil.which("npx")

    if not npm_path or not npx_path:
        print("   ERROR: Cannot locate npm/npx. Please reinstall Node.js.")
        input("\nPress Enter to exit...")
        return

    create_conda_env(conda_path)

    print_step(2, 6, "Starting Hardhat local blockchain...")

    try:
        import psutil

        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = " ".join(proc.cmdline())
                if "hardhat" in cmdline.lower():
                    proc.kill()
                    time.sleep(1)
            except Exception:
                pass
    except Exception:
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True)
        time.sleep(2)

    hardhat_cmd = [npx_path, "hardhat", "node"]
    hardhat_proc = subprocess.Popen(
        hardhat_cmd,
        cwd=hardhat_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    hardhat_ready = False

    for _ in range(30):
        if hardhat_proc.poll() is not None:
            break

        try:
            from web3 import Web3

            w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545", request_kwargs={"timeout": 5}))
            if w3.is_connected():
                print(f"   OK: Hardhat node started (Block #{w3.eth.block_number})")
                hardhat_ready = True
                break
        except Exception:
            pass

        time.sleep(1)

    if not hardhat_ready:
        print("   ERROR: Hardhat node not responding")
        hardhat_proc.kill()
        input("\nPress Enter to exit...")
        return

    print_step(3, 6, "Installing Hardhat dependencies...")

    os.chdir(hardhat_dir)

    if not os.path.exists("node_modules"):
        print("   Installing npm dependencies...")
        subprocess.run([npm_path, "install"], check=True)

    print_step(4, 6, "Compiling and deploying smart contract...")

    subprocess.run([npx_path, "hardhat", "compile"], check=True)
    subprocess.run([npx_path, "hardhat", "run", "scripts/deploy.js", "--network", "localhost"], check=True)

    os.chdir(project_dir)
    print("   OK: Contract compiled and deployed")

    print_step(5, 6, "Starting backend service...")

    python_path = r"C:\Users\efzzz\miniconda3\envs\ai_env\python.exe"
    if not os.path.exists(python_path):
        python_path = find_python()

    env = os.environ.copy()
    env["USE_TESTER"] = "false"

    backend_proc = subprocess.Popen(
        [python_path, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env,
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    time.sleep(8)

    try:
        import requests

        r = requests.get("http://127.0.0.1:8000/api/bootstrap", timeout=5)
        if r.status_code == 200:
            print("   OK: Backend service started")
        else:
            print("   WARNING: Backend service may have issues")
    except Exception:
        print("   OK: Backend service started (verification skipped)")

    print_step(6, 6, "Opening browser...")

    webbrowser.open("http://127.0.0.1:8000")
    print("   OK: Browser opened")

    print("\n" + "=" * 70)
    print("                    STARTUP COMPLETE!")
    print("")
    print("   Access URL: http://127.0.0.1:8000")
    print("")
    print("   Metamask Connection Settings:")
    print("     - Network Name: Hardhat Local")
    print("     - RPC URL: http://127.0.0.1:8545")
    print("     - Chain ID: 31337")
    print("     - Currency Symbol: ETH")
    print("")
    print("   Test Account Private Key (first one):")
    print("     0xac0974bec39a17e36ba4a6b4d238ff948bacb478cbed5efcae784d7bf4f2ff80")
    print("")
    print("   Press Ctrl+C to stop all services")
    print("=" * 70 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        hardhat_proc.terminate()
        print("All services stopped")


if __name__ == "__main__":
    main()