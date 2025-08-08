#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
法律案件管理系統 - FastAPI 主應用程式
提供完整的案件管理、LINE BOT整合、認證系統功能
"""
import os
import sys
from datetime import datetime

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text


# ==================== 環境設定 ====================

# 環境變數
DATABASE_URL = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME", "unknown")

# 添加專案路徑到系統路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ==================== FastAPI 應用程式初始化 ====================

app = FastAPI(
    title="法律案件管理系統 API",
    version="3.1.0",
    description="提供完整的案件管理、LINE BOT整合、認證系統功能",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 請求處理時間中介軟體
@app.middleware("http")
async def add_process_time_header(request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ==================== 基本端點 ====================

@app.get("/")
async def root():
    """根端點 - 系統基本資訊"""
    return {
        "title": "法律案件管理系統 API",
        "version": "3.1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "endpoints": {
            "健康檢查": "/health",
            "認證系統": "/api/auth",
            "API文件": "/docs",
            "系統資訊": "/api/system/info"
        }
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    database_status = "connected" if DATABASE_URL else "not_configured"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": database_status,
        "environment": ENVIRONMENT,
        "version": "3.1.0"
    }

@app.get("/api/system/info")
def system_info():
    """系統詳細資訊端點"""
    return {
        "system": "法律案件管理系統",
        "version": "3.1.0",
        "python_version": sys.version,
        "environment": ENVIRONMENT,
        "heroku_app": HEROKU_APP_NAME,
        "database_configured": bool(DATABASE_URL),
        "timestamp": datetime.now().isoformat(),
        "features": [
            "案件管理",
            "LINE BOT 整合",
            "用戶認證系統",
            "檔案管理",
            "進度追蹤"
        ]
    }

# ==================== 資料庫設定 ====================

if DATABASE_URL:
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, declarative_base

        print(f"🔗 正在連接資料庫...")

        # 建立資料庫引擎
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()

        print(f"✅ 資料庫連線建立成功")

        # 資料庫會話依賴注入
        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        # 初始化資料庫
        try:
            Base.metadata.create_all(bind=engine)
            print(f"✅ 資料庫表初始化完成")
        except Exception as e:
            print(f"⚠️ 資料庫初始化警告: {e}")

    except Exception as e:
        print(f"❌ 資料庫連線失敗: {e}")
        DATABASE_URL = None

# ==================== 認證系統路由 ====================

if DATABASE_URL:
    # 建立認證路由
    auth_router = APIRouter()

    class ClientLoginRequest(BaseModel):
        client_id: str
        password: str

    @auth_router.get("/test")
    def test_auth():
        """認證系統測試端點"""
        return {
            "message": "認證系統正常運作",
            "timestamp": datetime.now().isoformat(),
            "database_connected": True
        }

    @auth_router.post("/client-login")
    def client_login(request: ClientLoginRequest):
        """
        客戶端登入端點

        嚴格檢查付費狀態：
        - tenant_status = true → 允許登入
        - tenant_status = false/null → 拒絕登入
        """
        db = None
        try:
            print(f"🔍 登入請求: {request.client_id}")

            # 建立資料庫連線
            db = SessionLocal()

            # 查詢用戶資料
            query = text("""
                SELECT client_id, client_name, password, user_status, plan_type,
                       max_users, current_users, is_active, tenant_status
                FROM login_users
                WHERE client_id = :client_id
                  AND password = :password
                  AND is_active = true
            """)

            result = db.execute(query, {
                "client_id": request.client_id,
                "password": request.password
            }).fetchone()

            if not result:
                print(f"❌ 帳號密碼驗證失敗")
                raise HTTPException(status_code=401, detail="客戶端ID或密碼錯誤")

            print(f"✅ 帳號密碼驗證成功: {result.client_name}")

            # 🎯 嚴格檢查付費狀態
            tenant_status = getattr(result, 'tenant_status', None)
            user_status = getattr(result, 'user_status', 'inactive')

            print(f"🔍 檢查付費狀態: tenant_status={tenant_status}, user_status={user_status}")

            # 付費狀態檢查
            if tenant_status is False:
                print(f"❌ 付費狀態檢查失敗: tenant_status為False")
                raise HTTPException(
                    status_code=403,
                    detail="您的事務所尚未完成付費，請聯繫管理員開通服務"
                )

            if tenant_status is None:
                print(f"❌ 付費狀態檢查失敗: tenant_status為None")
                raise HTTPException(
                    status_code=403,
                    detail="無法確認付費狀態，請聯繫管理員確認帳戶狀態"
                )

            if tenant_status is not True:
                print(f"❌ 付費狀態檢查失敗: tenant_status不為True")
                raise HTTPException(
                    status_code=403,
                    detail="帳戶付費狀態異常，請聯繫管理員"
                )

            # 用戶狀態檢查
            if user_status not in ['active', 'trial']:
                print(f"❌ 用戶狀態檢查失敗: user_status={user_status}")

                if user_status == 'suspended':
                    error_message = "您的帳戶已被暫停，請聯繫管理員"
                elif user_status == 'expired':
                    error_message = "您的帳戶已過期，請續費後再試"
                else:
                    error_message = f"帳戶狀態異常，請聯繫管理員"

                raise HTTPException(status_code=403, detail=error_message)

            print(f"✅ 付費狀態檢查通過")

            # 更新最後登入時間
            update_query = text("""
                UPDATE login_users
                SET last_login = :last_login
                WHERE client_id = :client_id
            """)

            db.execute(update_query, {
                "last_login": datetime.now(),
                "client_id": request.client_id
            })
            db.commit()

            # 組織回傳資料
            client_data = {
                "client_id": result.client_id,
                "client_name": result.client_name,
                "plan_type": getattr(result, 'plan_type', 'basic'),
                "user_status": user_status,
                "tenant_status": tenant_status,
                "max_users": getattr(result, 'max_users', 5),
                "current_users": getattr(result, 'current_users', 0),
                "available_slots": max(0, getattr(result, 'max_users', 5) - getattr(result, 'current_users', 0)),
                "usage_percentage": round((getattr(result, 'current_users', 0) / getattr(result, 'max_users', 5)) * 100, 1) if getattr(result, 'max_users', 5) > 0 else 0,
                "is_paid": True,
                "subscription_status": "active",
                "last_login": datetime.now().isoformat()
            }

            print(f"✅ 登入成功: {result.client_name}")

            return {
                "success": True,
                "message": f"歡迎 {result.client_name}",
                "client_data": client_data
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ 登入過程發生錯誤: {e}")
            raise HTTPException(status_code=500, detail=f"登入過程發生錯誤: {str(e)}")
        finally:
            if db:
                db.close()

    @auth_router.get("/client-status/{client_id}")
    def get_client_status(client_id: str):
        """取得客戶端狀態"""
        db = None
        try:
            db = SessionLocal()

            query = text("""
                SELECT client_id, client_name, user_status, plan_type,
                       max_users, current_users, tenant_status
                FROM login_users
                WHERE client_id = :client_id
            """)

            result = db.execute(query, {"client_id": client_id}).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="事務所不存在")

            return {
                "success": True,
                "data": {
                    "client_name": result.client_name,
                    "current_users": getattr(result, 'current_users', 0),
                    "max_users": getattr(result, 'max_users', 5),
                    "plan_type": getattr(result, 'plan_type', 'basic'),
                    "tenant_status": getattr(result, 'tenant_status', True),
                    "user_status": getattr(result, 'user_status', 'active')
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if db:
                db.close()

    # 註冊認證路由
    app.include_router(auth_router, prefix="/api/auth", tags=["認證系統"])
    print("✅ 認證路由載入成功")

else:
    print("❌ DATABASE_URL 未設定，跳過認證路由載入")

# ==================== 其他路由載入 ====================

try:
    # 嘗試載入其他路由模組
    from api.routes import register_routes, get_route_info

    # 註冊所有可用路由
    registered_count = register_routes(app)
    print(f"📋 額外路由載入完成，共載入 {registered_count} 個路由模組")

    # 新增路由資訊端點
    @app.get("/api/routes/info")
    def routes_info():
        """取得路由資訊"""
        return get_route_info()

except ImportError as e:
    print(f"⚠️ 其他路由模組載入警告: {e}")

# ==================== 全域例外處理 ====================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "找不到請求的資源",
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "伺服器內部錯誤",
            "timestamp": datetime.now().isoformat(),
            "message": "請聯繫系統管理員"
        }
    )

# ==================== 應用程式啟動 ====================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))

    print("=" * 50)
    print("🚀 法律案件管理系統 API 啟動中...")
    print(f"📍 環境: {ENVIRONMENT}")
    print(f"🔗 資料庫: {'已連線' if DATABASE_URL else '未設定'}")
    print(f"🌐 端口: {port}")
    print("=" * 50)

    uvicorn.run(
        "main:app" if __name__ == "__main__" else app,
        host="0.0.0.0",
        port=port,
        reload=ENVIRONMENT == "development"
    )