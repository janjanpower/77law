# -*- coding: utf-8 -*-
# api/routes/case_upload_routes.py
# 支援單筆或多筆上傳；JSONB 以 ::jsonb 轉型

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from datetime import datetime
import json
import os

from api.database import DATABASE_URL
from api.services.tenant_bootstrap import ensure_tenant_schema

router = APIRouter(prefix="/api/cases", tags=["cases"])

# -------------------------
# helpers
# -------------------------

_ALLOWED_ITEM_KEYS = {
    "case_id", "case_type", "client", "lawyer", "legal_affairs",
    "progress", "case_reason", "case_number", "opposing_party",
    "court", "division", "progress_date",
    "progress_stages", "progress_notes", "progress_times",
    "created_date", "updated_date", "uploaded_by"
}

def _as_jsonb_str(v: Optional[Any]) -> str:
    """dict/None/'' 轉為合規 JSON 字串，其餘保留或序列化。"""
    if v is None:
        return "{}"
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, str):
        s = v.strip()
        return s if s else "{}"
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return "{}"

def _iso_or_none(v: Optional[Any]) -> Optional[str]:
    """空白->None；其它轉字串回傳（DB timestamptz 可吃 ISO 字串）。"""
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def _get_root_engine() -> Engine:
    db_url = os.getenv("DATABASE_URL", DATABASE_URL)
    if not db_url:
        raise RuntimeError("DATABASE_URL not configured")
    return create_engine(db_url, pool_pre_ping=True)

def _get_tenant_engine(client_id: str) -> Engine:
    """優先從 login_users.tenant_db_url 取；若無則 ensure_tenant_schema 後回傳。"""
    root = _get_root_engine()
    with root.connect() as cx:
        row = cx.execute(
            text("SELECT tenant_db_url FROM login_users WHERE client_id = :cid"),
            {"cid": client_id}
        ).mappings().first()
    tenant_url: Optional[str] = row["tenant_db_url"] if row else None
    if not tenant_url:
        tenant_url = ensure_tenant_schema(client_id)
    return create_engine(tenant_url, pool_pre_ping=True)

def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    同時支援：
    1) 多筆：payload['items'] 為 list
    2) 單筆：欄位直接在最外層（含 case_id/…）
    3) 單筆包在 payload['data']（若你之後改格式）
    """
    if isinstance(payload.get("items"), list) and payload["items"]:
        return payload["items"]

    # 單筆在最外層（你現在的情況）
    # 從 payload 萃取允許欄位變成一筆 item
    top_has_any_case_field = any(k in payload for k in _ALLOWED_ITEM_KEYS.union({"case_id"}))
    if top_has_any_case_field:
        single = {k: payload.get(k) for k in _ALLOWED_ITEM_KEYS if k in payload}
        # 把 case_id 若落在最外層也帶進去
        if "case_id" not in single and "case_id" in payload:
            single["case_id"] = payload["case_id"]
        return [single]

    # 若有 data 且是 dict，當單筆資料看待
    data = payload.get("data")
    if isinstance(data, dict):
        single = {k: data.get(k) for k in _ALLOWED_ITEM_KEYS if k in data}
        if "case_id" not in single and "case_id" in data:
            single["case_id"] = data["case_id"]
        return [single] if single else []

    return []

# -------------------------
# SQL
# -------------------------

INSERT_SQL = text("""
    INSERT INTO case_records (
        client_id, case_id,
        case_type, client, lawyer, legal_affairs,
        progress, case_reason, case_number, opposing_party, court, division,
        progress_date, progress_stages, progress_notes, progress_times,
        created_date, updated_date, uploaded_by
    ) VALUES (
        :client_id, :case_id,
        :case_type, :client, :lawyer, :legal_affairs,
        :progress, :case_reason, :case_number, :opposing_party, :court, :division,
        :progress_date,
        :progress_stages::jsonb, :progress_notes::jsonb, :progress_times::jsonb,
        :created_date, :updated_date, :uploaded_by
    )
    RETURNING id
""")

# -------------------------
# Route
# -------------------------

@router.post("/upload")
def upload_cases(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    支援兩種請求格式：

    A) 單筆（你現在的格式）
    {
      "client_id": "12345678",
      "case_id": "114001",
      "case_type": "民事",
      "client": "大狗",
      ...
      "progress_stages": "{\"調解\":\"2025-08-09\"}",
      "progress_notes":  "{}",
      "progress_times":  "{}",
      "created_date": "2025-08-09T23:58:02.112975",
      "updated_date": "2025-08-09T23:58:57.171500",
      "uploaded_by": "誰上傳"
    }

    B) 多筆
    {
      "client_id": "12345678",
      "uploaded_by": "誰上傳",
      "items": [ { ...單筆欄位... }, { ... } ]
    }
    """
    client_id = str(payload.get("client_id", "")).strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    uploaded_by_default = str(payload.get("uploaded_by") or "").strip() or None

    items: List[Dict[str, Any]] = _extract_items(payload)
    if not items:
        raise HTTPException(status_code=400, detail="items must be a non-empty list or provide single case fields at top-level")

    # 取得租戶連線
    try:
        tenant_eng = _get_tenant_engine(client_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"tenant init error: {e}")

    results = {"total": len(items), "success": 0, "failed": 0, "details": []}

    with tenant_eng.begin() as cx:
        # 逐筆寫入
        for it in items:
            try:
                params = {
                    "client_id": client_id,
                    "case_id": str(it.get("case_id", "")).strip(),
                    "case_type": str(it.get("case_type", "")).strip(),
                    "client": str(it.get("client", "")).strip(),
                    "lawyer": str(it.get("lawyer") or "").strip() or None,
                    "legal_affairs": str(it.get("legal_affairs") or "").strip() or None,
                    "progress": str(it.get("progress", "待處理") or "待處理").strip(),
                    "case_reason": str(it.get("case_reason") or "").strip() or None,
                    "case_number": str(it.get("case_number") or "").strip() or None,
                    "opposing_party": str(it.get("opposing_party") or "").strip() or None,
                    "court": str(it.get("court") or "").strip() or None,
                    "division": str(it.get("division") or "").strip() or None,
                    "progress_date": str(it.get("progress_date") or "").strip() or None,

                    "progress_stages": _as_jsonb_str(it.get("progress_stages")),
                    "progress_notes":  _as_jsonb_str(it.get("progress_notes")),
                    "progress_times":  _as_jsonb_str(it.get("progress_times")),

                    "created_date": _iso_or_none(it.get("created_date")),
                    "updated_date": _iso_or_none(it.get("updated_date")),

                    "uploaded_by": str(it.get("uploaded_by") or uploaded_by_default or "").strip() or None,
                }

                # 必填檢查
                if not params["case_id"] or not params["case_type"] or not params["client"] or not params["progress"]:
                    raise ValueError("missing required fields (case_id/case_type/client/progress)")

                new_id = cx.execute(INSERT_SQL, params).scalar()
                results["success"] += 1
                results["details"].append({"case_id": params["case_id"], "status": "ok", "id": new_id})

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "case_id": str(it.get("case_id", "")),
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
    }
