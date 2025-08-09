# api/main.py — single-start, clean routing
import os, sys
from pathlib import Path

# sys.path 修正（確保 api.* 可匯入）
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from datetime import datetime
from importlib import util as importlib_util
from api.routes import api_routes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# ----------------------------
# App
# ----------------------------
app = FastAPI(
    title="法律案件管理系統 API",
    version="3.3.0",
    description="Law Controller API",
)
# 掛載 API 路由
app.include_router(api_routes.router, prefix="/api/auth", tags=["auth"])
# CORS（需要可自行收斂網域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Helper: include routes (with fallback) — guarded
# ----------------------------
def _include_case_upload_routes():
    try:
        from api.routes.case_upload_routes import router as case_upload_router
        app.include_router(case_upload_router, tags=["案件上傳"])
        print("✅ case_upload_routes loaded")
    except Exception as e:
        print(f"⚠️ case_upload_routes not loaded: {e}")

def _include_auth_routes_with_fallback():
    """
    Normal:   from api.routes.api_routes import router
    Fallback: load file 'api_routes .py' (trailing space) if present
    """
    try:
        from api.routes.api_routes import router as auth_router
        app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
        print("✅ api_routes loaded (normal)")
        return
    except Exception as e:
        print(f"⚠️ normal import failed: {e}")

    # fallback by file path (handle filename with trailing space)
    try:
        routes_dir = Path(__file__).parent / "routes"
        weird = routes_dir / "api_routes .py"  # 注意：檔名含空白
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

def _include_all_routes_once():
    """避免重複掛載路由"""
    if getattr(app.state, "routes_included", False):
        return
    _include_case_upload_routes()
    _include_auth_routes_with_fallback()
    app.state.routes_included = True

# ----------------------------
# One-time boot on startup (no duplicate logs)
# ----------------------------
@app.on_event("startup")
async def _boot_once():
    # 已執行過就略過
    if getattr(app.state, "boot_logged", False):
        return

    # 1) 載入 .env（若存在）
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

    # 2) 修正 Heroku 舊版 Postgres 連線字首
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        os.environ["DATABASE_URL"] = db_url  # 回寫環境變數

    print(f"🔗 DB URL configured: {'✅' if db_url else '❌'}")

    # 3) 掛載路由（只做一次）
    _include_all_routes_once()

    # 4) 一次性啟動訊息
    env_name = os.getenv("ENVIRONMENT", "development")
    print("🚀 Starting Law Controller API")
    print(f"• ENV: {env_name}")
    print(f"• DB: {'✅ set' if db_url else '❌ not set'}")

    app.state.boot_logged = True

# ----------------------------
# Basic endpoints
# ----------------------------
@app.get("/")
async def root():
    return {
        "app": "Law Controller API",
        "version": app.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "time": datetime.now().isoformat(),
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "configured" if os.getenv("DATABASE_URL") else "not_configured",
        "time": datetime.now().isoformat(),
    }

@app.get("/system/info")
async def system_info():
    return {
        "python": sys.version,
        "cwd": os.getcwd(),
        "env": {
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
            "DB_SET": bool(os.getenv("DATABASE_URL")),
        },
    }

# ----------------------------
# Entrypoint (local run)
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
