from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from api.deps import get_client_id
from api.tenant_db import get_tenant_session

router = APIRouter()

@router.post("/upload")
def upload_cases(items: list[dict], client_id: str = Depends(get_client_id)):
    if not items:
        raise HTTPException(status_code=400, detail="No data provided")
    
    session = get_tenant_session(client_id)
    try:
        for item in items:
            if "case_id" not in item:
                continue
            stmt = text("""
                INSERT INTO case_records (case_id, client, case_type, progress, progress_stages, progress_notes, progress_times, updated_at)
                VALUES (:case_id, :client, :case_type, :progress, :progress_stages, :progress_notes, :progress_times, NOW())
                ON CONFLICT (case_id) DO UPDATE SET
                    client = EXCLUDED.client,
                    case_type = EXCLUDED.case_type,
                    progress = EXCLUDED.progress,
                    progress_stages = EXCLUDED.progress_stages,
                    progress_notes = EXCLUDED.progress_notes,
                    progress_times = EXCLUDED.progress_times,
                    updated_at = NOW()
            """)
            session.execute(stmt, item)
        session.commit()
        return {"success": True, "message": f"{len(items)} records processed"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
