# api/main.py — clean single include version
try:
    from api.routes import routes_upload, routes_search  # 先嘗試原本的匯入
except ModuleNotFoundError:
    import sys, pathlib
    HERE = pathlib.Path(__file__).resolve()
    # 將 law_controller 這層加入 sys.path，讓 `from api...` 成為頂層 package
    PKG_ROOT = HERE.parents[1]  # .../law_controller
    if str(PKG_ROOT) not in sys.path:
        sys.path.insert(0, str(PKG_ROOT))
    # 再試一次
    from api.routes import routes_upload, routes_search
import os, sys
from datetime import datetime
from pathlib import Path

from api.routes import routes_upload, routes_search
from api.routes.api_routes import router as auth_router
from api.routes.case_routes import router as cases_router
from api.routes.case_upload_routes import router as case_upload_router
from api.routes.case_upsert_routes import router as cases_upsert_router
from api.routes.file_routes import router as file_router
from api.routes.lawyer_routes import router as lawyer_router, router_user as user_router
from api.routes.line_routes import line_router
from api.routes.pending_routes import router as pending_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute


# 將 law_controller 的上層資料夾加入搜尋路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# (可選) 確保 operationId 唯一
def gen_unique_id(route: APIRoute) -> str:
    tag = (route.tags[0] if route.tags else "default").lower()
    method = next(iter(route.methods)).lower()
    return f"{tag}_{route.path.strip('/').replace('/', '_')}_{method}"

app = FastAPI(
    title="法律案件管理系統 API",
    version="3.3.0",
    description="Law Controller API",
    generate_unique_id_function=gen_unique_id
)

# ---- 單一來源，每個 router 掛一次 ----
app.include_router(routes_upload.router, prefix="/api/cases", tags=["Cases"])
app.include_router(routes_search.router, prefix="/api/cases", tags=["Cases"])
app.include_router(case_upload_router, tags=["cases"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(line_router)
app.include_router(file_router)
app.include_router(cases_upsert_router)
app.include_router(cases_router)
app.include_router(lawyer_router)
app.include_router(user_router)
app.include_router(pending_router)
app.include_router(user_router, prefix="/user")

# 可選載入
try:
    from api.routes.case_query_routes import router as cases_query_router
    app.include_router(cases_query_router)
except ModuleNotFoundError:
    print("ℹ️ 可選路由省略：api.routes.case_query_routes 不存在")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Basic endpoints ----
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
