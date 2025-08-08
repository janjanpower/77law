#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
api/routes/line_webhook_routes.py
N8N LINE Webhook 整合端點 - 完整版
專門處理 LINE Bot 的 Webhook 事件和用戶綁定
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid
import hashlib
import time

# 導入資料庫相關
from api.database import get_control_db
from api.models_control import LoginUser, ClientLineUsers

# 導入服務層
try:
    from api.services.qr_binding_service import QRBindingService
except ImportError:
    from services.qr_binding_service import QRBindingService

router = APIRouter()

# 初始化服務
qr_binding_service = QRBindingService("https://law-controller.herokuapp.com")

# QR Code 快取 - 存儲綁定代碼和對應的事務所資訊
qr_code_cache = {}

# ==================== Pydantic 模型 ====================

class LineWebhookEvent(BaseModel):
    """LINE Webhook 事件模型"""
    type: str = Field(..., description="事件類型")
    source: Dict[str, Any] = Field(..., description="事件來源")
    timestamp: int = Field(..., description="事件時間戳")
    mode: str = Field(default="active", description="事件模式")

class LineMessageEvent(LineWebhookEvent):
    """LINE 訊息事件模型"""
    message: Dict[str, Any] = Field(..., description="訊息內容")
    replyToken: str = Field(..., description="回覆Token")

class LinePostbackEvent(LineWebhookEvent):
    """LINE Postback 事件模型"""
    postback: Dict[str, Any] = Field(..., description="Postback資料")
    replyToken: Optional[str] = Field(None, description="回覆Token")

class N8NLineWebhookRequest(BaseModel):
    """N8N LINE Webhook 請求模型"""
    destination: str = Field(..., description="目標ID")
    events: List[Dict[str, Any]] = Field(..., description="事件列表")

class LineUserBindingRequest(BaseModel):
    """LINE 用戶綁定請求模型"""
    line_user_id: str = Field(..., description="LINE 用戶ID")
    binding_code: str = Field(..., description="綁定代碼")
    display_name: Optional[str] = Field(None, description="用戶顯示名稱")

class LineBindingResponse(BaseModel):
    """LINE 綁定回應模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="回應訊息")
    client_info: Optional[Dict[str, Any]] = Field(None, description="事務所資訊")
    reply_token: Optional[str] = Field(None, description="LINE回覆Token")

class QRGenerateRequest(BaseModel):
    """QR Code生成請求"""
    client_id: str = Field(..., description="事務所客戶端ID")

class QRScanRequest(BaseModel):
    """QR Code掃描請求"""
    binding_code: str = Field(..., description="綁定代碼")
    line_user_id: str = Field(..., description="LINE用戶ID")
    user_display_name: Optional[str] = Field(None, description="用戶顯示名稱")

# ==================== QR Code 管理功能 ====================

def generate_binding_code(client_id: str) -> str:
    """生成唯一的綁定代碼"""
    timestamp = str(int(time.time()))
    unique_id = str(uuid.uuid4())[:8]
    raw_string = f"{client_id}_{timestamp}_{unique_id}"
    return hashlib.md5(raw_string.encode()).hexdigest()[:16]

def store_qr_code(binding_code: str, client_id: str, client_name: str, expiry_minutes: int = 10):
    """儲存QR Code資訊到快取"""
    expiry_time = datetime.now().timestamp() + (expiry_minutes * 60)
    qr_code_cache[binding_code] = {
        'client_id': client_id,
        'client_name': client_name,
        'created_at': datetime.now().timestamp(),
        'expiry_time': expiry_time,
        'used': False
    }

def validate_binding_code(binding_code: str) -> Optional[Dict[str, Any]]:
    """驗證綁定代碼是否有效"""
    if binding_code not in qr_code_cache:
        return None

    code_info = qr_code_cache[binding_code]
    current_time = datetime.now().timestamp()

    # 檢查是否過期
    if current_time > code_info['expiry_time']:
        del qr_code_cache[binding_code]
        return None

    # 檢查是否已使用
    if code_info['used']:
        return None

    return code_info

def cleanup_expired_codes():
    """清理過期的綁定代碼"""
    current_time = datetime.now().timestamp()
    expired_codes = []

    for code, info in qr_code_cache.items():
        if current_time > info['expiry_time']:
            expired_codes.append(code)

    for code in expired_codes:
        del qr_code_cache[code]

    return len(expired_codes)

# ==================== N8N Webhook 端點 ====================

@router.post("/n8n/line-webhook")
async def handle_n8n_line_webhook(
    request: Request,
    webhook_data: N8NLineWebhookRequest,
    db: Session = Depends(get_control_db)
):
    """
    處理來自 N8N 的 LINE Webhook 事件

    此端點接收 N8N 轉發的 LINE Webhook 事件，
    並根據事件類型進行相應處理
    """
    try:
        print(f"🔔 收到 N8N LINE Webhook: {len(webhook_data.events)} 個事件")

        responses = []

        for event_data in webhook_data.events:
            event_type = event_data.get('type')

            if event_type == 'message':
                # 處理訊息事件
                response = await _handle_message_event(event_data, db)
                responses.append(response)

            elif event_type == 'postback':
                # 處理 Postback 事件（QR Code掃描後的確認）
                response = await _handle_postback_event(event_data, db)
                responses.append(response)

            elif event_type == 'follow':
                # 處理用戶關注事件
                response = await _handle_follow_event(event_data, db)
                responses.append(response)

            elif event_type == 'unfollow':
                # 處理用戶取消關注事件
                response = await _handle_unfollow_event(event_data, db)
                responses.append(response)

            else:
                print(f"⚠️ 未處理的事件類型: {event_type}")
                responses.append({
                    "event_type": event_type,
                    "handled": False,
                    "message": f"未處理的事件類型: {event_type}"
                })

        return {
            "success": True,
            "processed_events": len(responses),
            "responses": responses,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ N8N LINE Webhook 處理失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook 處理失敗: {str(e)}"
        )

# ==================== 事件處理函數 ====================

async def _handle_message_event(event_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """處理 LINE 訊息事件"""
    try:
        user_id = event_data['source']['userId']
        message = event_data.get('message', {})
        message_text = message.get('text', '')
        reply_token = event_data.get('replyToken')

        print(f"📨 收到訊息: {user_id} - {message_text}")

        # 檢查用戶是否已綁定
        line_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == user_id,
            ClientLineUsers.is_active == True
        ).first()

        if line_user:
            # 用戶已綁定，正常處理訊息
            client = db.query(LoginUser).filter(
                LoginUser.client_id == line_user.client_id
            ).first()

            return {
                "event_type": "message",
                "handled": True,
                "user_status": "bound",
                "client_name": client.client_name if client else "未知",
                "client_id": line_user.client_id,
                "user_name": line_user.user_name,
                "message": "訊息已轉發處理",
                "reply_token": reply_token,
                "should_process": True  # N8N 可依此決定是否繼續處理
            }
        else:
            # 用戶未綁定，提示綁定流程
            return {
                "event_type": "message",
                "handled": True,
                "user_status": "unbound",
                "message": "用戶尚未綁定事務所",
                "reply_token": reply_token,
                "should_process": False,
                "suggested_reply": "您尚未綁定事務所，請聯繫您的事務所取得綁定QR Code完成註冊。"
            }

    except Exception as e:
        print(f"❌ 處理訊息事件失敗: {e}")
        return {
            "event_type": "message",
            "handled": False,
            "error": str(e)
        }

async def _handle_postback_event(event_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """處理 LINE Postback 事件（通常來自 QR Code 掃描）"""
    try:
        user_id = event_data['source']['userId']
        postback_data = event_data.get('postback', {}).get('data', '')
        reply_token = event_data.get('replyToken')

        print(f"📲 收到 Postback: {user_id} - {postback_data}")

        # 解析 Postback 資料，預期格式: "binding_code=XXXXXX"
        if postback_data.startswith('binding_code='):
            binding_code = postback_data.replace('binding_code=', '')

            # 執行綁定流程
            binding_result = await _process_user_binding(user_id, binding_code, db)

            return {
                "event_type": "postback",
                "handled": True,
                "binding_result": binding_result,
                "reply_token": reply_token
            }
        else:
            return {
                "event_type": "postback",
                "handled": False,
                "message": "無效的 Postback 資料格式",
                "reply_token": reply_token
            }

    except Exception as e:
        print(f"❌ 處理 Postback 事件失敗: {e}")
        return {
            "event_type": "postback",
            "handled": False,
            "error": str(e)
        }

async def _handle_follow_event(event_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """處理用戶關注事件"""
    try:
        user_id = event_data['source']['userId']
        reply_token = event_data.get('replyToken')

        print(f"👥 新用戶關注: {user_id}")

        # 檢查用戶是否已綁定
        existing_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == user_id
        ).first()

        welcome_message = "歡迎使用法律案件管理系統！"

        if existing_user:
            if existing_user.is_active:
                client = db.query(LoginUser).filter(
                    LoginUser.client_id == existing_user.client_id
                ).first()
                welcome_message += f"\n您已綁定到：{client.client_name if client else '未知事務所'}"
                welcome_message += "\n您可以開始使用系統功能了。"
            else:
                welcome_message += "\n您的帳戶已停用，請聯繫事務所重新啟用。"
        else:
            welcome_message += "\n請聯繫您的事務所取得綁定QR Code來完成註冊。"

        return {
            "event_type": "follow",
            "handled": True,
            "user_status": "bound" if existing_user and existing_user.is_active else "unbound",
            "welcome_message": welcome_message,
            "reply_token": reply_token,
            "suggested_reply": welcome_message
        }

    except Exception as e:
        print(f"❌ 處理關注事件失敗: {e}")
        return {
            "event_type": "follow",
            "handled": False,
            "error": str(e)
        }

async def _handle_unfollow_event(event_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """處理用戶取消關注事件"""
    try:
        user_id = event_data['source']['userId']

        print(f"👋 用戶取消關注: {user_id}")

        # 可以選擇是否要停用該用戶的綁定
        # 這裡只記錄事件，不主動停用綁定

        return {
            "event_type": "unfollow",
            "handled": True,
            "user_id": user_id,
            "message": "用戶已取消關注",
            "action": "logged_only"  # 僅記錄，未執行其他動作
        }

    except Exception as e:
        print(f"❌ 處理取消關注事件失敗: {e}")
        return {
            "event_type": "unfollow",
            "handled": False,
            "error": str(e)
        }

# ==================== QR Code 生成和管理端點 ====================

@router.post("/generate-qr-code")
def generate_qr_code(
    request: QRGenerateRequest,
    db: Session = Depends(get_control_db)
):
    """
    為事務所生成綁定QR Code

    此端點由QR綁定控制器調用，生成給LINE用戶掃描的QR Code
    """
    try:
        # 檢查事務所是否存在
        client = db.query(LoginUser).filter(
            LoginUser.client_id == request.client_id,
            LoginUser.is_active == True
        ).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該事務所"
            )

        # 檢查是否還有可綁定名額
        current_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == request.client_id,
            ClientLineUsers.is_active == True
        ).count()

        if current_users >= client.max_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"已達到方案上限（{current_users}/{client.max_users}）"
            )

        # 生成綁定代碼
        binding_code = generate_binding_code(request.client_id)

        # 存儲到快取
        store_qr_code(binding_code, request.client_id, client.client_name)

        # 生成QR Code URL
        qr_data_url = f"https://law-controller.herokuapp.com/api/line-webhook/qr-scan?code={binding_code}"

        # 使用現有的QR Code生成邏輯
        import qrcode
        import base64
        from io import BytesIO

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return {
            "success": True,
            "message": "QR Code 生成成功",
            "qr_info": {
                "binding_code": binding_code,
                "qr_data": qr_data_url,
                "qr_image_base64": f"data:image/png;base64,{img_base64}",
                "expiry_time": datetime.fromtimestamp(qr_code_cache[binding_code]['expiry_time']).isoformat(),
                "remaining_slots": client.max_users - current_users,
                "client_name": client.client_name
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 生成 QR Code 失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"QR Code 生成失敗: {str(e)}"
        )

@router.get("/qr-scan")
async def handle_qr_scan(
    code: str,
    db: Session = Depends(get_control_db)
):
    """
    處理QR Code掃描

    當用戶掃描QR Code時，LINE會重定向到此端點
    此端點會返回一個頁面，引導用戶完成綁定
    """
    try:
        # 驗證綁定代碼
        code_info = validate_binding_code(code)

        if not code_info:
            return {
                "success": False,
                "message": "QR Code 無效或已過期",
                "error_code": "INVALID_OR_EXPIRED"
            }

        # 返回綁定頁面資訊（實際應該返回HTML頁面）
        return {
            "success": True,
            "message": f"準備綁定到事務所：{code_info['client_name']}",
            "client_info": {
                "client_name": code_info['client_name'],
                "client_id": code_info['client_id']
            },
            "binding_code": code,
            "instructions": "請在LINE中確認綁定"
        }

    except Exception as e:
        print(f"❌ 處理QR Code掃描失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"QR Code 掃描處理失敗: {str(e)}"
        )

@router.post("/qr-scan-confirm")
async def confirm_qr_scan(
    request: QRScanRequest,
    db: Session = Depends(get_control_db)
):
    """
    確認QR Code掃描並執行綁定

    此端點由LINE Bot調用，確認用戶綁定
    """
    try:
        result = await _process_user_binding(
            request.line_user_id,
            request.binding_code,
            db,
            request.user_display_name
        )

        return result

    except Exception as e:
        print(f"❌ 確認QR Code掃描失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"掃描確認失敗: {str(e)}"
        )

# ==================== 用戶綁定邏輯 ====================

@router.post("/bind-line-user", response_model=LineBindingResponse)
def bind_line_user_to_client(
    binding_request: LineUserBindingRequest,
    db: Session = Depends(get_control_db)
):
    """
    綁定 LINE 用戶到事務所

    此端點專門處理來自 QR Code 掃描的綁定請求
    """
    try:
        import asyncio
        result = asyncio.run(_process_user_binding(
            binding_request.line_user_id,
            binding_request.binding_code,
            db,
            binding_request.display_name
        ))

        if result['success']:
            return LineBindingResponse(
                success=True,
                message=result['message'],
                client_info=result.get('client_info'),
                reply_token=result.get('reply_token')
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ LINE 用戶綁定失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"綁定過程發生錯誤: {str(e)}"
        )

async def _process_user_binding(
    line_user_id: str,
    binding_code: str,
    db: Session,
    display_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    處理用戶綁定邏輯

    Args:
        line_user_id: LINE 用戶ID
        binding_code: 綁定代碼
        db: 資料庫會話
        display_name: 用戶顯示名稱

    Returns:
        Dict: 綁定結果
    """
    try:
        # 檢查用戶是否已經綁定
        existing_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == line_user_id,
            ClientLineUsers.is_active == True
        ).first()

        if existing_user:
            client = db.query(LoginUser).filter(
                LoginUser.client_id == existing_user.client_id
            ).first()

            return {
                "success": False,
                "message": f"此LINE帳號已綁定到：{client.client_name if client else '未知事務所'}",
                "client_info": {
                    "client_id": existing_user.client_id,
                    "client_name": client.client_name if client else "未知事務所"
                }
            }

        # 驗證綁定代碼
        code_info = validate_binding_code(binding_code)

        if not code_info:
            return {
                "success": False,
                "message": "QR Code 無效或已過期"
            }

        client_id = code_info['client_id']
        client_name = code_info['client_name']

        # 檢查事務所是否存在
        client = db.query(LoginUser).filter(
            LoginUser.client_id == client_id,
            LoginUser.is_active == True
        ).first()

        if not client:
            return {
                "success": False,
                "message": "找不到對應的事務所"
            }

        # 檢查人數限制
        current_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client_id,
            ClientLineUsers.is_active == True
        ).count()

        if current_users >= client.max_users:
            return {
                "success": False,
                "message": f"事務所已達人數上限 ({current_users}/{client.max_users})"
            }

        # 創建綁定記錄
        new_line_user = ClientLineUsers(
            client_id=client_id,
            line_user_id=line_user_id,
            user_name=display_name or f"LINE用戶_{line_user_id[:8]}",
            bound_at=datetime.now(),
            is_active=True
        )

        db.add(new_line_user)

        # 更新事務所的當前用戶數
        client.current_users = current_users + 1

        # 標記綁定代碼為已使用
        qr_code_cache[binding_code]['used'] = True

        db.commit()

        print(f"✅ LINE用戶綁定成功: {line_user_id} -> {client.client_name}")

        return {
            "success": True,
            "message": f"成功綁定到事務所：{client.client_name}",
            "client_info": {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "current_users": current_users + 1,
                "max_users": client.max_users
            }
        }

    except Exception as e:
        print(f"❌ 用戶綁定處理失敗: {e}")
        db.rollback()
        return {
            "success": False,
            "message": f"綁定失敗: {str(e)}"
        }

# ==================== 查詢和管理端點 ====================

@router.get("/line-user-status/{user_id}")
def get_line_user_status(user_id: str, db: Session = Depends(get_control_db)):
    """查詢 LINE 用戶的綁定狀態"""
    try:
        line_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == user_id
        ).first()

        if not line_user:
            return {
                "user_id": user_id,
                "status": "unbound",
                "message": "用戶尚未綁定任何事務所"
            }

        client = db.query(LoginUser).filter(
            LoginUser.client_id == line_user.client_id
        ).first()

        return {
            "user_id": user_id,
            "status": "bound" if line_user.is_active else "inactive",
            "client_info": {
                "client_id": line_user.client_id,
                "client_name": client.client_name if client else "未知事務所",
                "bound_at": line_user.bound_at.isoformat(),
                "user_name": line_user.user_name
            } if line_user.is_active else None,
            "message": f"已綁定到：{client.client_name}" if line_user.is_active else "帳戶已停用"
        }

    except Exception as e:
        print(f"❌ 查詢 LINE 用戶狀態失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢失敗: {str(e)}"
        )

@router.get("/client-binding-status/{client_id}")
def get_client_binding_status(client_id: str, db: Session = Depends(get_control_db)):
    """查詢事務所的綁定狀態和用戶列表"""
    try:
        # 檢查事務所是否存在
        client = db.query(LoginUser).filter(
            LoginUser.client_id == client_id,
            LoginUser.is_active == True
        ).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該事務所"
            )

        # 查詢綁定的LINE用戶
        line_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client_id,
            ClientLineUsers.is_active == True
        ).all()

        return {
            "client_info": {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "plan_type": client.plan_type,
                "max_users": client.max_users,
                "current_users": len(line_users)
            },
            "line_users": [
                {
                    "line_user_id": user.line_user_id,
                    "user_name": user.user_name,
                    "bound_at": user.bound_at.isoformat()
                }
                for user in line_users
            ],
            "available_slots": client.max_users - len(line_users),
            "usage_percentage": round((len(line_users) / client.max_users) * 100, 1) if client.max_users > 0 else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢事務所綁定狀態失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢失敗: {str(e)}"
        )

@router.delete("/unbind-line-user/{user_id}")
def unbind_line_user(user_id: str, db: Session = Depends(get_control_db)):
    """解除 LINE 用戶綁定（管理員功能）"""
    try:
        line_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == user_id,
            ClientLineUsers.is_active == True
        ).first()

        if not line_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該用戶的綁定記錄"
            )

        # 停用綁定記錄
        line_user.is_active = False

        # 更新事務所用戶數
        client = db.query(LoginUser).filter(
            LoginUser.client_id == line_user.client_id
        ).first()

        if client and client.current_users > 0:
            client.current_users -= 1

        db.commit()

        print(f"✅ LINE用戶解除綁定: {user_id}")

        return {
            "success": True,
            "message": "用戶綁定已解除",
            "user_id": user_id,
            "client_info": {
                "client_id": line_user.client_id,
                "client_name": client.client_name if client else "未知事務所",
                "updated_user_count": client.current_users if client else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 解除 LINE 用戶綁定失敗: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解除綁定失敗: {str(e)}"
        )

@router.post("/reactivate-line-user/{user_id}")
def reactivate_line_user(user_id: str, db: Session = Depends(get_control_db)):
    """重新啟用 LINE 用戶綁定"""
    try:
        line_user = db.query(ClientLineUsers).filter(
            ClientLineUsers.line_user_id == user_id,
            ClientLineUsers.is_active == False
        ).first()

        if not line_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該用戶的停用記錄"
            )

        # 檢查事務所人數限制
        client = db.query(LoginUser).filter(
            LoginUser.client_id == line_user.client_id
        ).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到對應的事務所"
            )

        current_active_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == line_user.client_id,
            ClientLineUsers.is_active == True
        ).count()

        if current_active_users >= client.max_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"事務所已達人數上限 ({current_active_users}/{client.max_users})"
            )

        # 重新啟用用戶
        line_user.is_active = True
        line_user.bound_at = datetime.now()  # 更新綁定時間

        # 更新事務所用戶數
        client.current_users = current_active_users + 1

        db.commit()

        print(f"✅ LINE用戶重新啟用: {user_id}")

        return {
            "success": True,
            "message": f"用戶已重新啟用並綁定到：{client.client_name}",
            "user_id": user_id,
            "client_info": {
                "client_id": line_user.client_id,
                "client_name": client.client_name,
                "updated_user_count": client.current_users
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 重新啟用 LINE 用戶失敗: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新啟用失敗: {str(e)}"
        )

# ==================== 系統維護和管理端點 ====================

@router.post("/cleanup-expired-qr")
def cleanup_expired_qr_codes():
    """
    清理過期的 QR Code（系統維護用）

    建議定期呼叫此端點清理過期的 QR Code
    """
    try:
        cleaned_count = cleanup_expired_codes()

        return {
            "success": True,
            "message": f"已清理 {cleaned_count} 個過期的 QR Code",
            "cleaned_count": cleaned_count,
            "remaining_codes": len(qr_code_cache),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ 清理過期 QR Code 錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理失敗: {str(e)}"
        )

@router.get("/qr-cache-status")
def get_qr_cache_status():
    """查看當前QR Code快取狀態（偵錯用）"""
    try:
        current_time = datetime.now().timestamp()
        active_codes = []
        expired_codes = []

        for code, info in qr_code_cache.items():
            code_status = {
                "binding_code": code[:8] + "...",  # 只顯示部分代碼保護隱私
                "client_name": info['client_name'],
                "created_at": datetime.fromtimestamp(info['created_at']).isoformat(),
                "expiry_time": datetime.fromtimestamp(info['expiry_time']).isoformat(),
                "used": info['used']
            }

            if current_time > info['expiry_time']:
                expired_codes.append(code_status)
            else:
                active_codes.append(code_status)

        return {
            "total_codes": len(qr_code_cache),
            "active_codes": len(active_codes),
            "expired_codes": len(expired_codes),
            "active_code_list": active_codes,
            "expired_code_list": expired_codes,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ 查看QR Code快取狀態失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢失敗: {str(e)}"
        )

@router.get("/system-stats")
def get_system_stats(db: Session = Depends(get_control_db)):
    """取得系統統計資訊"""
    try:
        # 事務所統計
        total_clients = db.query(LoginUser).filter(LoginUser.is_active == True).count()

        # LINE用戶統計
        total_line_users = db.query(ClientLineUsers).filter(ClientLineUsers.is_active == True).count()
        inactive_line_users = db.query(ClientLineUsers).filter(ClientLineUsers.is_active == False).count()

        # 方案統計
        from sqlalchemy import func
        plan_stats = db.query(
            LoginUser.plan_type,
            func.count(LoginUser.id).label('count')
        ).filter(
            LoginUser.is_active == True
        ).group_by(LoginUser.plan_type).all()

        plan_distribution = {plan: count for plan, count in plan_stats}

        # 使用率統計
        capacity_usage = db.query(
            func.sum(LoginUser.current_users).label('used'),
            func.sum(LoginUser.max_users).label('total')
        ).filter(LoginUser.is_active == True).first()

        return {
            "client_stats": {
                "total_active_clients": total_clients,
                "plan_distribution": plan_distribution
            },
            "line_user_stats": {
                "total_active_users": total_line_users,
                "total_inactive_users": inactive_line_users,
                "total_users": total_line_users + inactive_line_users
            },
            "capacity_stats": {
                "used_slots": capacity_usage.used or 0,
                "total_slots": capacity_usage.total or 0,
                "utilization_rate": round((capacity_usage.used / capacity_usage.total) * 100, 1) if capacity_usage.total and capacity_usage.used else 0
            },
            "qr_cache_stats": {
                "active_qr_codes": len(qr_code_cache),
                "cache_memory_usage": len(str(qr_code_cache))  # 簡單的記憶體使用估算
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ 取得系統統計失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計查詢失敗: {str(e)}"
        )

# ==================== 批量操作端點 ====================

@router.post("/batch-unbind-users")
def batch_unbind_users(
    user_ids: List[str],
    db: Session = Depends(get_control_db)
):
    """批量解除用戶綁定"""
    try:
        results = []

        for user_id in user_ids:
            try:
                line_user = db.query(ClientLineUsers).filter(
                    ClientLineUsers.line_user_id == user_id,
                    ClientLineUsers.is_active == True
                ).first()

                if line_user:
                    # 停用用戶
                    line_user.is_active = False

                    # 更新事務所用戶數
                    client = db.query(LoginUser).filter(
                        LoginUser.client_id == line_user.client_id
                    ).first()

                    if client and client.current_users > 0:
                        client.current_users -= 1

                    results.append({
                        "user_id": user_id,
                        "success": True,
                        "message": f"已解除綁定：{client.client_name if client else '未知事務所'}"
                    })
                else:
                    results.append({
                        "user_id": user_id,
                        "success": False,
                        "message": "找不到該用戶的綁定記錄"
                    })

            except Exception as e:
                results.append({
                    "user_id": user_id,
                    "success": False,
                    "message": f"處理失敗: {str(e)}"
                })

        db.commit()

        successful_count = sum(1 for r in results if r['success'])

        return {
            "success": True,
            "message": f"批量操作完成，成功處理 {successful_count}/{len(user_ids)} 個用戶",
            "results": results,
            "summary": {
                "total_requested": len(user_ids),
                "successful": successful_count,
                "failed": len(user_ids) - successful_count
            }
        }

    except Exception as e:
        print(f"❌ 批量解除用戶綁定失敗: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量操作失敗: {str(e)}"
        )

@router.get("/client-users-export/{client_id}")
def export_client_users(client_id: str, db: Session = Depends(get_control_db)):
    """匯出事務所的所有用戶資料（CSV格式）"""
    try:
        # 檢查事務所
        client = db.query(LoginUser).filter(
            LoginUser.client_id == client_id
        ).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到該事務所"
            )

        # 查詢所有用戶（包括停用的）
        line_users = db.query(ClientLineUsers).filter(
            ClientLineUsers.client_id == client_id
        ).all()

        # 格式化為CSV資料
        csv_data = []
        csv_data.append(["LINE用戶ID", "用戶名稱", "綁定時間", "狀態", "事務所名稱"])

        for user in line_users:
            csv_data.append([
                user.line_user_id,
                user.user_name or "未設定",
                user.bound_at.strftime("%Y-%m-%d %H:%M:%S"),
                "啟用" if user.is_active else "停用",
                client.client_name
            ])

        return {
            "success": True,
            "client_info": {
                "client_id": client.client_id,
                "client_name": client.client_name
            },
            "csv_data": csv_data,
            "total_users": len(line_users),
            "active_users": sum(1 for u in line_users if u.is_active),
            "export_time": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 匯出事務所用戶資料失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"匯出失敗: {str(e)}"
        )

# ==================== 健康檢查端點 ====================

@router.get("/health")
def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "LINE Webhook Integration",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "cache_status": {
            "active_qr_codes": len(qr_code_cache)
        }
    }

# ==================== 初始化和清理任務 ====================

import atexit
import threading
import time

def periodic_cleanup():
    """定期清理過期的QR Code"""
    while True:
        try:
            cleaned = cleanup_expired_codes()
            if cleaned > 0:
                print(f"🧹 定期清理：移除了 {cleaned} 個過期的QR Code")
        except Exception as e:
            print(f"❌ 定期清理失敗: {e}")

        # 每5分鐘執行一次清理
        time.sleep(300)

# 啟動背景清理任務
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

# 程式結束時的清理工作
def cleanup_on_exit():
    """程式結束時清理資源"""
    print("🔧 清理 LINE Webhook 資源...")
    qr_code_cache.clear()
    print("✅ LINE Webhook 資源清理完成")

atexit.register(cleanup_on_exit)

print("🚀 LINE Webhook 整合端點載入完成")
print(f"📋 已註冊 {len(router.routes)} 個端點")