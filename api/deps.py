from fastapi import Header, HTTPException, status

def get_client_id(x_client_id: str = Header(..., alias="X-Client-ID")) -> str:
    if not x_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Client-ID header is required")
    return x_client_id
