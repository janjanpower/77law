# -*- coding: utf-8 -*-
"""
api/routes/case_upload_routes.py
Multi-tenant upload: writes to the tenant's schema based on client_id.
"""

from typing import Dict, Any
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query
from sqlalchemy import text

from api.database import get_db

router = APIRouter(prefix="/api/cases", tags=["cases"])

def ensure_dict(v: Any) -> Dict[str, Any]:
    if isinstance(v, dict):
        return v
    if v in (None, ""):
        return {}
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return {}

@router.post("/upload")
async def upload_case(
    request: Request,
    client_id: str = Query(..., description="事務所/租戶的 client_id"),
):
    """Create or update a case by (client_id, case_id) scoped to the tenant DB."""
    try:
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Invalid JSON payload")
        except Exception:
            raise HTTPException(status_code=400, detail="Body must be JSON object")

        case_id = (payload.get("case_id") or "").strip()
        if not client_id or not case_id:
            raise HTTPException(status_code=400, detail="client_id 與 case_id 必填")

        data = ensure_dict(payload.get("data"))

        # Flatten fields with sane defaults (compatible with models_cases.CaseRecord)
        def get_s(key, default=""): return str(data.get(key, default) or default)

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
            # JSON buckets
            "progress_stages": json.dumps(ensure_dict(data.get("progress_stages")), ensure_ascii=False),
            "progress_notes": json.dumps(ensure_dict(data.get("progress_notes")), ensure_ascii=False),
            "progress_times": json.dumps(ensure_dict(data.get("progress_times")), ensure_ascii=False),
            # Timestamps (nullable in model; we also store server-side created_at/updated_at)
            "created_date": data.get("created_date") or datetime.utcnow(),
            "updated_date": data.get("updated_date") or datetime.utcnow(),
        }

        # We cannot rely on ON CONFLICT if unique constraint is absent. Do manual upsert.
        SELECT_ID = text("""
            SELECT id FROM case_records
             WHERE client_id = :client_id AND case_id = :case_id
             LIMIT 1
        """)
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
                case_type = :case_type,
                client    = :client,
                lawyer    = :lawyer,
                legal_affairs = :legal_affairs,
                progress  = :progress,
                case_reason = :case_reason,
                case_number = :case_number,
                opposing_party = :opposing_party,
                court = :court,
                division = :division,
                progress_date = :progress_date,
                progress_stages = CAST(:progress_stages AS JSONB),
                progress_notes  = CAST(:progress_notes  AS JSONB),
                progress_times  = CAST(:progress_times  AS JSONB),
                updated_date = :updated_date
             WHERE client_id = :client_id AND case_id = :case_id
            RETURNING id
        """)

        with get_db(client_id) as db:
            row = db.execute(SELECT_ID, {"client_id": client_id, "case_id": case_id}).fetchone()
            if row:
                row2 = db.execute(UPDATE_SQL, params).fetchone()
                rec_id = row2[0] if row2 else row[0]
            else:
                row2 = db.execute(INSERT_SQL, params).fetchone()
                rec_id = row2[0] if row2 else None
            db.commit()

        return {
            "success": True,
            "message": "案件資料上傳成功",
            "client_id": client_id,
            "case_id": case_id,
            "database_id": rec_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"伺服器內部錯誤: {e}")