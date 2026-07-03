import os

os.environ['USE_TESTER'] = 'false'
os.environ['RPC_URL'] = 'http://127.0.0.1:8545'

import uvicorn
from backend.app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
