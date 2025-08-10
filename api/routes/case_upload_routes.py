# -*- coding: utf-8 -*-
# api/routes/case_upload_routes.py
# 依 client_id 寫入該租戶(schema)的 case_records；回傳 debug 資訊方便你確認寫到哪裡

from typing import List, Dict, Any, Optional, Tuple
from fastapi import APIRouter, HTTPException, Body, Query
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from datetime import datetime
import os, json

from api.database import DATABASE_URL
from api.services.tenant_bootstrap import ensure_tenant_schema

router = APIRouter(prefix="/api/cases", tags=["cases"])

# -------------------------
# Helpers
# -------------------------

def _mask_url(u: Optional[str]) -> str:
    if not u:
        return ""
    try:
        # postgres://user:pass@host:port/db?...  -> user:***@host:port/db?...（遮蔽密碼）
        if "://" in u and "@" in u:
            head, rest = u.split("://", 1)
            creds, tail = rest.split("@", 1)
            user = creds.split(":")[0]
            return f"{head}://{user}:***@{tail}"
    except Exception:
        pass
    return u

def _iso_or_none(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)

def _as_jsonb_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # 若是「字典樣字串」，原樣丟給 ::jsonb 轉
        return s
    return json.dumps(v, ensure_ascii=False)

def _get_root_engine() -> Engine:
    db_url = os.getenv("DATABASE_URL", DATABASE_URL)
    if not db_url:
        raise RuntimeError("DATABASE_URL not configured")
    return create_engine(db_url, pool_pre_ping=True)

def _get_tenant_engine_and_url(client_id: str) -> Tuple[Engine, str]:
    """優先用 login_users.tenant_db_url；沒有就建立 schema 後回傳。"""
    if not client_id or not str(client_id).strip():
        raise HTTPException(status_code=400, detail="client_id is required")

    root = _get_root_engine()
    tenant_url: Optional[str] = None
    with root.connect() as cx:
        row = cx.execute(
            text("SELECT tenant_db_url FROM login_users WHERE client_id = :cid"),
            {"cid": client_id}
        ).mappings().first()
        if row and row.get("tenant_db_url"):
            tenant_url = row["tenant_db_url"]

    if not tenant_url:
        tenant_url = ensure_tenant_schema(client_id)

    return create_engine(tenant_url, pool_pre_ping=True), tenant_url

def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    支援：
    1) 多筆：payload['items'] 為 list
    2) 單筆：欄位直接在最外層（含 case_id/…）
    3) 單筆包在 payload['data']（你的 Desktop 目前是這種：{client_id, case_id, data:{...}}）
    """
    if isinstance(payload.get("items"), list) and payload["items"]:
        return payload["items"]

    # 單筆：把外層與 data 併起來
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    merged = {**data}
    # 允許外層覆蓋關鍵欄位
    for k in [
        "case_id","case_type","client","lawyer","legal_affairs","progress","case_reason",
        "case_number","opposing_party","court","division","progress_date",
        "progress_stages","progress_notes","progress_times",
        "created_date","updated_date","uploaded_by"
    ]:
        if payload.get(k) is not None:
            merged[k] = payload[k]
    return [merged]

INSERT_UPSERT = text("""
INSERT INTO case_records (
    client_id, case_id,
    case_type, client, lawyer, legal_affairs,
    progress, case_reason, case_number, opposing_party, court, division, progress_date,
    progress_stages, progress_notes, progress_times,
    created_date, updated_date, uploaded_by
)
VALUES (
    :client_id, :case_id,
    :case_type, :client, :lawyer, :legal_affairs,
    :progress, :case_reason, :case_number, :opposing_party, :court, :division, :progress_date,
    :progress_stages::jsonb, :progress_notes::jsonb, :progress_times::jsonb,
    :created_date, :updated_date, :uploaded_by
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
    progress_stages = COALESCE(EXCLUDED.progress_stages, case_records.progress_stages),
    progress_notes  = COALESCE(EXCLUDED.progress_notes,  case_records.progress_notes),
    progress_times  = COALESCE(EXCLUDED.progress_times,  case_records.progress_times),
    created_date    = COALESCE(EXCLUDED.created_date,    case_records.created_date),
    updated_date    = COALESCE(EXCLUDED.updated_date,    case_records.updated_date),
    uploaded_by     = EXCLUDED.uploaded_by,
    updated_at      = now()
RETURNING id
""")

# -------------------------
# Health / Debug
# -------------------------

@router.get("/health")
def health(client_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    root = _get_root_engine()
    info = {"status": "ok", "time": datetime.now().isoformat()}
    with root.connect() as cx:
        info["root_db"] = str(cx.engine.url)
        info["root_url_masked"] = _mask_url(str(cx.engine.url))
    if client_id:
        te, turl = _get_tenant_engine_and_url(client_id)
        with te.connect() as cx:
            sp = cx.execute(text("SHOW search_path")).scalar()
            schema = cx.execute(text("SELECT current_schema()")).scalar()
            info["tenant_url_masked"] = _mask_url(turl)
            info["tenant_search_path"] = sp
            info["tenant_current_schema"] = schema
            # 驗證 case_records 是否存在
            try:
                cx.execute(text("SELECT 1 FROM case_records LIMIT 1"))
                info["case_records_exists"] = True
            except Exception:
                info["case_records_exists"] = False
    return info

# -------------------------
# Upload
# -------------------------

@router.post("/upload")
def upload_cases(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    client_id = str(payload.get("client_id") or "").strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    items = _extract_items(payload)
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="items must resolve to a non-empty list")

    engine, tenant_url = _get_tenant_engine_and_url(client_id)

    results = {
        "total": len(items),
        "success": 0,
        "failed": 0,
        "details": [],
        "debug": {}
    }

    with engine.begin() as cx:
        # Debug：回報實際連到哪裡、search_path 是什麼
        results["debug"]["tenant_url_masked"] = _mask_url(tenant_url)
        results["debug"]["search_path"] = cx.execute(text("SHOW search_path")).scalar()
        results["debug"]["current_schema"] = cx.execute(text("SELECT current_schema()")).scalar()

        for it in items:
            try:
                params = {
                    "client_id": client_id,
                    "case_id": str(it.get("case_id") or "").strip(),

                    "case_type": str(it.get("case_type") or "").strip(),
                    "client": str(it.get("client") or "").strip(),
                    "lawyer": str(it.get("lawyer") or "").strip(),
                    "legal_affairs": str(it.get("legal_affairs") or "").strip(),

                    "progress": str(it.get("progress") or "待處理").strip(),
                    "case_reason": str(it.get("case_reason") or "").strip(),
                    "case_number": str(it.get("case_number") or "").strip(),
                    "opposing_party": str(it.get("opposing_party") or "").strip(),
                    "court": str(it.get("court") or "").strip(),
                    "division": str(it.get("division") or "").strip(),
                    "progress_date": _iso_or_none(it.get("progress_date")),

                    "progress_stages": _as_jsonb_str(it.get("progress_stages")),
                    "progress_notes":  _as_jsonb_str(it.get("progress_notes")),
                    "progress_times":  _as_jsonb_str(it.get("progress_times")),

                    "created_date": _iso_or_none(it.get("created_date")),
                    "updated_date": _iso_or_none(it.get("updated_date")),
                    "uploaded_by": str(it.get("uploaded_by") or "").strip() or None,
                }

                if not params["case_id"] or not params["case_type"] or not params["client"] or not params["progress"]:
                    raise ValueError("missing required fields (case_id/case_type/client/progress)")

                new_id = cx.execute(INSERT_UPSERT, params).scalar()
                results["success"] += 1
                results["details"].append({"case_id": params["case_id"], "status": "ok", "id": new_id})

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "case_id": str(it.get("case_id") or ""),
                    "status": "error",
                    "reason": str(e),
                })

    return {
        "summary": {
            "total": results["total"],
            "success": results["success"],
            "failed": results["failed"],
        },
        "details": results["details"],
        "debug": results["debug"],
    }
