# api/routes/case_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from datetime import datetime

from api.database import get_db
from api.models_control import ClientLineUsers, LoginUser, get_tenant_engine

router = APIRouter(prefix="/api", tags=["cases"])

# ---- helpers ---------------------------------------------------------------

def _ensure_lawyer(db: Session, line_user_id: str) -> str:
    """回傳該 LINE 使用者的 client_id；若不是律師則 403。"""
    clu = db.query(ClientLineUsers).filter(
        ClientLineUsers.line_user_id == line_user_id
    ).first()
    if not clu:
        raise HTTPException(403, detail="not bound to any firm")
    role = (getattr(clu, "role", "") or "").lower()
    is_lawyer = bool(getattr(clu, "is_lawyer", False) or role in ("lawyer", "attorney", "律師"))
    if not is_lawyer:
        raise HTTPException(403, detail="not a lawyer")
    client_id = getattr(clu, "client_id", None)
    if not client_id:
        raise HTTPException(400, detail="client_id missing")
    return str(client_id)

def _get_tenant_db_url(db: Session, client_id: str) -> str:
    rec = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
    url = getattr(rec, "tenant_db_url", None) if rec else None
    if not url:
        raise HTTPException(404, detail="tenant_db_url not found")
    # Heroku 可能是 postgres:// 要轉 sqlalchemy 可用
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url

def _extract_case_no(text_msg: str) -> Optional[str]:
    """從訊息中抓出案件編號：支援『查案 123』或文字裡第一個連續英數字串。"""
    if not text_msg:
        return None
    import re
    m = re.search(r"查案\s*([A-Za-z0-9\-_/]+)", text_msg)
    if m:
        return m.group(1)
    m = re.search(r"([A-Za-z0-9]{4,})", text_msg)
    return m.group(1) if m else None

def _row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row._mapping)
    except Exception:
        return dict(row)

def _format_dt(v: Any) -> str:
    if isinstance(v, (datetime, )):
        return v.strftime("%Y-%m-%d %H:%M")
    return str(v)

def _find_case(engine, case_no: str) -> Dict[str, Any]:
    """偵測 case_records 的欄位，優先用 case_no/case_number/case_id 其一查資料。"""
    with engine.begin() as conn:
        cols = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='case_records'
        """)).fetchall()
        colnames = [c[0].lower() for c in cols]
        # 找可用的案號欄位
        candidates = [c for c in ["case_no", "case_number", "caseid", "case_id"] if c in colnames]
        if not candidates:
            # 退而求其次，直接撈一列
            row = conn.execute(text("SELECT * FROM case_records LIMIT 1")).first()
            return _row_to_dict(row) if row else {}
        key = candidates[0]
        row = conn.execute(text(f"SELECT * FROM case_records WHERE {key} = :v LIMIT 1"), {"v": case_no}).first()
        return _row_to_dict(row) if row else {}

def _compose_message(d: Dict[str, Any], case_no: str) -> str:
    if not d:
        return f"找不到編號「{case_no}」的案件。"
    # 嘗試取一些常見欄位
    lower = {k.lower(): v for k, v in d.items()}
    parts = []
    def add(label, key):
        if key in lower and lower[key] not in (None, ""):
            parts.append(f"{label}：{_format_dt(lower[key])}")
    # 顯示順序
    parts.append(f"案件編號：{case_no}")
    add("案件名稱", "title")
    add("當事人", "party_name")
    add("狀態", "status")
    add("承辦人", "handler")
    add("更新時間", "updated_at")
    add("建立時間", "created_at")
    # 最多取 6~7 個欄位，避免訊息過長
    return "\n".join(parts[:7])

# ---- route ----------------------------------------------------------------

@router.post("/lawyer/case-search")
async def lawyer_case_search(req: Request, db: Session = Depends(get_db)):
    payload = await req.json()
    text_msg = (payload.get("text") or "").strip()
    line_user_id = payload.get("line_user_id") or payload.get("user_id")

    if not line_user_id:
        raise HTTPException(400, detail="line_user_id required")

    case_no = _extract_case_no(text_msg)
    if not case_no:
        return {"ok": False, "message": "請輸入格式：查案 <案件編號>，例如：查案 114001"}

    # 驗證律師 & 找到 tenant
    client_id = _ensure_lawyer(db, line_user_id)
    tenant_db_url = _get_tenant_db_url(db, client_id)
    engine = get_tenant_engine(client_id, tenant_db_url)

    # 查資料
    row_dict = _find_case(engine, case_no)
    message = _compose_message(row_dict, case_no)

    return {"ok": True, "message": message, "case": row_dict, "case_no": case_no}
