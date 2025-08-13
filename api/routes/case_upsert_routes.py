# case_upsert_routes.py（重點片段，可覆蓋）
# -*- coding: utf-8 -*-
import os
from typing import List, Dict, Any, Union, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from api.database import get_db
from api.models_cases import CaseRecord  # ← 你的 CaseRecord

router = APIRouter(prefix="/api/cases", tags=["cases"])

# ✅ 從環境變數取得本租戶的 client_id（單一事務所部署最方便）
TENANT_ID = os.getenv("APP_CLIENT_ID", "").strip()

class CaseUpsertIn(BaseModel):
    case_type: str = Field(..., min_length=1)
    case_id:   str = Field(..., min_length=1)

    # 可選：如果前端有傳 client_id 也接受；否則後端自動補 TENANT_ID
    client_id: Optional[str] = None

    client: Optional[str] = None
    lawyer: Optional[str] = None
    legal_affairs: Optional[str] = None
    progress: Optional[str] = None
    case_reason: Optional[str] = None
    case_number: Optional[str] = None
    opposing_party: Optional[str] = None
    court: Optional[str] = None
    division: Optional[str] = None
    progress_date: Optional[str] = None
    created_date: Optional[str] = None
    updated_date: Optional[str] = None

    progress_stages: Optional[Dict[str, Any]] = None
    progress_notes:  Optional[Dict[str, Any]] = None
    progress_times:  Optional[Dict[str, Any]] = None

    uploaded_by: Optional[str] = None

def _to_obj_if_json_str(v: Any) -> Any:
    if isinstance(v, str):
        import json
        s = v.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                return json.loads(s)
            except Exception:
                return None
    return v

def _normalize_row(d: Dict[str, Any]) -> Dict[str, Any]:
    keep = {c.name for c in CaseRecord.__table__.columns}
    x: Dict[str, Any] = {}
    for k, v in d.items():
        if k in ("progress_stages", "progress_notes", "progress_times"):
            v = _to_obj_if_json_str(v)
        if k in keep:
            x[k] = v
    # ✅ 自動補上 client_id（若欄位存在且來自環境變數）
    if "client_id" in keep and not x.get("client_id") and TENANT_ID:
        x["client_id"] = TENANT_ID
    return x

@router.post("/upsert")
def upsert_cases(payload: Union[List[CaseUpsertIn], CaseUpsertIn], db: Session = Depends(get_db)):
    # 統一轉 list
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        return {"ok": True, "total": 0, "uploaded": 0, "failed": 0}

    rows: List[Dict[str, Any]] = []
    for p in items:
        d = p.model_dump(exclude_none=True)
        if not d.get("case_type") or not d.get("case_id"):
            raise HTTPException(status_code=400, detail="case_type 與 case_id 為必填")
        rows.append(_normalize_row(d))

    stmt = insert(CaseRecord).values(rows)

    # 衝突時要更新的欄位（❗不更新主鍵/唯一鍵本身）
    exclude = {"id", "case_type", "case_id"}
    update_cols = {c.name: stmt.excluded[c.name]
                   for c in CaseRecord.__table__.columns
                   if c.name not in exclude}

    stmt = stmt.on_conflict_do_update(
        index_elements=[CaseRecord.case_type, CaseRecord.case_id],
        set_=update_cols,
    )

    db.execute(stmt)
    db.commit()

    return {"ok": True, "total": len(rows), "uploaded": len(rows), "failed": 0}
