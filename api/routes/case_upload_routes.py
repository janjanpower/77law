# -*- coding: utf-8 -*-
"""api/routes/case_upload_routes.py — flexible client_id intake (query/body/header) and tenant-aware DB"""
from typing import Dict, Any, Optional
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query
from sqlalchemy import text

from api.database import get_db_cm

router = APIRouter(prefix="/api/cases", tags=["cases"])

def ensure_dict(v: Any) -> Dict[str, Any]:
    if isinstance(v, dict): return v
    if v in (None, ""): return {}
    if isinstance(v, str):
        try: return json.loads(v)
        except Exception: return {}
    return {}

@router.post("/upload")
async def upload_case(
    request: Request,
    client_id_q: Optional[str] = Query(None, description="事務所/租戶的 client_id (query)"),
):
    # 1) 讀取 JSON
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
    except Exception:
        payload = {}

    # 2) 多來源取得 client_id / case_id：query > body > header
    client_id = client_id_q or payload.get("client_id") or request.headers.get("X-Client-Id")
    case_id = (payload.get("case_id") or "").strip()

    if not client_id:
        raise HTTPException(status_code=422, detail=[{
            "type": "missing", "loc": ["query", "client_id"], "msg": "Field required", "input": None
        }])
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id 必填 (in JSON body)")

    data = ensure_dict(payload.get("data"))

    def get_s(k, d=""): return str(data.get(k, d) or d)

    params = {
        "client_id": client_id,
        "case_id": case_id,
        "case_type": get_s("case_type"),
        "client": get_s("client"),
        "lawyer": get_s("lawyer"),
        "legal_affairs": get_s("legal_affairs"),
        "progress": get_s("progress", "待處理"),
        "case_reason": get_s("case_reason"),
        "case_number": get_s("case_number"),
        "opposing_party": get_s("opposing_party"),
        "court": get_s("court"),
        "division": get_s("division"),
        "progress_date": get_s("progress_date"),
        "progress_stages": json.dumps(ensure_dict(data.get("progress_stages")), ensure_ascii=False),
        "progress_notes": json.dumps(ensure_dict(data.get("progress_notes")), ensure_ascii=False),
        "progress_times": json.dumps(ensure_dict(data.get("progress_times")), ensure_ascii=False),
        "created_date": data.get("created_date") or datetime.utcnow(),
        "updated_date": data.get("updated_date") or datetime.utcnow(),
    }

    SELECT_ID = text("""SELECT id FROM case_records WHERE client_id=:client_id AND case_id=:case_id LIMIT 1""")
    INSERT_SQL = text("""
        INSERT INTO case_records (
            client_id, case_id,
            case_type, client, lawyer, legal_affairs,
            progress, case_reason, case_number, opposing_party, court, division,
            progress_date, progress_stages, progress_notes, progress_times,
            created_date, updated_date
        ) VALUES (
            :client_id, :case_id,
            :case_type, :client, :lawyer, :legal_affairs,
            :progress, :case_reason, :case_number, :opposing_party, :court, :division,
            :progress_date, CAST(:progress_stages AS JSONB), CAST(:progress_notes AS JSONB), CAST(:progress_times AS JSONB),
            :created_date, :updated_date
        )
        RETURNING id
    """)
    UPDATE_SQL = text("""
        UPDATE case_records SET
            case_type=:case_type, client=:client, lawyer=:lawyer, legal_affairs=:legal_affairs,
            progress=:progress, case_reason=:case_reason, case_number=:case_number, opposing_party=:opposing_party,
            court=:court, division=:division, progress_date=:progress_date,
            progress_stages=CAST(:progress_stages AS JSONB),
            progress_notes =CAST(:progress_notes  AS JSONB),
            progress_times =CAST(:progress_times  AS JSONB),
            updated_date=:updated_date
        WHERE client_id=:client_id AND case_id=:case_id
        RETURNING id
    """)

    try:
        # 3) 切到該租戶的 DB（依據 login_users.tenant_db_url）
        with get_db_cm(client_id) as db:
            row = db.execute(SELECT_ID, {"client_id": client_id, "case_id": case_id}).fetchone()
            if row:
                r2 = db.execute(UPDATE_SQL, params).fetchone()
                rec_id = r2[0] if r2 else row[0]
            else:
                r2 = db.execute(INSERT_SQL, params).fetchone()
                rec_id = r2[0] if r2 else None
            db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    return {"success": True, "client_id": client_id, "case_id": case_id, "database_id": rec_id}