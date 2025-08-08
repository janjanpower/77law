# api/routes/data_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session
from contextlib import contextmanager
from database import DATABASE_URL, SessionLocal

router = APIRouter()

class AddRecordRequest(BaseModel):
    schema_name: str
    user_id: int
    type: str
    content: str

@contextmanager
def get_tenant_session(schema_name: str):
    engine = create_engine(DATABASE_URL)
    session = Session(bind=engine)
    try:
        session.execute(text(f"SET search_path TO {schema_name}"))
        yield session
    finally:
        session.close()

@router.post("/add-record")
def add_record(req: AddRecordRequest):
    # 驗證 schema 是否存在
    db = SessionLocal()
    tenant = db.query(Tenant).filter_by(schema_name=req.schema_name).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租戶不存在")

    # 插入資料記錄
    with get_tenant_session(req.schema_name) as session:
        session.execute(
            text("""
                INSERT INTO data_records (user_id, type, content)
                VALUES (:user_id, :type, :content)
            """),
            {
                "user_id": req.user_id,
                "type": req.type,
                "content": req.content
            }
        )
        session.commit()

    return {"message": "✅ 資料記錄新增成功"}
