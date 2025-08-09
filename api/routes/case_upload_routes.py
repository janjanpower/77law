# -*- coding: utf-8 -*-
"""
api/routes/case_upload_routes.py
修復現有代碼的 500 錯誤
主要問題：SQL 語句中的欄位與實際資料庫結構不匹配
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

# ---------- 預設鍵：只包含實際存在的欄位 ----------
DEFAULT_KEYS: Dict[str, Any] = {
    "case_type": "",
    "client": "",
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

# ---------- 修復：只包含實際存在的欄位 ----------
UPSERT_SQL = text("""
    INSERT INTO case_records (
        client_id, case_id,
        case_type, client, lawyer, legal_affairs,
        progress, case_reason, case_number, opposing_party, court, division,
        progress_date, progress_stages, progress_notes, progress_times,
        created_date, updated_date
    )
    VALUES (
        :client_id, :case_id,
        :case_type, :client, :lawyer, :legal_affairs,
        :progress, :case_reason, :case_number, :opposing_party, :court, :division,
        :progress_date,
        CAST(:progress_stages AS JSONB),
        CAST(:progress_notes AS JSONB),
        CAST(:progress_times AS JSONB),
        :created_date, :updated_date
    )
    ON CONFLICT (client_id, case_id)
    DO UPDATE SET
        case_type = EXCLUDED.case_type,
        client = EXCLUDED.client,
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
        updated_date = EXCLUDED.updated_date
    RETURNING id;
""").bindparams(
    bindparam("client_id"),
    bindparam("case_id"),
    bindparam("case_type"),
    bindparam("client"),
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
    bindparam("created_date"),
    bindparam("updated_date"),
)

GET_ONE_SQL = text("""
    SELECT case_type, client, lawyer, legal_affairs, progress, case_reason,
           case_number, opposing_party, court, division, progress_date,
           progress_stages, progress_notes, progress_times
    FROM case_records
    WHERE client_id=:client_id AND case_id=:case_id
    LIMIT 1
""")

# ---------- 路由 ----------
@router.post("/upload")
async def upload_case(request: Request, db: Session = Depends(get_db)):
    """
    建立/更新一筆案件
    修復版本：完全匹配資料庫結構
    """
    try:
        # 1) 讀取 JSON 請求
        payload: Dict[str, Any] = {}
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            # 2) 若不是 JSON，嘗試表單
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

        # 4) 標準化資料
        data_obj = with_defaults(raw_data)

        # 5) 準備參數 - 完全匹配資料庫欄位
        from datetime import datetime
        now = datetime.utcnow()

        params = {
            "client_id": client_id,
            "case_id": case_id,

            "case_type": data_obj.get("case_type", ""),
            "client": data_obj.get("client", ""),
            "lawyer": data_obj.get("lawyer", ""),
            "legal_affairs": data_obj.get("legal_affairs", ""),
            "progress": data_obj.get("progress", "待處理"),
            "case_reason": data_obj.get("case_reason", ""),
            "case_number": data_obj.get("case_number", ""),
            "opposing_party": data_obj.get("opposing_party", ""),
            "court": data_obj.get("court", ""),
            "division": data_obj.get("division", ""),
            "progress_date": data_obj.get("progress_date", ""),

            "progress_stages": json.dumps(data_obj.get("progress_stages", {}), ensure_ascii=False),
            "progress_notes": json.dumps(data_obj.get("progress_notes", {}), ensure_ascii=False),
            "progress_times": json.dumps(data_obj.get("progress_times", {}), ensure_ascii=False),

            # 處理時間戳
            "created_date": _parse_datetime(data_obj.get("created_date")) or now,
            "updated_date": _parse_datetime(data_obj.get("updated_date")) or now,
        }

        # 6) 執行 upsert
        try:
            row = db.execute(UPSERT_SQL, params).fetchone()
            db.commit()

            record_id = row[0] if row else None
            print(f"✅ 案件 upsert 成功: {client_id}/{case_id}, record_id: {record_id}")

        except Exception as e:
            db.rollback()
            print(f"❌ DB upsert 失敗: {e}")
            raise HTTPException(status_code=500, detail=f"資料庫操作失敗: {str(e)}")

        # 7) 回傳結果
        return {
            "success": True,
            "message": "案件資料上傳成功",
            "client_id": client_id,
            "case_id": case_id,
            "database_id": record_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ upload_case 異常: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"伺服器內部錯誤: {str(e)}")

def _parse_datetime(value):
    """解析時間戳"""
    if not value:
        return None
    if isinstance(value, str):
        try:
            from datetime import datetime
            # 嘗試 ISO 格式
            if 'T' in value:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(value)
        except:
            return None
    return value

@router.get("/by-id")
def get_case(client_id: str, case_id: str, db: Session = Depends(get_db)):
    """讀取一筆案件"""
    try:
        row = db.execute(GET_ONE_SQL, {"client_id": client_id, "case_id": case_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="案件不存在")

        # 組合回傳資料
        data = {
            "case_type": row[0],
            "client": row[1],
            "lawyer": row[2],
            "legal_affairs": row[3],
            "progress": row[4],
            "case_reason": row[5],
            "case_number": row[6],
            "opposing_party": row[7],
            "court": row[8],
            "division": row[9],
            "progress_date": row[10],
            "progress_stages": row[11] if row[11] else {},
            "progress_notes": row[12] if row[12] else {},
            "progress_times": row[13] if row[13] else {}
        }

        return {
            "success": True,
            "client_id": client_id,
            "case_id": case_id,
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ get_case 異常: {e}")
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

# 健康檢查
@router.get("/health")
def health_check():
    """健康檢查"""
    return {"status": "healthy", "service": "case_upload_routes"}