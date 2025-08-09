#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API 模組
LINE BOT案件管理API系統的主要模組
"""

# 版本資訊
__version__ = "2.0.0"
__title__ = "LINE BOT案件管理API"
__description__ = "為LINE BOT設計的案件管理API系統，採用模組化架構"
__author__ = "專業Python工程團隊"

# 嘗試導入主要組件
try:
    from .main import app as main_app
    MAIN_APP_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告：無法載入主應用程式 - {e}")
    main_app = None
    MAIN_APP_AVAILABLE = False

# 只匯入新的註冊函式；不再匯入 webhook_router/case_router/health_router/get_route_info
try:
    from .routes import register_routes
    ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告：無法載入路由註冊函式 - {e}")
    register_routes = None  # type: ignore
    ROUTES_AVAILABLE = False

# Schemas（若存在就載）
try:
    from .schemas import (
        LineWebhookRequest,
        LineWebhookResponse,
        CaseDetailResponse,
        CaseListResponse,
        SystemStatusResponse
    )
    SCHEMAS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告：無法載入資料模型 - {e}")
    SCHEMAS_AVAILABLE = False

# 快速創建API應用程式的函數
def create_app():
    """
    創建並配置FastAPI應用程式
    """
    from fastapi import FastAPI
    from datetime import datetime

    app = FastAPI(
        title=__title__,
        version=__version__,
        description=__description__
    )

    # 註冊路由（若可用）
    if ROUTES_AVAILABLE and callable(register_routes):
        try:
            register_routes(app)  # 由 api.routes.__init__.py 提供
        except Exception as e:
            print(f"❌ 路由註冊失敗: {e}")

    # 基本中介軟體
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        import time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # 根端點
    @app.get("/")
    async def root():
        return {
            "title": __title__,
            "version": __version__,
            "description": __description__,
            "timestamp": datetime.now().isoformat(),
            "status": "running",
            "endpoints": {
                "health": "/health",
                "docs": "/docs"
            }
        }

    return app

# 取得系統狀態
def get_system_status():
    """取得API系統狀態"""
    return {
        "version": __version__,
        "main_app_available": MAIN_APP_AVAILABLE,
        "routes_available": ROUTES_AVAILABLE,
        "schemas_available": SCHEMAS_AVAILABLE,
        "components": {
            "main_app": MAIN_APP_AVAILABLE,
            "routes_register": ROUTES_AVAILABLE,
            "schemas": SCHEMAS_AVAILABLE
        }
    }

# 匯出主要組件
__all__ = [
    "__version__",
    "__title__",
    "__description__",
    "__author__",
    "main_app",
    "create_app",
    "get_system_status",
    "MAIN_APP_AVAILABLE",
    "ROUTES_AVAILABLE",
    "SCHEMAS_AVAILABLE",
]

# 若路由註冊可用，則一併匯出
if ROUTES_AVAILABLE:
    __all__.extend([
        "register_routes"
    ])

print(f"📦 {__title__} v{__version__} 模組已載入")
print(f"🔧 主應用程式: {'✅' if MAIN_APP_AVAILABLE else '❌'}")
print(f"🛣️  路由註冊: {'✅' if ROUTES_AVAILABLE else '❌'}")
print(f"📊 資料模型: {'✅' if SCHEMAS_AVAILABLE else '❌'}")
