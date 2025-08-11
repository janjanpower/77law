# -*- coding: utf-8 -*-
# api/routes/case_upload_routes.py
# Single-ENGINE + per-request SET search_path + payload normalization + write-then-readback

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body, Query
from sqlalchemy import text
from datetime import datetime
import json

from api.database import ENGINE  # ✅ use one shared Engine to avoid connection explosion

router = APIRouter(prefix="/api/cases", tags=["cases"])

# ---------- helpers ----------

JSONB_KEYS = ("progress_stages", "progress_notes", "progress_times")
DATE_KEYS  = ("progress_date", "created_date", "updated_date")

def to_iso_or_none(v: Any) -> Optional[str]:
    if v is None: return None
    if isinstance(v, str) and not v.strip(): return None
    return v.isoformat() if hasattr(v, "isoformat") else str(v)

def to_jsonb_or_none(v: Any) -> Optional[str]:
    if v is None: return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, str):
        s = v.strip()
        if not s: return None
        # try to parse JSON string
        try:
            return json.dumps(json.loads(s), ensure_ascii=False)
        except Exception:
            return None  # not valid JSON -> store NULL to avoid 500
    return json.dumps(v, ensure_ascii=False)

def normalize_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    # support items[] or single {data:{...}} + allow top-level overrides
    if isinstance(payload.get("items"), list) and payload["items"]:
        items = payload["items"]
    else:
        data = payload.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        merged = {**data}
        for k in ("case_id","case_type","client","lawyer","legal_affairs","progress",
                  "case_reason","case_number","opposing_party","court","division",
                  "progress_date","progress_stages","progress_notes","progress_times",
                  "created_date","updated_date","uploaded_by"):
            if payload.get(k) is not None:
                merged[k] = payload[k]
        items = [merged]

    out: List[Dict[str, Any]] = []
    for it in items:
        obj = dict(it)
        for k in DATE_KEYS:
            obj[k] = to_iso_or_none(obj.get(k))
        for k in JSONB_KEYS:
            obj[k] = to_jsonb_or_none(obj.get(k))
        obj["case_id"] = str(obj.get("case_id", "")).strip()
        obj["case_type"] = str(obj.get("case_type", "")).strip()
        obj["client"] = str(obj.get("client", "")).strip()
        obj["progress"] = str(obj.get("progress", "待處理")).strip() or "待處理"
        out.append(obj)
    return out

UPSERT_SQL = text("""
INSERT INTO case_records (
  client_id, case_id,
  case_type, client, lawyer, legal_affairs,
  progress, case_reason, case_number, opposing_party, court, division, progress_date,
  progress_stages, progress_notes, progress_times,
  created_date, updated_date, uploaded_by
) VALUES (
  :client_id, :case_id,
  :case_type, :client, :lawyer, :legal_affairs,
  :progress, :case_reason, :case_number, :opposing_party, :court, :division, :progress_date,
  CAST(:progress_stages AS jsonb), CAST(:progress_notes AS jsonb), CAST(:progress_times AS jsonb),
  :created_date, :updated_date, :uploaded_by
)
ON CONFLICT (client_id, case_id) DO UPDATE SET
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
  progress_stages = COALESCE(EXCLUDED.progress_stages, case_records.progress_stages),
  progress_notes  = COALESCE(EXCLUDED.progress_notes,  case_records.progress_notes),
  progress_times  = COALESCE(EXCLUDED.progress_times,  case_records.progress_times),
  created_date    = COALESCE(EXCLUDED.created_date,    case_records.created_date),
  updated_date    = COALESCE(EXCLUDED.updated_date,    case_records.updated_date),
  uploaded_by     = EXCLUDED.uploaded_by,
  updated_at      = now()
RETURNING id
""")

# ---------- endpoints ----------

@router.get("/health")
def health(client_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    info: Dict[str, Any] = {"status": "ok", "time": datetime.now().isoformat()}
    try:
        with ENGINE.connect() as cx:
            info["root_search_path"] = cx.execute(text("SHOW search_path")).scalar()
            info["current_database"] = cx.execute(text("SELECT current_database()")).scalar()
    except Exception as e:
        return {"status": "error", "where": "root", "error": str(e)}

    if not client_id:
        return info

    schema = f"client_{client_id}"
    try:
        with ENGINE.begin() as cx:
            cx.execute(text(f"SET search_path TO {schema}"))
            info["tenant_search_path"] = cx.execute(text("SHOW search_path")).scalar()
            info["tenant_current_schema"] = cx.execute(text("SELECT current_schema()")).scalar()
            try:
                cx.execute(text("SELECT 1 FROM case_records LIMIT 1"))
                info["case_records_exists"] = True
            except Exception as e2:
                info["case_records_exists"] = False
                info["case_records_check_error"] = str(e2)
    except Exception as e:
        info.update({"status":"error","where":"tenant_connect","error":str(e)})
        return info

    return info

@router.post("/upload")
def upload_cases(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    client_id = str(payload.get("client_id") or "").strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    items = normalize_items(payload)
    if not items:
        raise HTTPException(status_code=400, detail="items must resolve to a non-empty list")

    schema = f"client_{client_id}"

    summary = {"total": len(items), "success": 0, "failed": 0, "details": []}
    debug: Dict[str, Any] = {}

    with ENGINE.begin() as cx:
        # force into tenant schema
        cx.execute(text(f"SET search_path TO {schema}"))
        debug["search_path"] = cx.execute(text("SHOW search_path")).scalar()
        debug["current_schema"] = cx.execute(text("SELECT current_schema()")).scalar()

        # ensure table + unique index exist (idempotent)
        cx.execute(text("""
            CREATE TABLE IF NOT EXISTS case_records (
              id bigserial PRIMARY KEY,
              client_id text NOT NULL,
              case_id   text NOT NULL,
              case_type text, client text, lawyer text, legal_affairs text,
              progress  text, case_reason text, case_number text,
              opposing_party text, court text, division text,
              progress_date timestamptz,
              progress_stages jsonb, progress_notes jsonb, progress_times jsonb,
              created_date timestamptz, updated_date timestamptz, uploaded_by text,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now()
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ux_case_records_client_case
            ON case_records (client_id, case_id);
        """))

        for it in items:
            try:
                params = {
                    "client_id": client_id,
                    "case_id": it["case_id"],
                    "case_type": it["case_type"],
                    "client": it["client"],
                    "lawyer": it.get("lawyer") or "",
                    "legal_affairs": it.get("legal_affairs") or "",
                    "progress": it["progress"],
                    "case_reason": it.get("case_reason") or "",
                    "case_number": it.get("case_number") or "",
                    "opposing_party": it.get("opposing_party") or "",
                    "court": it.get("court") or "",
                    "division": it.get("division") or "",
                    "progress_date": it.get("progress_date"),

                    "progress_stages": it.get("progress_stages"),
                    "progress_notes":  it.get("progress_notes"),
                    "progress_times":  it.get("progress_times"),

                    "created_date": it.get("created_date"),
                    "updated_date": it.get("updated_date"),
                    "uploaded_by": it.get("uploaded_by"),
                }

                if not params["case_id"] or not params["case_type"] or not params["client"] or not params["progress"]:
                    raise ValueError("missing required fields (case_id/case_type/client/progress)")

                new_id = cx.execute(UPSERT_SQL, params).scalar()
                summary["success"] += 1
                summary["details"].append({"case_id": params["case_id"], "status": "ok", "id": new_id})
            except Exception as e:
                summary["failed"] += 1
                summary["details"].append({"case_id": it.get("case_id",""), "status": "error", "reason": str(e)})

        # read back last N rows immediately from the same txn
        rows = [dict(r) for r in cx.execute(text("""
            SELECT id, client_id, case_id, client, case_type, progress, updated_at
            FROM case_records
            ORDER BY id DESC
            LIMIT 20
        """)).mappings().all()]

    return {
        "summary": summary,
        "debug": debug,
        "tail_rows": rows
    }

@router.get("/debug-list")
def debug_list(client_id: str = Query(...), limit: int = Query(20, ge=1, le=200)):
    schema = f"client_{client_id}"
    with ENGINE.begin() as cx:
        cx.execute(text(f"SET search_path TO {schema}"))
        rows = [dict(r) for r in cx.execute(text("""
            SELECT id, client_id, case_id, client, case_type, progress, updated_at
            FROM case_records
            ORDER BY id DESC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()]
        search_path = cx.execute(text("SHOW search_path")).scalar()
        return {"schema": schema, "search_path": search_path, "count": len(rows), "rows": rows}
