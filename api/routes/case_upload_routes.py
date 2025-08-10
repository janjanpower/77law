# -*- coding: utf-8 -*-
"""
api/routes/case_upload_routes.py
多租戶版本：上傳案件資料到對應租戶資料庫
"""

from typing import Optional, Dict, Any
import json
from fastapi import APIRouter, HTTPException, Request, Query
from sqlalchemy import text, bindparam
from api.database import get_db

router = APIRouter(prefix="/api/cases", tags=["cases"])

# ---------- 預設欄位 ----------
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
    "progress_stages": {},
    "progress_notes": {},
    "progress_times": {}
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

# ---------- SQL ----------
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
""")

# ---------- 路由 ----------
@router.post("/upload")
async def upload_case(
    request: Request,
    client_id: str = Query(..., description="事務所/租戶的 client_id")
):
    """
    建立/更新一筆案件（會自動切換到該租戶的資料庫）
    """
    try:
        payload: Dict[str, Any] = {}
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            form = await request.form()
            payload = dict(form)

        case_id = (payload.get("case_id") or "").strip()
        if not client_id or not case_id:
            raise HTTPException(status_code=400, detail="client_id 與 case_id 必填")

        raw_data = payload.get("data", {})
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                raise HTTPException(status_code=400, detail="data 必須是 JSON")
        if not isinstance(raw_data, dict):
            raise HTTPException(status_code=400, detail="data 必須是 JSON 物件")

        data_obj = with_defaults(raw_data)

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
            "created_date": data_obj.get("created_date") or now,
            "updated_date": data_obj.get("updated_date") or now,
        }

        with get_db(client_id) as db:
            row = db.execute(UPSERT_SQL, params).fetchone()
            db.commit()
            record_id = row[0] if row else None

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
