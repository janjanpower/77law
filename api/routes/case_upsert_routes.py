# api/routes/case_upsert_routes.py
# -*- coding: utf-8 -*-
"""
提供 /api/cases/upsert
- 單筆或批次 upsert 到資料庫 case_records
- 修正：若 JSON 欄位以「字串」送入，會自動 json.loads() 成真正的物件再寫入
- 修正：只有內容有變動才更新，並刷新 updated_at；無變動回傳 action="nochange"
- 若存在 api/local_cases.py，會在寫入成功後同步到本地 cases.json（相容舊檔 case_data.json）
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
import json, traceback

from sqlalchemy.orm import Session
from sqlalchemy import text, inspect, func

# 依你的專案實際路徑調整
from api.database import get_db            # 提供 SQLAlchemy Session
from api.models_cases import CaseRecord    # SQLAlchemy Model: case_records

# optional: 本地 JSON 同步（沒有檔案也能跑）
try:
    from api.local_cases import upsert_case_local, migrate_case_json  # 可選
    _HAS_LOCAL = True
except Exception:
    _HAS_LOCAL = False

router = APIRouter(prefix="/api/cases", tags=["cases"])

# ---------- Pydantic 輸入模型 ----------
class CaseUpsertIn(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=50)
    case_id:   str = Field(..., min_length=1, max_length=100)

    title: Optional[str] = None
    case_type: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    lawyer: Optional[str] = None
    legal_affairs: Optional[str] = None

    progress: Optional[str] = None
    case_reason: Optional[str] = None
    case_number: Optional[str] = None
    opposing_party: Optional[str] = None
    court: Optional[str] = None
    division: Optional[str] = None
    progress_date: Optional[str] = None

    # 三個 JSON 欄位
    progress_stages: Optional[Dict[str, Any]] = None
    progress_notes:  Optional[Dict[str, Any]] = None
    progress_times:  Optional[Dict[str, Any]] = None


# ---------- Safety：確保資料表/欄位存在（對舊庫友善） ----------
def _ensure_case_table(db: Session) -> None:
    try:
        eng = db.get_bind()
        insp = inspect(eng)
        if not insp.has_table("case_records"):
            CaseRecord.__table__.create(bind=eng, checkfirst=True)
            print(">> created table: case_records")
    except Exception:
        traceback.print_exc()

def _ensure_case_columns(db: Session) -> None:
    """補齊常用欄位，避免 UndefinedColumn；已存在會略過"""
    try:
        eng = db.get_bind()
        insp = inspect(eng)
        if not insp.has_table("case_records"):
            return
        existing = {c["name"] for c in insp.get_columns("case_records")}
        add_sql = []

        def add(col: str, ddl: str):
            if col not in existing:
                add_sql.append(f"ADD COLUMN IF NOT EXISTS {col} {ddl}")

        # 文字欄位
        for col in [
            "title","case_type","plaintiff","defendant","lawyer","legal_affairs",
            "progress","case_reason","case_number","opposing_party","court",
            "division","progress_date"
        ]:
            add(col, "TEXT")
        # JSONB 欄位
        add("progress_stages", "JSONB DEFAULT '{}'::jsonb")
        add("progress_notes",  "JSONB DEFAULT '{}'::jsonb")
        add("progress_times",  "JSONB DEFAULT '{}'::jsonb")
        # 時間欄位
        add("created_at", "timestamptz DEFAULT NOW()")
        add("updated_at", "timestamptz DEFAULT NOW()")

        if add_sql:
            db.execute(text("ALTER TABLE case_records " + ", ".join(add_sql)))
            db.commit()
            print(">> altered table case_records:", ", ".join(add_sql))
    except Exception:
        traceback.print_exc()


# ---------- 修正：把字串化 JSON 轉回物件 ----------
def _ensure_json_obj(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return v

def _prep_fields(data: CaseUpsertIn) -> Dict[str, Any]:
    fields = data.dict(exclude_unset=True).copy()
    fields.pop("client_id", None)
    fields.pop("case_id", None)
    # 三個 JSON 欄位若為字串 → 轉回物件
    if "progress_stages" in fields:
        fields["progress_stages"] = _ensure_json_obj(fields["progress_stages"])
    if "progress_notes" in fields:
        fields["progress_notes"]  = _ensure_json_obj(fields["progress_notes"])
    if "progress_times" in fields:
        fields["progress_times"]  = _ensure_json_obj(fields["progress_times"])
    return fields


# ---------- 核心：單筆 upsert ----------
def _upsert_one(data: CaseUpsertIn, db: Session) -> Dict[str, Any]:
    obj = (
        db.query(CaseRecord)
          .filter(CaseRecord.client_id == data.client_id,
                  CaseRecord.case_id   == data.case_id)
          .order_by(CaseRecord.id.desc())
          .first()
    )

    fields = _prep_fields(data)

    if obj:
        changed = False
        for k, v in fields.items():
            # 僅在值真的不同時更新；None 不覆蓋
            if v is not None and getattr(obj, k, None) != v:
                setattr(obj, k, v)
                changed = True
        if changed:
            setattr(obj, "updated_at", func.now())
            db.add(obj)
            db.commit()
            db.refresh(obj)
            action = "updated"
        else:
            action = "nochange"
    else:
        obj = CaseRecord(client_id=data.client_id, case_id=data.case_id, **fields)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        action = "created"

    # optional：同步到本地 cases.json
    if _HAS_LOCAL:
        try:
            migrate_case_json()
            local_payload = {
                "client_id": data.client_id,
                "case_id":   data.case_id,
                "title":     getattr(obj, "title", None),
                "case_type": getattr(obj, "case_type", None),
                "plaintiff": getattr(obj, "plaintiff", None),
                "defendant": getattr(obj, "defendant", None),
                "lawyer":    getattr(obj, "lawyer", None),
                "legal_affairs": getattr(obj, "legal_affairs", None),
                "progress":      getattr(obj, "progress", None),
                "case_reason":   getattr(obj, "case_reason", None),
                "case_number":   getattr(obj, "case_number", None),
                "opposing_party":getattr(obj, "opposing_party", None),
                "court":         getattr(obj, "court", None),
                "division":      getattr(obj, "division", None),
                "progress_date": getattr(obj, "progress_date", None),
                "progress_stages": getattr(obj, "progress_stages", None),
                "progress_notes":  getattr(obj, "progress_notes", None),
                "progress_times":  getattr(obj, "progress_times", None),
                "created_at": (getattr(obj, "created_at", None).isoformat()
                               if getattr(obj, "created_at", None) else None),
                "updated_at": (getattr(obj, "updated_at", None).isoformat()
                               if getattr(obj, "updated_at", None) else None),
            }
            upsert_case_local(local_payload)
        except Exception:
            traceback.print_exc()

    # post-check：直接從 DB 撈最新一筆回給前端核對
    row = db.execute(
        text("""
            SELECT id, client_id, case_id, title, case_type, case_reason, court, division,
                   progress, progress_date, created_at, updated_at,
                   progress_stages, progress_notes, progress_times
            FROM case_records
            WHERE client_id=:cid AND case_id=:caseid
            ORDER BY id DESC
            LIMIT 1
        """),
        {"cid": data.client_id, "caseid": data.case_id}
    ).mappings().first()

    return {
        "ok": True,
        "action": action,
        "id": obj.id if obj else None,
        "client_id": data.client_id,
        "case_id": data.case_id,
        "latest_row": dict(row) if row else None
    }


# ---------- 端點：支援單筆或批次 ----------
@router.post("/upsert")
def upsert_case(
    payload: Union[CaseUpsertIn, List[CaseUpsertIn]] = Body(...),
    db: Session = Depends(get_db)
):
    try:
        bind = db.get_bind()
        print(">> writing to DB:", str(getattr(bind, "url", "unknown")))

        _ensure_case_table(db)
        _ensure_case_columns(db)

        if isinstance(payload, list):
            results: List[Dict[str, Any]] = []
            for item in payload:
                results.append(_upsert_one(item, db))
            return {
                "ok": True,
                "total": len(results),
                "created": sum(1 for r in results if r["action"] == "created"),
                "updated": sum(1 for r in results if r["action"] == "updated"),
                "nochange": sum(1 for r in results if r["action"] == "nochange"),
                "items": results
            }
        else:
            return _upsert_one(payload, db)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "upsert_case failed",
                "error_type": type(e).__name__,
                "error": str(e),
            }
        )
