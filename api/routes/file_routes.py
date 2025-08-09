# -*- coding: utf-8 -*-
# 放在 api/routes/file_routes.py 內，或合併到你現有的檔案上傳路由中

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
import json, traceback

from api.database import get_db
from api.models_cases import CaseRecord

router = APIRouter(prefix="/api/files", tags=["files"])

# ------- 小工具 -------
def _get(d: Dict[str, Any], *names: str):
    for n in names:
        if isinstance(d, dict) and n in d and d[n] not in (None, "", "null"):
            return d[n]
    return None

def _ensure_case_table_and_columns(db: Session):
    try:
        engine = db.get_bind()
        insp = inspect(engine)
        if not insp.has_table("case_records"):
            CaseRecord.__table__.create(bind=engine, checkfirst=True)
        # 補欄位（只補可能缺的；已存在就略過）
        existing = {c["name"] for c in insp.get_columns("case_records")}
        add_sql = []
        def add(col, ddl):
            if col not in existing:
                add_sql.append(f"ADD COLUMN IF NOT EXISTS {col} {ddl}")
        for col in ["title","case_type","plaintiff","defendant","lawyer","legal_affairs",
                    "progress","case_reason","case_number","opposing_party","court",
                    "division","progress_date"]:
            add(col, "TEXT DEFAULT ''")
        if "progress_stages" not in existing: add_sql.append("ADD COLUMN IF NOT EXISTS progress_stages JSONB DEFAULT '{}'::jsonb")
        if "progress_notes"  not in existing: add_sql.append("ADD COLUMN IF NOT EXISTS progress_notes  JSONB DEFAULT '{}'::jsonb")
        if "progress_times"  not in existing: add_sql.append("ADD COLUMN IF NOT EXISTS progress_times  JSONB DEFAULT '{}'::jsonb")
        if add_sql:
            db.execute(text("ALTER TABLE case_records " + ", ".join(add_sql)))
        # created_at / updated_at
        if "created_at" not in existing:
            db.execute(text("ALTER TABLE case_records ADD COLUMN created_at timestamptz DEFAULT NOW()"))
        if "updated_at" not in existing:
            db.execute(text("ALTER TABLE case_records ADD COLUMN updated_at timestamptz DEFAULT NOW()"))
        db.commit()
    except Exception:
        traceback.print_exc()

def _upsert_case(db: Session, payload: Dict[str, Any]):
    """最小實作：把案件資料 upsert 進 case_records"""
    _ensure_case_table_and_columns(db)
    cid = str(payload["client_id"])
    caseid = str(payload["case_id"])

    obj = (
        db.query(CaseRecord)
          .filter(CaseRecord.client_id == cid, CaseRecord.case_id == caseid)
          .order_by(CaseRecord.id.desc())
          .first()
    )

    fields = {k: v for k, v in payload.items() if k not in ("client_id", "case_id") and v is not None}
    if obj:
        for k, v in fields.items():
            setattr(obj, k, v)
        db.add(obj); db.commit(); db.refresh(obj)
        action = "updated"
    else:
        obj = CaseRecord(client_id=cid, case_id=caseid, **fields)
        db.add(obj); db.commit(); db.refresh(obj)
        action = "created"
    return action, obj.id

# ------- 串接在你的檔案上傳端點 -------
@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    client_info: Optional[str] = Form(None),   # 前端可傳 JSON 字串
    case_data:   Optional[str] = Form(None),   # 前端可傳 JSON 字串
    client_id:   Optional[str] = Form(None),   # 也支援扁平欄位
    case_id:     Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    # 1) 解析 metadata
    ci = {}
    cd = {}
    try:
        if client_info: ci = json.loads(client_info) if isinstance(client_info, str) else client_info
    except Exception: pass
    try:
        if case_data:   cd = json.loads(case_data) if isinstance(case_data, str) else case_data
    except Exception: pass

    # 從多種位置找 client_id / case_id
    cid = client_id or _get(ci, "client_id","clientId","tenant_id","tenantId") or _get(await request.form(), "client_id")
    cno = case_id   or _get(cd, "case_id","caseId","case_no","caseNo","case_number","caseNumber","id","number","案號","案件編號")

    # 2) 若拿得到，就 upsert 進 case_records（檔案上傳前或後都可；這裡放前）
    upsert_info = None
    if cid and cno:
        body = {
            "client_id": str(cid),
            "case_id": str(cno),
            "title":           _get(cd, "title","subject","case_title","案件名稱"),
            "case_type":       _get(cd, "case_type","caseType","type","案件類型"),
            "plaintiff":       _get(cd, "plaintiff","原告"),
            "defendant":       _get(cd, "defendant","被告"),
            "lawyer":          _get(cd, "lawyer","attorney","律師"),
            "legal_affairs":   _get(cd, "legal_affairs","legalAffairs","assistant","助理"),
            "progress":        _get(cd, "progress","status","進度"),
            "case_reason":     _get(cd, "case_reason","reason","案由"),
            "case_number":     _get(cd, "case_number","caseNumber","docket_no","docketNo","字號"),
            "opposing_party":  _get(cd, "opposing_party","opposingParty","對造"),
            "court":           _get(cd, "court","法院"),
            "division":        _get(cd, "division","dept","股別"),
            "progress_date":   _get(cd, "progress_date","progressDate","進度日期"),
            "progress_stages": _get(cd, "progress_stages","progressStages"),
            "progress_notes":  _get(cd, "progress_notes","progressNotes"),
            "progress_times":  _get(cd, "progress_times","progressTimes"),
        }
        body = {k: v for k, v in body.items() if v is not None}
        action, rec_id = _upsert_case(db, {"client_id": str(cid), "case_id": str(cno), **body})
        upsert_info = {"action": action, "record_id": rec_id}
        print(">> files.upload upsert case:", upsert_info)
    else:
        print(">> files.upload no client_id/case_id found; skip case upsert")

    # 3) 照你原有邏輯上傳檔案 (以下是示意；把它換成你的 S3 邏輯)
    # ----------------------------------------------------------------
    # s3_url = await your_own_upload_s3_function(file)  # 你的既有程式
    # ----------------------------------------------------------------

    # 4) 回傳綜合結果（包含是否有 upsert 成功）
    return {
        "ok": True,
        "filename": file.filename,
        # "s3_url": s3_url,
        "case_upsert": upsert_info,
    }
