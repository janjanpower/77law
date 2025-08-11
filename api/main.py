# api/main.py — single-start, clean routing with sys.path fix

import os, sys
from pathlib import Path
from datetime import datetime
from importlib import util as importlib_util

# ----------------------------
# 修正 sys.path（確保能找到 api.*）
# ----------------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ----------------------------
# FastAPI 初始化
# ----------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import api_routes

app = FastAPI(
    title="法律案件管理系統 API",
    version="3.3.0",
    description="Law Controller API",
)
# === 新增 import（檔頭區） ===
from api.database import Base, engine
from api.routes.case_upload_routes import router as case_router
from api.routes.file_routes import router as file_router
from api.routes.case_upsert_routes import router as cases_upsert_router
from api.routes import case_upload_routes
from api.routes.lawyer_routes import router as lawyer_router
from api.routes.line_routes import line_router

from api.routes import pending_routes
from api.routes import case_routes
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    print("✅ DB tables ensured.")
# 掛載路由
app.include_router(case_router)
app.include_router(file_router)
app.include_router(cases_upsert_router)
app.include_router(case_upload_routes.router)
app.include_router(lawyer_router)
app.include_router(pending_routes.router)
app.include_router(case_routes.router)
app.include_router(line_router)
# 掛載 API 路由
app.include_router(api_routes.router, prefix="/api/auth", tags=["auth"])

# 不一定存在 → 用安全匯入
try:
    from api.routes.case_query_routes import router as cases_query_router
    app.include_router(cases_query_router)
except ModuleNotFoundError:
    print("ℹ️ 可選路由省略：api.routes.case_query_routes 不存在，已略過")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Helper: include routes
# ----------------------------
def _include_case_upload_routes():
    try:
        from api.routes.case_upload_routes import router as case_upload_router
        app.include_router(case_upload_router, tags=["案件上傳"])
        print("✅ case_upload_routes loaded")
    except Exception as e:
        print(f"⚠️ case_upload_routes not loaded: {e}")

def _include_auth_routes_with_fallback():
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
            print("✅ api_routes loaded via fallback file path")
        else:
            print("❌ fallback file 'api_routes .py' not found")
    except Exception as e:
        print(f"❌ failed to load auth routes (fallback): {e}")

def _include_all_routes_once():
    if getattr(app.state, "routes_included", False):
        return
    _include_case_upload_routes()
    _include_auth_routes_with_fallback()
    app.state.routes_included = True

# ----------------------------
# One-time boot on startup
# ----------------------------
@app.on_event("startup")
async def _boot_once():
    if getattr(app.state, "boot_logged", False):
        return

    try:
        from dotenv import load_dotenv
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded .env: {env_path}")
        else:
            print("ℹ️ No .env found, using system env")
    except Exception as e:
        print(f"ℹ️ dotenv not available or failed: {e}")

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        os.environ["DATABASE_URL"] = db_url

    print(f"🔗 DB URL configured: {'✅' if db_url else '❌'}")

    _include_all_routes_once()

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

