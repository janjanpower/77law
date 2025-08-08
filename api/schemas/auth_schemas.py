# schemas/auth_schemas.py

from pydantic import BaseModel

class ClientLoginRequest(BaseModel):
    client_id: str
    password: str

class ClientLoginResponse(BaseModel):
    client_name: str
    plan_type: str
    max_users: int
    current_users: int
