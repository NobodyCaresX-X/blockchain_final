import os
import sys
import multiprocessing

def run_server():
    os.environ['USE_TESTER'] = 'true'
    import uvicorn
    from backend.app.main import app
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")

if __name__ == "__main__":
    p = multiprocessing.Process(target=run_server)
    p.daemon = True
    p.start()
    print(f"Server started with PID: {p.pid}")
    p.join()
