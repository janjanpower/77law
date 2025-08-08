from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from database import get_db_connection  # 你要有連接 DB 的函式
from fastapi.responses import JSONResponse

router = APIRouter()

class BindRequest(BaseModel):
    user_id: str
    client_id: str

@router.post("/api/user/bind")
def bind_user(data: BindRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢目前綁定數量
    cursor.execute("SELECT COUNT(*) FROM tenant_users WHERE client_id = %s", (data.client_id,))
    bound_count = cursor.fetchone()[0]

    # 查詢使用上限
    cursor.execute("SELECT user_limit FROM login_users WHERE client_id = %s", (data.client_id,))
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_limit = result[0]

    if bound_count >= user_limit:
        return JSONResponse(status_code=400, content={"message": "綁定人數已達上限"})

    # 寫入新綁定
    cursor.execute(
        "INSERT INTO tenant_users (user_id, client_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (data.user_id, data.client_id)
    )
    conn.commit()

    return {"message": "綁定成功"}

@router.get("/api/user/bound-count")
def get_bound_count(client_id: str = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tenant_users WHERE client_id = %s", (client_id,))
    count = cursor.fetchone()[0]
    return {"bound_count": count}

@router.get("/api/user/bind/status")
def check_bind_status(user_id: str = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tenant_users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    return {"is_bound": result is not None}
