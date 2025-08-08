# api/main.py (環境變數修復版)
# 解決 Heroku 無法讀取 DATABASE_URL 的問題

import os
import sys
from datetime import datetime

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 建立FastAPI應用程式
app = FastAPI(
    title="法律案件管理系統 API",
    version="3.2.0",
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


# 1. 在檔案頂部的導入區域新增：
try:
    from api.routes.case_upload_routes import router as case_upload_router
    CASE_UPLOAD_AVAILABLE = True
    print("✅ 案件上傳路由載入成功")
except ImportError as e:
    print(f"⚠️ 案件上傳路由載入失敗: {e}")
    CASE_UPLOAD_AVAILABLE = False

# 2. 在路由註冊區域新增（通常在app初始化之後）：
if CASE_UPLOAD_AVAILABLE:
    # 註冊案件上傳路由
    app.include_router(case_upload_router, tags=["案件管理"])
    print("✅ 案件上傳路由註冊成功")
else:
    print("⚠️ 案件上傳路由不可用")

# ==================== 環境變數載入 ====================

def load_environment():
    """載入環境變數 - 支援 .env 文件和 Heroku 環境變數"""
    try:
        # 方法1: 嘗試載入 python-dotenv (如果可用)
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✅ 載入 .env 文件: {env_path}")
            else:
                print("ℹ️ 沒有找到 .env 文件，使用系統環境變數")
        except ImportError:
            print("ℹ️ python-dotenv 不可用，使用系統環境變數")

        # 方法2: 手動讀取 .env 文件 (備用方案)
        if not os.getenv("DATABASE_URL"):
            env_file = Path(__file__).parent.parent / '.env'
            if env_file.exists():
                print("🔧 手動讀取 .env 文件...")
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # 移除引號
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]

                            # 只有在環境變數不存在時才設定
                            if not os.getenv(key):
                                os.environ[key] = value
                print("✅ 手動載入 .env 文件完成")

        # 方法3: 硬編碼 DATABASE_URL (最後備用方案)
        if not os.getenv("DATABASE_URL"):
            print("⚠️ 無法從環境變數或 .env 文件讀取 DATABASE_URL")
            print("🔧 使用硬編碼的資料庫連線...")
            # 您的 PostgreSQL 連線字串
            os.environ["DATABASE_URL"] = "postgresql://uekiogttp3k83o:p185ab9eb7a3e51077a51d9cba099beefce0c5351ed9d3d3f073f6b573c406fdc@cer3tutrbi7n1t.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/debg6ra63vhnin"
            print("✅ 硬編碼 DATABASE_URL 已設定")

        # 顯示環境變數狀態
        database_url = os.getenv("DATABASE_URL", "")
        if database_url:
            # 隱藏敏感資訊
            safe_url = database_url.split('@')[0] + "@[HIDDEN]" if '@' in database_url else database_url
            print(f"✅ DATABASE_URL 已設定: {safe_url}")
        else:
            print("❌ DATABASE_URL 仍未設定")

        # 設定其他預設環境變數
        if not os.getenv("ENVIRONMENT"):
            os.environ["ENVIRONMENT"] = "production"

        return True

    except Exception as e:
        print(f"❌ 環境變數載入失敗: {e}")
        return False

# 載入環境變數
load_environment()

# 環境變數
DATABASE_URL = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME", "unknown")

# 修正 PostgreSQL URL
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"🔗 資料庫連線狀態: {'✅ 已設定' if DATABASE_URL else '❌ 未設定'}")


# 確保路徑正確
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# ==================== 基本端點 ====================

@app.get("/")
async def root():
    """根端點"""
    return {
        "title": "法律案件管理系統 API",
        "version": "3.2.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "features": {
            "user_authentication": bool(DATABASE_URL),
            "case_upload": CASE_UPLOAD_AVAILABLE,
            "database_storage": bool(DATABASE_URL)
        },
        "endpoints": {
            "健康檢查": "/health",
            "認證系統": "/api/auth",
            "案件上傳": "/api/cases/upload" if CASE_UPLOAD_AVAILABLE else "不可用",
            "系統資訊": "/api/system/info",
            "API文件": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    database_status = "connected" if DATABASE_URL else "not_configured"

    # 檢查案件資料庫表格
    case_db_status = "unknown"
    if DATABASE_URL:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'case_records'
                    );
                """))
                case_db_status = "ready" if result.scalar() else "tables_not_created"
        except Exception as e:
            case_db_status = f"error: {str(e)[:50]}"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": database_status,
        "case_database": case_db_status,
        "case_upload_api": CASE_UPLOAD_AVAILABLE,
        "environment": ENVIRONMENT,
        "version": "3.2.0"
    }

@app.get("/api/system/info")
def system_info():
    """系統資訊端點"""
    return {
        "system": "法律案件管理系統",
        "version": "3.2.0",
        "environment": ENVIRONMENT,
        "heroku_app": HEROKU_APP_NAME,
        "database_configured": bool(DATABASE_URL),
        "case_upload_enabled": CASE_UPLOAD_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

# ==================== 資料庫和認證設定 ====================


if DATABASE_URL:
    print(f"✅ 成功取得 DATABASE_URL")

    try:
        from fastapi import APIRouter, Depends
        from pydantic import BaseModel
        from sqlalchemy.orm import Session
        from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, func, text
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker
        from api.database import Base, get_control_db

        # 建立引擎
        engine = create_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300
        )
        print("✅ 資料庫引擎建立成功")

        # 建立表格
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ 資料庫表格初始化完成")
        except Exception as e:
            print(f"⚠️ 資料庫表格初始化警告: {e}")

    except Exception as e:
        print(f"❌ 資料庫設定失敗: {e}")
        DATABASE_URL = None

# ==================== 案件上傳功能設定 ====================

# 🔥 關鍵修復：在 app 初始化之後才導入和註冊路由
CASE_UPLOAD_AVAILABLE = False

if DATABASE_URL:
    try:
        # 導入案件上傳路由
        from api.routes.case_upload_routes import router as case_upload_router
        from api.models_cases import CaseRecord, UploadLog  # 確保模型已載入

        # 註冊案件上傳路由
        app.include_router(case_upload_router, tags=["案件管理"])

        CASE_UPLOAD_AVAILABLE = True
        print("✅ 案件上傳功能已啟用")

    except ImportError as e:
        print(f"⚠️ 案件上傳路由載入失敗: {e}")
        CASE_UPLOAD_AVAILABLE = False
    except Exception as e:
        print(f"❌ 案件上傳功能初始化失敗: {e}")
        CASE_UPLOAD_AVAILABLE = False

# ==================== 認證系統路由 ====================

if DATABASE_URL:
    try:
        from api.routes.api_routes import router as auth_router
        app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
        print("✅ 認證系統路由已載入")
    except Exception as e:
        print(f"⚠️ 認證系統路由載入失敗: {e}")

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()

        # 資料庫模型
        class LoginUser(Base):
            __tablename__ = "login_users"
            id = Column(Integer, primary_key=True, index=True)
            client_name = Column(String, nullable=False)
            client_id = Column(String, unique=True, nullable=False)
            password = Column(String, nullable=False)
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            last_login = Column(DateTime(timezone=True), nullable=True)
            plan_type = Column(String, default="basic_5")
            user_status = Column(String, default="active")
            max_users = Column(Integer, default=5)
            current_users = Column(Integer, default=0)

        # 建立表格
        def init_database():
            try:
                Base.metadata.create_all(bind=engine)
                print("✅ 資料表初始化完成")

                # 檢查是否需要插入測試資料
                db = SessionLocal()
                try:
                    existing_count = db.query(LoginUser).count()
                    if existing_count == 0:
                        print("🔧 插入測試資料...")
                        test_user = LoginUser(
                            client_name="測試法律事務所",
                            client_id="test_law_firm",
                            password="test123",
                            plan_type="basic_5",
                            max_users=5,
                            current_users=0,
                            is_active=True
                        )
                        db.add(test_user)
                        db.commit()
                        print("✅ 測試資料插入完成")
                    else:
                        print(f"ℹ️ 資料庫已有 {existing_count} 筆用戶資料")
                finally:
                    db.close()

            except Exception as e:
                print(f"⚠️ 資料庫初始化警告: {e}")

        # 初始化資料庫
        init_database()

        # 資料庫會話
        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        if DATABASE_URL:
            try:
                print("🔧 開始載入認證路由...")

                # 🎯 完整流程：建立認證路由，包含完整資料庫查詢
                auth_router = APIRouter()

                class ClientLoginRequest(BaseModel):
                    client_id: str
                    password: str

                @auth_router.get("/test")
                def test_auth():
                    """測試端點"""
                    return {
                        "message": "認證 API 正常運作",
                        "timestamp": datetime.now().isoformat(),
                        "database_connected": True
                    }

                @auth_router.post("/client-login")
                def client_login(request: ClientLoginRequest):
                    """
                    客戶端登入端點 - 修正付費狀態檢查

                    🎯 核心邏輯：
                    1. 先驗證帳號密碼
                    2. 檢查付費狀態 (tenant_status)
                    3. 付費狀態為 false/null 時直接拒絕登入
                    4. 付費狀態為 true 時才允許登入
                    """
                    db = None
                    try:
                        print(f"🔍 步驟1: 收到登入請求 - {request.client_id}")

                        # 建立資料庫連線
                        db = SessionLocal()
                        print(f"✅ 步驟2: 資料庫連線成功")

                        # 查詢用戶資料
                        from sqlalchemy import text

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
                            print(f"❌ 步驟3: 帳號密碼驗證失敗")
                            raise HTTPException(status_code=401, detail="客戶端ID或密碼錯誤")

                        print(f"✅ 步驟3: 帳號密碼驗證成功 - 找到客戶端: {result.client_name}")

                        # 🎯 關鍵修正：嚴格檢查付費狀態
                        tenant_status = getattr(result, 'tenant_status', None)
                        user_status = getattr(result, 'user_status', 'inactive')

                        print(f"🔍 步驟4: 檢查付費狀態 - tenant_status={tenant_status}, user_status={user_status}")

                        # 🚨 嚴格的付費狀態檢查
                        if tenant_status is False:
                            print(f"❌ 步驟4: 付費狀態檢查失敗 - tenant_status為False")
                            raise HTTPException(
                                status_code=403,
                                detail="您的事務所尚未完成付費，請聯繫管理員開通服務"
                            )

                        if tenant_status is None:
                            print(f"❌ 步驟4: 付費狀態檢查失敗 - tenant_status為None")
                            raise HTTPException(
                                status_code=403,
                                detail="無法確認付費狀態，請聯繫管理員確認帳戶狀態"
                            )

                        if tenant_status is not True:
                            print(f"❌ 步驟4: 付費狀態檢查失敗 - tenant_status不為True (值:{tenant_status})")
                            raise HTTPException(
                                status_code=403,
                                detail="帳戶付費狀態異常，請聯繫管理員"
                            )

                        # 額外的用戶狀態檢查
                        if user_status not in ['active', 'trial']:
                            print(f"❌ 步驟4: 用戶狀態檢查失敗 - user_status={user_status}")

                            if user_status == 'suspended':
                                error_message = "您的帳戶已被暫停，請聯繫管理員"
                            elif user_status == 'expired':
                                error_message = "您的帳戶已過期，請續費後再試"
                            else:
                                error_message = f"帳戶狀態異常 ({user_status})，請聯繫管理員"

                            raise HTTPException(status_code=403, detail=error_message)

                        print(f"✅ 步驟4: 付費狀態檢查通過 - tenant_status=True, user_status={user_status}")

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
                        print(f"✅ 步驟5: 更新最後登入時間成功")

                        # 組織回傳資料
                        client_data = {
                            "client_id": result.client_id,
                            "client_name": result.client_name,
                            "plan_type": getattr(result, 'plan_type', 'basic'),
                            "user_status": user_status,
                            "tenant_status": tenant_status,  # 確定為 True
                            "max_users": getattr(result, 'max_users', 5),
                            "current_users": getattr(result, 'current_users', 0),
                            "available_slots": max(0, getattr(result, 'max_users', 5) - getattr(result, 'current_users', 0)),
                            "usage_percentage": round((getattr(result, 'current_users', 0) / getattr(result, 'max_users', 5)) * 100, 1) if getattr(result, 'max_users', 5) > 0 else 0,
                            "is_paid": True,  # 能到這裡一定是已付費
                            "subscription_status": "active",
                            "last_login": datetime.now().isoformat()
                        }

                        print(f"✅ 步驟6: 登入成功 - {result.client_name} (已確認付費)")

                        return {
                            "success": True,
                            "message": f"歡迎 {result.client_name}",
                            "client_data": client_data
                        }

                    except HTTPException:
                        # 重新拋出 HTTPException，保持原有的錯誤碼和訊息
                        raise
                    except Exception as e:
                        print(f"❌ 登入過程發生錯誤: {e}")
                        raise HTTPException(status_code=500, detail=f"登入過程發生錯誤: {str(e)}")
                    finally:
                        if db:
                            db.close()
                            print(f"✅ 步驟7: 資料庫連線已關閉")


                # 註冊路由
                app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
                print("✅ 完整認證路由載入成功")

            except Exception as e:
                print(f"❌ 認證路由載入失敗: {e}")

                # 如果還是有 MetaData 問題，提供最終備用方案
                if "already defined" in str(e):
                    print("🔧 檢測到 MetaData 重複定義問題，使用備用方案...")

                    # 清除 MetaData 並重新建立
                    try:
                        from sqlalchemy import MetaData
                        metadata = MetaData()
                        metadata.clear()
                        print("✅ MetaData 已清除")
                    except:
                        pass

                # 建立最基本的路由
                basic_router = APIRouter()

                @basic_router.get("/test")
                def basic_test():
                    return {"message": "基本認證API", "error": str(e)}

                app.include_router(basic_router, prefix="/api/auth", tags=["Basic Auth"])
                print("✅ 基本認證路由載入成功")

        else:
            print("❌ DATABASE_URL 未設定")

        # 註冊認證路由
        app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
        print("✅ 完整認證路由載入成功")

    except Exception as e:
        print(f"❌ 認證路由載入失敗: {e}")

        # 建立最基本的測試路由
        from fastapi import APIRouter
        basic_router = APIRouter()

        @basic_router.get("/test")
        def basic_test():
            return {
                "message": "基本認證 API",
                "status": "running",
                "database_error": str(e)
            }

        app.include_router(basic_router, prefix="/api/auth", tags=["Basic Auth"])
        print("✅ 基本認證路由載入成功")

else:
    print("❌ DATABASE_URL 未設定，建立最小化 API")

    # 建立最小化路由
    from fastapi import APIRouter
    minimal_router = APIRouter()

    @minimal_router.get("/test")
    def minimal_test():
        return {
            "message": "最小化認證 API",
            "status": "no_database",
            "note": "請設定 DATABASE_URL 環境變數"
        }

    app.include_router(minimal_router, prefix="/api/auth", tags=["Minimal Auth"])



@app.get("/health")
async def health_check():
    """健康檢查端點 - 增強版"""
    database_status = "connected" if DATABASE_URL else "not_configured"

    # 檢查案件資料庫表格
    case_db_status = "unknown"
    if DATABASE_URL:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # 檢查案件表格是否存在
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'case_records'
                    );
                """))
                if result.scalar():
                    case_db_status = "ready"
                else:
                    case_db_status = "tables_not_created"
        except Exception as e:
            case_db_status = f"error: {str(e)[:50]}"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": database_status,
        "case_database": case_db_status,
        "case_upload_api": CASE_UPLOAD_AVAILABLE,
        "environment": ENVIRONMENT,
        "version": "3.2.0"  # 更新版本號
    }

# 4. 新增案件API的系統資訊端點：
@app.get("/api/cases/system-info")
def case_system_info():
    """案件系統資訊端點"""
    try:
        if not DATABASE_URL:
            return {
                "error": "資料庫未配置",
                "case_upload_available": False
            }

        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # 統計資訊
            total_cases = db.execute(text("SELECT COUNT(*) FROM case_records WHERE is_deleted = false")).scalar()
            total_uploads = db.execute(text("SELECT COUNT(*) FROM upload_logs")).scalar()

            # 按類型統計
            case_types = db.execute(text("""
                SELECT case_type, COUNT(*) as count
                FROM case_records
                WHERE is_deleted = false
                GROUP BY case_type
            """)).fetchall()

            type_stats = {row[0]: row[1] for row in case_types}

            return {
                "system_status": "operational",
                "total_cases": total_cases,
                "total_uploads": total_uploads,
                "case_types": type_stats,
                "case_upload_available": CASE_UPLOAD_AVAILABLE,
                "database_connected": True,
                "timestamp": datetime.now().isoformat()
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "error": f"系統資訊查詢失敗: {str(e)}",
            "case_upload_available": False,
            "database_connected": False,
            "timestamp": datetime.now().isoformat()
        }

# 5. 更新根端點資訊：
@app.get("/")
async def root():
    """根端點 - 更新版"""
    return {
        "title": "法律案件管理系統 API",
        "version": "3.2.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "features": {
            "user_authentication": True,
            "case_upload": CASE_UPLOAD_AVAILABLE,
            "line_integration": True,
            "database_storage": bool(DATABASE_URL)
        },
        "endpoints": {
            "健康檢查": "/health",
            "認證系統": "/api/auth",
            "案件上傳": "/api/cases/upload" if CASE_UPLOAD_AVAILABLE else "不可用",
            "案件列表": "/api/cases/list/{client_id}" if CASE_UPLOAD_AVAILABLE else "不可用",
            "系統資訊": "/api/cases/system-info" if CASE_UPLOAD_AVAILABLE else "不可用",
            "API文件": "/docs"
        }
    }

# ==================== 額外的實用端點 ====================

@app.get("/api/system/info")
def system_info():
    """系統資訊端點"""
    return {
        "system": "法律案件管理系統",
        "version": "3.0.1",
        "python_version": sys.version,
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "heroku_app": os.getenv("HEROKU_APP_NAME", "unknown"),
        "database_configured": bool(os.getenv("DATABASE_URL")),
        "port": os.getenv("PORT", "unknown"),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/debug/env")
def debug_environment():
    """環境變數除錯端點 (僅顯示安全資訊)"""
    env_info = {}
    safe_vars = ["ENVIRONMENT", "HEROKU_APP_NAME", "PORT", "PYTHONPATH"]

    for var in safe_vars:
        env_info[var] = os.getenv(var, "not_set")

    # DATABASE_URL 特殊處理 (隱藏敏感資訊)
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        if '@' in database_url:
            env_info["DATABASE_URL"] = database_url.split('@')[0] + "@[HIDDEN]"
        else:
            env_info["DATABASE_URL"] = "[SET_BUT_HIDDEN]"
    else:
        env_info["DATABASE_URL"] = "not_set"

    return {
        "environment_variables": env_info,
        "timestamp": datetime.now().isoformat()
    }

# ==================== 錯誤處理 ====================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "端點不存在",
        "message": f"找不到路徑: {request.url.path}",
        "available_endpoints": [
            "/", "/health", "/api/auth/test", "/api/auth/client-login",
            "/api/system/info", "/docs"
        ] + (["/api/cases/upload"] if CASE_UPLOAD_AVAILABLE else []),
        "timestamp": datetime.now().isoformat()
    }

# ==================== 啟動配置 ====================

if __name__ == "__main__":
    import uvicorn

    print("🚀 啟動法律案件管理系統 API")
    print("=" * 60)
    print("📋 環境檢查:")
    print(f"  • DATABASE_URL: {'✅ 已設定' if DATABASE_URL else '❌ 未設定'}")
    print(f"  • CASE_UPLOAD: {'✅ 可用' if CASE_UPLOAD_AVAILABLE else '❌ 不可用'}")
    print(f"  • ENVIRONMENT: {ENVIRONMENT}")
    print("=" * 60)

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
