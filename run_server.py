import os
os.environ['USE_TESTER'] = 'true'

import uvicorn
from backend.app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
