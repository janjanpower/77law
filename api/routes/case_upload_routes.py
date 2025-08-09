# -*- coding: utf-8 -*-
"""
api/routes/case_upload_routes.py
雙寫版：實體欄位 + data(JSONB)
- 支援 JSON / form-data / x-www-form-urlencoded
- 三個 progress_* 欄位字串也會自動解析為物件
"""

from typing import Optional, Dict, Any, List
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam

try:
    from api.database import get_db
except ImportError:
    from database import get_db

router = APIRouter(prefix="/api/cases", tags=["cases"])

# ---------- 預設鍵：保留空鍵 ----------
DEFAULT_KEYS: Dict[str, Any] = {
    "title": "",
    "case_type": "",
    "plaintiff": "",
    "defendant": "",
    "lawyer": "",
    "legal_affairs": "",
    "progress": "",
    "case_reason": "",
    "case_number": "",
    "opposing_party": "",
    "court": "",
    "division": "",
    "progress_date": "",
    "progress_stages": {},   # JSON 物件
    "progress_notes": {},    # JSON 物件
    "progress_times": {}     # JSON 物件
}

def ensure_dict(v: Any) -> Dict[str, Any]:
    if isinstance(v, dict):
        return v
    if v is None or v == "":
        return {}
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return {}

def with_defaults(user_data: Dict[str, Any]) -> Dict[str, Any]:
    data = DEFAULT_KEYS.copy()
    data.update(user_data or {})
    for k in ("progress_stages", "progress_notes", "progress_times"):
        data[k] = ensure_dict(data.get(k))
    return data

def is_empty_value(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (dict, list, tuple, set)):
        return len(v) == 0
    return False

# ---------- Pydantic（僅用於結構提示） ----------
class CaseUploadPayload(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=50)
    case_id: str = Field(..., min_length=1, max_length=50)
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    @validator("data", pre=True)
    def _coerce_data(cls, v):
        return ensure_dict(v)

# ---------- 雙寫 UPSERT（同時寫欄位 + data JSONB） ----------
UPSERT_SQL = text("""
    INSERT INTO case_records (
        client_id, case_id, data,
        title, case_type, plaintiff, defendant, lawyer, legal_affairs,
        progress, case_reason, case_number, opposing_party, court, division,
        progress_date, progress_stages, progress_notes, progress_times
    )
    VALUES (
        :client_id, :case_id, CAST(:data AS JSONB),
        :title, :case_type, :plaintiff, :defendant, :lawyer, :legal_affairs,
        :progress, :case_reason, :case_number, :opposing_party, :court, :division,
        :progress_date, CAST(:progress_stages AS JSONB), CAST(:progress_notes AS JSONB), CAST(:progress_times AS JSONB)
    )
    ON CONFLICT (client_id, case_id)
    DO UPDATE SET
        data = COALESCE(case_records.data, '{}'::jsonb) || EXCLUDED.data,
        title = EXCLUDED.title,
        case_type = EXCLUDED.case_type,
        plaintiff = EXCLUDED.plaintiff,
        defendant = EXCLUDED.defendant,
        lawyer = EXCLUDED.lawyer,
        legal_affairs = EXCLUDED.legal_affairs,
        progress = EXCLUDED.progress,
        case_reason = EXCLUDED.case_reason,
        case_number = EXCLUDED.case_number,
        opposing_party = EXCLUDED.opposing_party,
        court = EXCLUDED.court,
        division = EXCLUDED.division,
        progress_date = EXCLUDED.progress_date,
        progress_stages = EXCLUDED.progress_stages,
        progress_notes = EXCLUDED.progress_notes,
        progress_times = EXCLUDED.progress_times,
        updated_at = now()
    RETURNING id;
""").bindparams(
    bindparam("client_id"),
    bindparam("case_id"),
    bindparam("data"),
    bindparam("title"),
    bindparam("case_type"),
    bindparam("plaintiff"),
    bindparam("defendant"),
    bindparam("lawyer"),
    bindparam("legal_affairs"),
    bindparam("progress"),
    bindparam("case_reason"),
    bindparam("case_number"),
    bindparam("opposing_party"),
    bindparam("court"),
    bindparam("division"),
    bindparam("progress_date"),
    bindparam("progress_stages"),
    bindparam("progress_notes"),
    bindparam("progress_times"),
)

GET_ONE_SQL = text("""
    SELECT data
    FROM case_records
    WHERE client_id=:client_id AND case_id=:case_id
    LIMIT 1
""")

# ---------- 路由 ----------
@router.post("/upload")
async def upload_case(request: Request, db: Session = Depends(get_db)):
    """
    建立/更新一筆案件（雙寫）：
    - 寫入各實體欄位 + data(JSONB)
    - 保留空鍵，三個 progress_* 自動轉物件
    """
    # 1) 嘗試讀 JSON
    payload: Dict[str, Any] = {}
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    # 2) 若不是 JSON，吃表單
    if not payload:
        form = await request.form()
        payload = dict(form)

    # 3) 取欄位 & 檢查
    client_id = (payload.get("client_id") or "").strip()
    case_id = (payload.get("case_id") or "").strip()
    if not client_id or not case_id:
        raise HTTPException(status_code=400, detail="client_id 與 case_id 為必填且不可為空字串")

    raw_data = payload.get("data", {})
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except Exception:
            raise HTTPException(status_code=400, detail="data 必須是 JSON 物件或可被解析的 JSON 字串")
    if not isinstance(raw_data, dict):
        raise HTTPException(status_code=400, detail="data 必須是 JSON 物件")

    # 4) 標準化資料（保留空鍵 + 三欄轉 dict）
    data_obj = with_defaults(ensure_dict(raw_data))

    # 5) 準備雙寫參數
    params = {
        "client_id": client_id,
        "case_id": case_id,
        "data": json.dumps(data_obj, ensure_ascii=False),

        "title": data_obj.get("title", ""),
        "case_type": data_obj.get("case_type", ""),
        "plaintiff": data_obj.get("plaintiff", ""),
        "defendant": data_obj.get("defendant", ""),
        "lawyer": data_obj.get("lawyer", ""),
        "legal_affairs": data_obj.get("legal_affairs", ""),
        "progress": data_obj.get("progress", ""),
        "case_reason": data_obj.get("case_reason", ""),
        "case_number": data_obj.get("case_number", ""),
        "opposing_party": data_obj.get("opposing_party", ""),
        "court": data_obj.get("court", ""),
        "division": data_obj.get("division", ""),
        "progress_date": data_obj.get("progress_date", ""),
        "progress_stages": json.dumps(data_obj.get("progress_stages", {}), ensure_ascii=False),
        "progress_notes": json.dumps(data_obj.get("progress_notes", {}), ensure_ascii=False),
        "progress_times": json.dumps(data_obj.get("progress_times", {}), ensure_ascii=False),
    }

    # 6) 寫入（雙寫 upsert）
    try:
        row = db.execute(UPSERT_SQL, params).fetchone()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB upsert failed: {e}")

    # 7) 回傳整包 data（給你檢查）
    row2 = db.execute(GET_ONE_SQL, {"client_id": client_id, "case_id": case_id}).fetchone()
    data_now: Dict[str, Any] = row2[0] if row2 else {}
    all_keys = list(data_now.keys())
    non_empty_keys = [k for k, v in data_now.items() if not is_empty_value(v)]

    return {
        "ok": True,
        "id": row[0],
        "client_id": client_id,
        "case_id": case_id,
        "data": data_now,
        "data_keys": all_keys,
        "data_keys_non_empty": non_empty_keys
    }

@router.get("/by-id")
def get_case(client_id: str, case_id: str, as_text: bool = False, db: Session = Depends(get_db)):
    """
    讀取一筆案件：
    - 預設回傳整包 data JSON
    - ?as_text=true → 回傳純文字（略過空值）
    """
    row = db.execute(GET_ONE_SQL, {"client_id": client_id, "case_id": case_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="case not found")

    data: Dict[str, Any] = row[0] or {}
    if not as_text:
        return {"client_id": client_id, "case_id": case_id, "data": data}

    lines = []
    def add(label: str, key: str):
        v = data.get(key, "")
        if not is_empty_value(v):
            lines.append(f"{label}：{v}")
    add("案件類型", "case_type")
    add("進度", "progress")
    add("案號", "case_number")
    add("法院", "court")
    add("股別", "division")
    stages = data.get("progress_stages", {})
    if isinstance(stages, dict) and stages:
        for k, v in stages.items():
            if not is_empty_value(v):
                lines.append(f"{k}：{v}")

    text_out = "\n".join(lines) if lines else "目前無可顯示內容"
    return {"client_id": client_id, "case_id": case_id, "text": text_out}
