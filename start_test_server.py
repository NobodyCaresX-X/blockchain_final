import os
import subprocess
import sys

os.environ['USE_TESTER'] = 'true'

cmd = [
    sys.executable, '-m', 'uvicorn',
    'backend.app.main:app',
    '--host', '127.0.0.1',
    '--port', '8003',
    '--reload'
]

print(f"Starting with command: {' '.join(cmd)}")
print(f"Working directory: {os.getcwd()}")
print(f"USE_TESTER: {os.environ.get('USE_TESTER')}")

subprocess.run(cmd)