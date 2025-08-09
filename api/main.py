# api/main.py — cleaned
import os
import sys
from datetime import datetime
from pathlib import Path
from importlib import util as importlib_util

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def load_environment():
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded .env: {env_path}")
        else:
            print("ℹ️ No .env found, using system env")
    except Exception as e:
        print(f"ℹ️ dotenv not available or failed: {e}")

load_environment()

DATABASE_URL = os.getenv("DATABASE_URL", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME", "unknown")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"🔗 DB URL configured: {'✅' if DATABASE_URL else '❌'}")

app = FastAPI(
    title="法律案件管理系統 API",
    version="3.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

@app.get("/")
async def root():
    return {
        "app": "Law Controller API",
        "version": app.version,
        "environment": ENVIRONMENT,
        "heroku_app": HEROKU_APP_NAME,
        "time": datetime.now().isoformat(),
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "configured" if DATABASE_URL else "not_configured",
        "time": datetime.now().isoformat(),
    }

@app.get("/system/info")
async def system_info():
    return {
        "python": sys.version,
        "cwd": os.getcwd(),
        "env": {
            "ENVIRONMENT": ENVIRONMENT,
            "HEROKU_APP_NAME": HEROKU_APP_NAME,
            "DB_SET": bool(DATABASE_URL),
        },
    }

def include_case_upload_routes():
    try:
        from api.routes.case_upload_routes import router as case_upload_router
        app.include_router(case_upload_router, tags=["案件上傳"])
        print("✅ case_upload_routes loaded")
    except Exception as e:
        print(f"⚠️ case_upload_routes not loaded: {e}")

def include_auth_routes_with_fallback():
    try:
        from api.routes.api_routes import router as auth_router
        app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
        print("✅ api_routes loaded (normal)")
        return
    except Exception as e:
        print(f"⚠️ normal import failed: {e}")
    try:
        routes_dir = Path(__file__).parent / "routes"
        weird = routes_dir / "api_routes .py"
        if weird.exists():
            spec = importlib_util.spec_from_file_location("api_routes_fallback", str(weird))
            module = importlib_util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(module)
            auth_router = getattr(module, "router", None)
            if auth_router is None:
                raise RuntimeError("api_routes(.py) has no 'router'")
            app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
            print("✅ api_routes loaded via fallback file path (rename file later!)")
        else:
            print("❌ fallback file 'api_routes .py' not found. Please rename to 'api_routes.py'")
    except Exception as e:
        print(f"❌ failed to load auth routes (fallback): {e}")

include_case_upload_routes()
include_auth_routes_with_fallback()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Law Controller API")
    print(f"• ENV: {ENVIRONMENT}")
    print(f"• DB: {'✅ set' if DATABASE_URL else '❌ not set'}")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
