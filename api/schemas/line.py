
from typing import Optional
from pydantic import BaseModel

# 入參：驗證暗號
class VerifySecretIn(BaseModel):
    text: Optional[str] = None
    line_user_id: str

# 出參：驗證暗號結果
class VerifySecretOut(BaseModel):
    success: bool = True
    is_secret: bool = False
    is_lawyer: bool = False
    route: str = "USER"          # "USER" | "LOGIN" | "SEARCH" | "REGISTER"
    message: str = ""
    # 如果是有效 tenant 可能會帶出來
    client_name: Optional[str] = None
    client_id: Optional[str] = None

# 入參：解析路由
class ResolveRouteIn(BaseModel):
    text: Optional[str] = None
    is_secret: bool = False
    is_lawyer: bool = False
    line_user_id: str

# 出參：解析路由結果
class ResolveRouteOut(BaseModel):
    route: str
    message: str = ""
