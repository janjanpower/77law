# api/routes/line_routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Literal

line_router = APIRouter(prefix="/api/line", tags=["line"])

class ResolveRouteIn(BaseModel):
    is_secret: bool = False
    is_lawyer: bool = False
    client_name: Optional[str] = None
    line_user_id: Optional[str] = None
    text: Optional[str] = None

class ResolveRouteOut(BaseModel):
    route: Literal["LAWYER", "LOGIN", "USER"]
    success: bool
    is_lawyer: bool
    client_name: Optional[str] = None

@line_router.post("/resolve-route", response_model=ResolveRouteOut)
def resolve_route(p: ResolveRouteIn):
    if p.is_secret and p.is_lawyer:
        route = "LAWYER"
    elif p.is_secret and not p.is_lawyer:
        route = "LOGIN"
    else:
        route = "USER"
    return ResolveRouteOut(
        route=route,
        success=bool(p.is_secret),
        is_lawyer=bool(p.is_lawyer),
        client_name=p.client_name,
    )
