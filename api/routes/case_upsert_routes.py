# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Union, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from api.database import get_db
from api.models import CaseRecord  # 對應 public.case_records

router = APIRouter(prefix="/api/cases", tags=["cases"])

# ---- 請求模型（client_id 移除；只保留必要欄位） ----
class CaseUpsertIn(BaseModel):
    case_type: str = Field(..., min_length=1, description="案件類型")
    case_id:   str = Field(..., min_length=1, description="案件編號")

    # 常用欄位（可按你的模型擴充）
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

    # 三個 JSON 欄位（可為 dict 或 JSON 字串）
    progress_stages: Optional[Dict[str, Any]] = None
    progress_notes:  Optional[Dict[str, Any]] = None
    progress_times:  Optional[Dict[str, Any]] = None

    # 稽核資訊（可選）
    uploaded_by: Optional[str] = None


def _to_obj_if_json_str(v: Any) -> Any:
    """若是字串 JSON 就轉成物件；其餘維持原樣"""
    if isinstance(v, str):
        import json
        v_strip = v.strip()
        if v_strip.startswith("{") or v_strip.startswith("["):
            try:
                return json.loads(v_strip)
            except Exception:
                return None
    return v


def _normalize_row(d: Dict[str, Any]) -> Dict[str, Any]:
    """將輸入 dict 清洗成 ORM 欄位鍵名；只保留 CaseRecord 有的欄位"""
    keep_keys = {c.name for c in CaseRecord.__table__.columns}
    x = {}
    for k, v in d.items():
        if k in ("progress_stages", "progress_notes", "progress_times"):
            v = _to_obj_if_json_str(v)
        if k in keep_keys:
            x[k] = v
    return x


@router.post("/upsert")
def upsert_cases(payload: Union[List[CaseUpsertIn], CaseUpsertIn], db: Session = Depends(get_db)):
    """
    Upsert 案件（以 (case_type, case_id) 為唯一鍵）
    - 支援單筆或多筆
    - 不使用 client_id
    """
    # 統一成 list
    items: List[CaseUpsertIn] = payload if isinstance(payload, list) else [payload]
    if not items:
        return {"ok": True, "total": 0, "uploaded": 0, "failed": 0}

    # 轉為 dict 並清洗
    rows: List[Dict[str, Any]] = []
    for p in items:
        d = p.model_dump(exclude_none=True)
        # 防呆：必填
        if not d.get("case_type") or not d.get("case_id"):
            raise HTTPException(status_code=400, detail="case_type 與 case_id 為必填")
        rows.append(_normalize_row(d))

    if not rows:
        return {"ok": True, "total": 0, "uploaded": 0, "failed": 0}

    # SQLAlchemy INSERT ... ON CONFLICT (case_type, case_id) DO UPDATE
    stmt = insert(CaseRecord).values(rows)

    # 衝突時要更新的欄位（不更新主鍵與唯一鍵本身）
    exclude_cols = {"id", "case_type", "case_id"}
    update_cols = {
        c.name: stmt.excluded[c.name]
        for c in CaseRecord.__table__.columns
        if c.name not in exclude_cols
    }

    stmt = stmt.on_conflict_do_update(
        index_elements=[CaseRecord.case_type, CaseRecord.case_id],
        set_=update_cols,
    )

    db.execute(stmt)
    db.commit()

    return {
        "ok": True,
        "total": len(rows),
        "uploaded": len(rows),  # 以新增+更新計
        "failed": 0
    }
