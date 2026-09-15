import os
import sys
import uvicorn

# Ensure the backend directory is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Cement Store Billing & Accounting Server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
