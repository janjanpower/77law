# api/main.py — cleaned & Heroku-friendly
import os
import sys
from datetime import datetime
from pathlib import Path

# --- Robust import bootstrap (works for both module & direct file run) ---
try:
    # Prefer absolute imports when running as a package (Heroku / uvicorn)
    from api.routes import routes_upload, routes_search  # noqa: F401
except ModuleNotFoundError:
    HERE = Path(__file__).resolve()
    PKG_ROOT = HERE.parents[1]  # .../law_controller
    if str(PKG_ROOT) not in sys.path:
        sys.path.insert(0, str(PKG_ROOT))
    from api.routes import routes_upload, routes_search  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

# Import routers (absolute paths only)
from api.routes.api_routes import router as auth_router
from api.routes.case_routes import router as cases_router
from api.routes.case_upload_routes import router as case_upload_router
from api.routes.case_upsert_routes import router as cases_upsert_router
from api.routes.file_routes import router as file_router
from api.routes.lawyer_routes import router as lawyer_router, router_user as user_router
from api.routes.line_routes import line_router
from api.routes.pending_routes import router as pending_router

# Optional routes
try:
    from api.routes.case_query_routes import router as cases_query_router  # type: ignore
except Exception:
    cases_query_router = None

# Ensure operationId uniqueness
def gen_unique_id(route: APIRoute) -> str:
    tag = (route.tags[0] if route.tags else "default").lower()
    method = next(iter(route.methods)).lower()
    return f"{tag}_{route.path.strip('/').replace('/', '_')}_{method}"

app = FastAPI(
    title="法律案件管理系統 API",
    version="3.3.1",
    description="Law Controller API",
    generate_unique_id_function=gen_unique_id,
)

# ---- Mount routers (normalized prefixes) ----
# Keep your original cases prefixes
app.include_router(routes_upload.router, prefix="/api/cases", tags=["Cases"])
app.include_router(routes_search.router, prefix="/api/cases", tags=["Cases"])

# Standardize critical endpoints used by LINE / n8n
app.include_router(line_router, prefix="/api")                 # => /api/lawyer/verify-secret, /api/line/resolve-route
app.include_router(user_router, prefix="/api/user", tags=["user"])  # => /api/user/my-cases

# Other routers (preserve original behavior)
app.include_router(case_upload_router, tags=["cases"])
app.include_router(cases_upsert_router)
app.include_router(cases_router)
app.include_router(lawyer_router)
app.include_router(file_router)
app.include_router(pending_router)
if cases_query_router:
    app.include_router(cases_query_router)

# ---- CORS ----
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
