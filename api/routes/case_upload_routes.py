# -*- coding: utf-8 -*-
# api/routes/case_upload_routes.py
# 直接覆蓋本檔

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

def _as_jsonb_str(v: Optional[Any]) -> str:
    """
    接受 dict / str / None：
    - dict -> json.dumps(dict)
    - '' 或 None -> '{}'
    - 其餘字串 -> 原字串（去除前後空白）
    """
    if v is None:
        return "{}"
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, str):
        s = v.strip()
        return s if s else "{}"
    # 其他型別（list/number 等）也序列化
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return "{}"

def _iso_or_none(v: Optional[str]) -> Optional[str]:
    """
    接受 ISO 字串、空字串或 None，空白視為 None。
    DB 端 timestamptz 可接受 ISO 字串。
    """
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
    """
    1) 從 login_users 讀取 tenant_db_url
    2) 若無 -> 呼叫 ensure_tenant_schema 建立並寫回
    3) 回傳指向租戶 schema 的 engine
    """
    root = _get_root_engine()
    with root.connect() as cx:
        row = cx.execute(
            text("SELECT tenant_db_url FROM login_users WHERE client_id = :cid"),
            {"cid": client_id}
        ).mappings().first()

    tenant_url: Optional[str] = row["tenant_db_url"] if row else None
    if not tenant_url:
        # 建立新租戶 schema 並回寫 URL
        tenant_url = ensure_tenant_schema(client_id)

    return create_engine(tenant_url, pool_pre_ping=True)

# -------------------------
# SQL (欄位清單只放欄位名；VALUES 端做 ::jsonb)
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
    請求格式：
    {
      "client_id": "12345678",
      "uploaded_by": "someone",                # 可選
      "items": [
        {
          "case_id": "114001",
          "case_type": "民事",
          "client": "大狗",
          "lawyer": "",
          "legal_affairs": "996",
          "progress": "待處理",
          "case_reason": "",
          "case_number": "",
          "opposing_party": "",
          "court": "",
          "division": "",
          "progress_date": "",                 # 文字即可
          "progress_stages": "{\"調解\":\"2025-08-09\"}",  # 字串或 dict 皆可
          "progress_notes": "{}",
          "progress_times": "{}",
          "created_date": "2025-08-09T23:58:02.112975",
          "updated_date": "2025-08-09T23:58:57.171500"
        },
        ...
      ]
    }
    """
    client_id = str(payload.get("client_id", "")).strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    uploaded_by = str(payload.get("uploaded_by") or "").strip() or None
    items: List[Dict[str, Any]] = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="items must be a non-empty list")

    # 取得租戶連線
    try:
        tenant_eng = _get_tenant_engine(client_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"tenant init error: {e}")

    results = {"total": len(items), "success": 0, "failed": 0, "details": []}

    with tenant_eng.begin() as cx:
        # 鎖定 search_path（穩妥起見）
        cx.execute(text("SELECT current_schema()"))  # 建立 session
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

                    # JSONB 欄位（允許 str / dict / None）
                    "progress_stages": _as_jsonb_str(it.get("progress_stages")),
                    "progress_notes":  _as_jsonb_str(it.get("progress_notes")),
                    "progress_times":  _as_jsonb_str(it.get("progress_times")),

                    # 時間戳（ISO 字串或 None）
                    "created_date": _iso_or_none(it.get("created_date")),
                    "updated_date": _iso_or_none(it.get("updated_date")),

                    # 上傳者
                    "uploaded_by": uploaded_by,
                }

                # 必填欄位檢查（你需求中這幾個是 NOT NULL）
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
