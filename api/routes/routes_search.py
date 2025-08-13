from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from api.deps import get_client_id
from api.tenant_db import get_tenant_session

router = APIRouter()

@router.get("/by-id/{case_id}")
def get_case_by_id(case_id: str, client_id: str = Depends(get_client_id)):
    session = get_tenant_session(client_id)
    try:
        stmt = text("SELECT * FROM case_records WHERE case_id = :case_id")
        row = session.execute(stmt, {"case_id": case_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        return dict(row)
    finally:
        session.close()

@router.get("/by-client/{client_name}")
def get_cases_by_client(client_name: str, client_id: str = Depends(get_client_id)):
    session = get_tenant_session(client_id)
    try:
        stmt = text("SELECT * FROM case_records WHERE client = :client_name")
        rows = session.execute(stmt, {"client_name": client_name}).fetchall()
        return [dict(r) for r in rows]
    finally:
        session.close()
