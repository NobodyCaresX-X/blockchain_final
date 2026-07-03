import os
os.environ['USE_TESTER'] = 'true'

print("Starting server...")
print(f"Python: {os.sys.executable}")
print(f"Working dir: {os.getcwd()}")

try:
    from backend.app.main import app
    print("App imported successfully")
    
    import uvicorn
    print("Starting uvicorn...")
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
