import os
import sys
import subprocess

os.environ['USE_TESTER'] = 'true'

cmd = [
    sys.executable, '-m', 'uvicorn',
    'backend.app.main:app',
    '--host', '127.0.0.1',
    '--port', '8002',
    '--reload'
]

print(f"Starting with command: {' '.join(cmd)}")
print(f"Working directory: {os.getcwd()}")
print(f"USE_TESTER: {os.environ.get('USE_TESTER')}")

result = subprocess.run(cmd, capture_output=True, text=True)
print(f"Exit code: {result.returncode}")
print(f"STDOUT:\n{result.stdout}")
print(f"STDERR:\n{result.stderr}")
