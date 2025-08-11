# api/routes/line_routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from sqlalchemy.orm import Session

from api.database import get_db
from api.models_control import ClientLineUsers  # 需要時可用來補充 client_name 等

line_router = APIRouter(prefix="/api/line", tags=["line"])

# --- 你現有邏輯：請改成實際 import 的服務函式 ---
# 建議把 /api/lawyer/verify-secret 的核心邏輯抽成函式，這裡直接呼叫，不再繞 HTTP。
# 這裡先示範一個介面，請替換成你的實作。
def verify_secret_core(db: Session, line_user_id: str, text: str) -> dict:
    """
    回傳格式示例：
    {
      "success": True/False,          # 是否通過「暗號」檢測
      "is_lawyer": True/False,        # 是否為律師
      "client_name": "XXX"            # 可選
    }
    """
    # TODO: 直接重用你 /api/lawyer/verify-secret 的實作（抽成 service 後在此呼叫）
    raise NotImplementedError("請將 verify-secret 的判定抽成函式後在此呼叫")

# --- 入參 / 出參 ---
class ResolveRouteIn(BaseModel):
    line_user_id: str
    text: Optional[str] = ""

class ResolveRouteOut(BaseModel):
    route: Literal["LAWYER", "LOGIN", "USER"]
    success: bool
    is_lawyer: bool
    client_name: Optional[str] = None

@line_router.post("/resolve-route", response_model=ResolveRouteOut)
def resolve_route(payload: ResolveRouteIn, db: Session = Depends(get_db)):
    line_user_id = (payload.line_user_id or "").strip()
    if not line_user_id:
        raise HTTPException(status_code=400, detail="line_user_id required")

    text = (payload.text or "").strip()

    # 1) 呼叫你既有的「檢測暗號 + 是否律師」核心邏輯
    #    （把 /api/lawyer/verify-secret 的內文抽成 verify_secret_core 後直接呼叫）
    res = verify_secret_core(db, line_user_id=line_user_id, text=text)
    success = bool(res.get("success"))
    is_lawyer = bool(res.get("is_lawyer"))
    client_name = res.get("client_name")

    # 2) 依規則決定 route
    if success and is_lawyer:
        route = "LAWYER"
    elif success and not is_lawyer:
        route = "LOGIN"
    else:
        route = "USER"

    return ResolveRouteOut(
        route=route,
        success=success,
        is_lawyer=is_lawyer,
        client_name=client_name,
    )
