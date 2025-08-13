# api/routes/case_upload_routes.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import Table, Column, BigInteger, Text, JSON, TIMESTAMP, MetaData
from api.database import ENGINE
from datetime import datetime
import re

router = APIRouter()
metadata = MetaData()

class CaseItem(BaseModel):
    case_id: Optional[str] = None
    case_type: Optional[str] = None
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
    progress_stages: Optional[Dict[str, Any]] = None
    progress_notes: Optional[Dict[str, Any]] = None
    progress_times: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"  # 相容舊欄位

class UploadPayload(BaseModel):
    client_id: str = Field(..., description="事務所 ID（用來選表）")
    uploaded_by: Optional[str] = "frontend"
    items: List[CaseItem]

SAFE = re.compile(r"[^a-zA-Z0-9_]")

def _tenant_table_name(client_id: str) -> str:
    return f"case_records_{SAFE.sub('_', client_id)}"

def _coerce_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    try:
        # 最後嘗試 ISO 解析（Python 3.11+ 支援較好）
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None  # 不可解析就寫 NULL，避免 500

def _get_or_create_table(tbl_name: str) -> Table:
    # 定義表（每租戶同樣結構）
    tbl = Table(
        tbl_name, metadata,
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column("case_id", Text, nullable=True),
        Column("case_type", Text),
        Column("client", Text),
        Column("lawyer", Text),
        Column("legal_affairs", Text),
        Column("progress", Text),
        Column("case_reason", Text),
        Column("case_number", Text),
        Column("opposing_party", Text),
        Column("court", Text),
        Column("division", Text),
        Column("progress_date", TIMESTAMP(timezone=True)),
        Column("progress_stages", JSON, default=dict),
        Column("progress_notes", JSON, default=dict),
        Column("progress_times", JSON, default=dict),
        Column("created_at", TIMESTAMP(timezone=True), server_default=text("NOW()")),
        Column("updated_at", TIMESTAMP(timezone=True), server_default=text("NOW()")),
        extend_existing=True,
    )
    metadata.create_all(ENGINE, tables=[tbl])

    # 確保唯一索引存在（ON CONFLICT 需要唯一/排他約束）
    with ENGINE.begin() as conn:
        conn.execute(text(f"""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'public' AND indexname = '{tbl_name}_uq_case_id'
          ) THEN
            EXECUTE 'CREATE UNIQUE INDEX {tbl_name}_uq_case_id ON {tbl_name} (case_id) WHERE case_id IS NOT NULL';
          END IF;
        END $$;
        """))
    return tbl

@router.post("/api/cases/upload")
def upload_cases(payload: UploadPayload, request: Request):
    client_id = payload.client_id.strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    tbl_name = _tenant_table_name(client_id)
    tbl = _get_or_create_table(tbl_name)

    success = 0
    failed = 0
    errors: List[str] = []

    with ENGINE.begin() as conn:
        for i, item in enumerate(payload.items, start=1):
            try:
                row = item.dict()

                values = {
                    "case_id": (row.get("case_id") or row.get("case_number") or "").strip() or None,
                    "case_type": row.get("case_type"),
                    "client": row.get("client"),
                    "lawyer": row.get("lawyer"),
                    "legal_affairs": row.get("legal_affairs"),
                    "progress": row.get("progress"),
                    "case_reason": row.get("case_reason"),
                    "case_number": row.get("case_number"),
                    "opposing_party": row.get("opposing_party"),
                    "court": row.get("court"),
                    "division": row.get("division"),
                    "progress_date": _coerce_dt(row.get("progress_date")),
                    "progress_stages": row.get("progress_stages") or {},
                    "progress_notes": row.get("progress_notes") or {},
                    "progress_times": row.get("progress_times") or {},
                }

                stmt = pg_insert(tbl).values(**values)
                # 以 case_id 當唯一鍵更新（case_id 可能為 NULL，則行為是插入）
                stmt = stmt.on_conflict_do_update(
                    index_elements=["case_id"],
                    set_={
                        "case_type": stmt.excluded.case_type,
                        "client": stmt.excluded.client,
                        "lawyer": stmt.excluded.lawyer,
                        "legal_affairs": stmt.excluded.legal_affairs,
                        "progress": stmt.excluded.progress,
                        "case_reason": stmt.excluded.case_reason,
                        "case_number": stmt.excluded.case_number,
                        "opposing_party": stmt.excluded.opposing_party,
                        "court": stmt.excluded.court,
                        "division": stmt.excluded.division,
                        "progress_date": stmt.excluded.progress_date,
                        "progress_stages": stmt.excluded.progress_stages,
                        "progress_notes": stmt.excluded.progress_notes,
                        "progress_times": stmt.excluded.progress_times,
                        "updated_at": text("NOW()"),
                    }
                )
                conn.execute(stmt)
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"#{i} {repr(e)}")

    return {"summary": {"total": success + failed, "success": success, "failed": failed}, "errors": errors}
