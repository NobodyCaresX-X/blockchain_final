import subprocess
import sys
import os

# 设置环境变量
env = os.environ.copy()
env['USE_TESTER'] = 'true'

# 启动服务器
cmd = [sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8002']

print(f"Running: {' '.join(cmd)}")
print(f"Env: USE_TESTER={env.get('USE_TESTER')}")

process = subprocess.Popen(
    cmd,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=os.getcwd()
)

print(f"Process started with PID: {process.pid}")

# 读取输出
try:
    for line in process.stdout:
        print(line.strip())
except KeyboardInterrupt:
    print("Interrupted")
    process.terminate()
    process.wait()
