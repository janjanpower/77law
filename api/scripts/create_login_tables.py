# 🗄️ 資料庫設定和測試資料建立

# ==================== 1. 建立資料庫遷移腳本 ====================
# scripts/create_login_tables.py

"""
在您的API專案中執行此腳本來建立資料表
"""

import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 設定資料庫連線 (請根據您的實際設定調整)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_law_system.db")

# 如果是PostgreSQL，修正連線字串
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

Base = declarative_base()

class ClientLineUsers(Base):
    """LINE用戶綁定表"""
    __tablename__ = "client_line_users"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, nullable=False)
    line_user_id = Column(String, nullable=False, unique=True)
    user_name = Column(String, nullable=True)
    bound_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

def create_tables_and_test_data():
    """建立資料表並插入測試資料"""
    try:
        # 建立引擎和連線
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        print("🔧 建立資料表...")
        Base.metadata.create_all(bind=engine)
        print("✅ 資料表建立完成")

        # 建立會話
        db = SessionLocal()

        try:
            # 檢查是否已有測試資料
            existing_data = db.query(LoginUser).filter(LoginUser.client_id == "law_firm_001").first()
            if existing_data:
                print("⚠️ 測試資料已存在，跳過插入")
                return

            print("📝 插入測試資料...")

            # 🔥 插入測試事務所資料
            test_clients = [
                LoginUser(
                    client_name="不專業法律事務所",
                    client_id="law_firm_001",
                    password="123456",
                    is_active=True,
                    plan_type="basic_5",
                    user_status="active",
                    max_users=5,
                    current_users=0
                ),
                LoginUser(
                    client_name="專業法律事務所",
                    client_id="law_firm_002",
                    password="789012",
                    is_active=True,
                    plan_type="standard_10",
                    user_status="active",
                    max_users=10,
                    current_users=0
                ),
                LoginUser(
                    client_name="系統管理員",
                    client_id="admin",
                    password="admin123",
                    is_active=True,
                    plan_type="enterprise_50",
                    user_status="active",
                    max_users=999,
                    current_users=1
                )
            ]

            for client in test_clients:
                db.add(client)

            # 🔥 可選：插入一些測試LINE用戶 (模擬已綁定的情況)
            test_line_users = [
                ClientLineUsers(
                    client_id="law_firm_002",
                    line_user_id="U1234567890abcdef1234567890abcdef",
                    user_name="測試用戶1",
                    is_active=True
                ),
                ClientLineUsers(
                    client_id="law_firm_002",
                    line_user_id="U9876543210fedcba9876543210fedcba",
                    user_name="測試用戶2",
                    is_active=True
                )
            ]

            for line_user in test_line_users:
                db.add(line_user)

            # 更新專業法律事務所的current_users
            professional_firm = db.query(LoginUser).filter(LoginUser.client_id == "law_firm_002").first()
            if professional_firm:
                professional_firm.current_users = 2

            db.commit()
            print("✅ 測試資料插入完成")

            # 顯示插入的資料
            print("\n📊 測試資料清單:")
            clients = db.query(LoginUser).all()
            for client in clients:
                print(f"  - {client.client_name} (ID: {client.client_id}) - {client.current_users}/{client.max_users} 用戶")

        except Exception as e:
            db.rollback()
            print(f"❌ 插入測試資料失敗: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        print(f"❌ 資料庫設定失敗: {e}")
        raise

if __name__ == "__main__":
    print("🚀 開始設定登入系統資料庫...")
    create_tables_and_test_data()
    print("🎉 資料庫設定完成！")


# ==================== 2. API端點實作 ====================
# api/routes/auth_routes.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
import os
from datetime import datetime

# 您需要根據實際專案結構調整import路徑
from api.database import get_db  # 或您的資料庫會話函數
from api.models_control import LoginUser, ClientLineUsers  # 或您的模型位置

router = APIRouter()

class ClientLoginRequest(BaseModel):
    client_id: str
    password: str

class ClientLoginResponse(BaseModel):
    success: bool
    message: str
    client_data: Dict[str, Any] = {}

@router.post("/client-login", response_model=ClientLoginResponse)
def client_login(request: ClientLoginRequest, db: Session = Depends(get_db)):
    """客戶端登入驗證端點"""
    try:
        print(f"🔍 收到登入請求: client_id={request.client_id}")

        # 查詢客戶端資料
        client = db.query(LoginUser).filter(
            LoginUser.client_id == request.client_id,
            LoginUser.password == request.password,
            LoginUser.is_active == True
        ).first()

        if not client:
            print(f"❌ 登入失敗: 找不到匹配的客戶端")
            raise HTTPException(status_code=401, detail="客戶端ID或密碼錯誤")

        # 更新最後登入時間
        client.last_login = datetime.now()

        # 計算實際LINE用戶數
        actual_line_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == request.client_id,
            ClientLineUsers.is_active == True
        ).count()

        # 更新current_users
        client.current_users = actual_line_users

        db.commit()

        # 準備回應資料
        client_data = {
            'id': client.id,
            'client_name': client.client_name,
            'client_id': client.client_id,
            'plan_type': client.plan_type,
            'user_status': client.user_status,
            'current_users': client.current_users,
            'max_users': client.max_users,
            'usage_display': f"{client.current_users}/{client.max_users}",
            'available_slots': max(0, client.max_users - client.current_users),
            'is_full': client.current_users >= client.max_users
        }

        print(f"✅ 登入成功: {client.client_name}")

        return ClientLoginResponse(
            success=True,
            message=f"歡迎 {client.client_name}",
            client_data=client_data
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 登入API錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"登入過程發生錯誤: {str(e)}")

@router.get("/client-status/{client_id}")
def get_client_status(client_id: str, db: Session = Depends(get_db)):
    """取得客戶端狀態"""
    try:
        client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="事務所不存在")

        # 更新實際用戶數
        actual_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client_id,
            ClientLineUsers.is_active == True
        ).count()

        client.current_users = actual_users
        db.commit()

        return {
            "success": True,
            "data": {
                "client_name": client.client_name,
                "current_users": client.current_users,
                "max_users": client.max_users,
                "usage_display": f"{client.current_users}/{client.max_users}",
                "plan_type": client.plan_type,
                "is_full": client.current_users >= client.max_users
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 3. 在main.py中註冊路由 ====================
# api/main.py (添加以下內容)

"""
在您的FastAPI main.py中添加：

from api.routes.auth_routes import router as auth_router

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
"""

# ==================== 4. 測試腳本 ====================
# test_login_api.py

import requests
import json

def test_login_api(api_base_url="http://localhost:8000"):
    """測試登入API"""
    print("🧪 開始測試登入API...")

    # 測試資料
    test_cases = [
        {
            "name": "不專業法律事務所",
            "client_id": "law_firm_001",
            "password": "123456",
            "should_success": True
        },
        {
            "name": "專業法律事務所",
            "client_id": "law_firm_002",
            "password": "789012",
            "should_success": True
        },
        {
            "name": "系統管理員",
            "client_id": "admin",
            "password": "admin123",
            "should_success": True
        },
        {
            "name": "錯誤密碼測試",
            "client_id": "law_firm_001",
            "password": "wrong_password",
            "should_success": False
        }
    ]

    for test_case in test_cases:
        print(f"\n🔍 測試: {test_case['name']}")

        try:
            response = requests.post(
                f"{api_base_url}/api/auth/client-login",
                json={
                    "client_id": test_case["client_id"],
                    "password": test_case["password"]
                },
                timeout=10
            )

            print(f"   狀態碼: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 成功: {data['message']}")
                if 'client_data' in data:
                    client_data = data['client_data']
                    print(f"   📊 {client_data['client_name']} - 用戶數: {client_data['usage_display']}")
            else:
                if test_case["should_success"]:
                    print(f"   ❌ 預期成功但失敗: {response.text}")
                else:
                    print(f"   ✅ 預期失敗且確實失敗: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ 連線錯誤: {e}")

if __name__ == "__main__":
    # 請根據您的API服務位址調整
    API_URL = "http://localhost:8000"  # 或您的實際API位址
    test_login_api(API_URL)


# ==================== 5. 執行步驟說明 ====================
"""
🔧 執行步驟：

1. 建立資料表和測試資料：
   python scripts/create_login_tables.py

2. 確認API路由已註冊：
   在 api/main.py 中添加 auth_routes

3. 啟動API服務：
   python api/main.py
   或
   uvicorn api.main:app --host 0.0.0.0 --port 8000

4. 測試API：
   python test_login_api.py

5. 測試本地登入：
   python main.py (您的桌面應用程式)

🎯 測試帳號：
- 不專業法律事務所 / 123456
- 專業法律事務所 / 789012
- admin / admin123
"""