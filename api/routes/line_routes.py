# api/routes/line_routes.py
# FastAPI routes for LINE/n8n integration
#
# - Replaces dependency on a non-existent "lawyers" table.
# - Uses existing tables: login_users (tenant), client_line_users (lawyer binding).
# - Removes any dependency on 'user_role' column.
# - Shapes responses to match your n8n "My workflow (6).json".
#
# Endpoints:
#   POST /api/lawyer/verify-secret
#   POST /api/line/resolve-route
#
# Assumptions:
#   - api.database.get_db returns a SQLAlchemy Session
#   - Tables exist:
#       public.login_users(client_id text, client_name text, secret_code text, is_active boolean, ...)
#       public.client_line_users(client_id text, line_user_id text unique, user_name text, is_active boolean, bound_at timestamptz, ...)
#   - If you allow one LINE user to bind multiple clients, change UNIQUE(line_user_id) to UNIQUE(client_id, line_user_id)
#     and update the ON CONFLICT clause accordingly (see comment below).

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from api.database import get_db  # adjust import if your path differs

router = APIRouter(prefix="/api", tags=["line"])


# =========================
# Helpers
# =========================

def _lookup_client_by_code(db: Session, code: str) -> Optional[dict]:
    """
    Interpret 'code' as one of (client_id | client_name | secret_code) in login_users.
    Returns dict(client_id, client_name) if matched.
    """
    code = (code or "").strip()
    if not code:
        return None

    sql = text("""
        SELECT client_id, client_name
        FROM public.login_users
        WHERE is_active = TRUE
          AND (
                client_id = :code
             OR client_name = :code
             OR COALESCE(secret_code, '') = :code
          )
        LIMIT 1
    """)
    row = db.execute(sql, {"code": code}).first()
    if row:
        return {"client_id": row[0], "client_name": row[1]}
    return None


def _bind_line_user_to_client(db: Session, line_user_id: str, client_id: str, user_name: Optional[str] = None) -> None:
    """
    Upsert binding into client_line_users by line_user_id.
    If you support multi-tenant bindings per LINE user, change UNIQUE to (client_id, line_user_id)
    and also change ON CONFLICT target below accordingly.
    """
    sql = text("""
        INSERT INTO public.client_line_users (client_id, line_user_id, user_name, is_active, bound_at)
        VALUES (:client_id, :lid, :user_name, TRUE, NOW())
        ON CONFLICT (line_user_id)
        DO UPDATE SET
            client_id = EXCLUDED.client_id,
            user_name = COALESCE(EXCLUDED.user_name, public.client_line_users.user_name),
            is_active = TRUE,
            bound_at = NOW()
    """)
    db.execute(sql, {"client_id": client_id, "lid": line_user_id, "user_name": user_name})
    db.commit()


def _is_bound_to_lawyer(db: Session, line_user_id: str) -> bool:
    """
    Determine whether this LINE user is already bound to a lawyer (client) via client_line_users.
    No user_role column involved.
    """
    sql = text("""
        SELECT 1
        FROM public.client_line_users
        WHERE line_user_id = :lid
          AND is_active = TRUE
        LIMIT 1
    """)
    return bool(db.execute(sql, {"lid": line_user_id}).first())


# =========================
# Schemas
# =========================

class VerifySecretIn(BaseModel):
    text: str
    line_user_id: str
    client_name: Optional[str] = None  # Optional, e.g. the display name user typed


class VerifySecretOut(BaseModel):
    success: bool
    is_secret: bool
    is_lawyer: bool
    client_name: Optional[str] = None
    client_id: Optional[str] = None
    action: Optional[str] = None   # e.g., "BIND_OK"
    message: Optional[str] = None


class ResolveRouteIn(BaseModel):
    is_secret: Optional[bool] = None
    is_lawyer: Optional[bool] = None
    client_name: Optional[str] = None
    line_user_id: str
    text: Optional[str] = None


class ResolveRouteOut(BaseModel):
    route: str                  # "AUTH" | "GUEST"
    action: Optional[str] = None  # "BIND_OK" | "LAWYER_QUERY" | "QUERY"
    message: Optional[str] = None


# =========================
# Routes
# =========================

@router.post("/lawyer/verify-secret", response_model=VerifySecretOut)
def verify_secret(payload: VerifySecretIn, db: Session = Depends(get_db)):
    """
    First step in n8n:
      - Input: {"text": "<code>", "line_user_id": "...", "client_name": "...?"}
      - Behavior:
          * If 'text' matches a tenant in login_users (by client_id/client_name/secret_code):
              - Bind line_user_id into client_line_users
              - Return {success:true, is_secret:true, is_lawyer:true, action:"BIND_OK", ...}
          * Else:
              - Return {success:true, is_secret:false, is_lawyer:<current binding>, message:"不是合法暗號"}
    """
    code = (payload.text or "").strip()
    # current bound state (even if not secret)
    already_bound = _is_bound_to_lawyer(db, payload.line_user_id)

    if not code:
        return VerifySecretOut(
            success=True,
            is_secret=False,
            is_lawyer=already_bound,
            message="空白輸入"
        )

    tenant = _lookup_client_by_code(db, code)
    if not tenant:
        return VerifySecretOut(
            success=True,
            is_secret=False,
            is_lawyer=already_bound,
            message="不是合法暗號"
        )

    # Secret matched -> bind
    _bind_line_user_to_client(
        db=db,
        line_user_id=payload.line_user_id,
        client_id=tenant["client_id"],
        user_name=payload.client_name
    )

    return VerifySecretOut(
        success=True,
        is_secret=True,
        is_lawyer=True,
        client_name=tenant["client_name"],
        client_id=tenant["client_id"],
        action="BIND_OK",
        message=f"綁定成功！已綁定至「{tenant['client_name']}」。之後輸入「?」可查看操作選項。"
    )


@router.post("/line/resolve-route", response_model=ResolveRouteOut)
def resolve_route(p: ResolveRouteIn, db: Session = Depends(get_db)):
    """
    Second step in n8n:
      - Input: {
          "is_secret": <bool>,  // from verify-secret
          "is_lawyer": <bool>,  // from verify-secret or unknown
          "client_name": "...",
          "line_user_id": "...",
          "text": "?" | "<person name>" | "..."
        }
      - Behavior:
          * If is_secret==true and is_lawyer==true -> BIND_OK
          * If (bound as lawyer):
                - text == "?"           -> QUERY (user's own cases)
                - otherwise (any text)  -> LAWYER_QUERY (query by person name)
          * Else -> GUEST
    """
    text_in = (p.text or "").strip()

    # Case 1: just bound via verify-secret
    if p.is_secret is True and p.is_lawyer is True:
        return ResolveRouteOut(route="AUTH", action="BIND_OK", message="綁定完成")

    # Case 2: lawyer bound
    bound = p.is_lawyer if p.is_lawyer is not None else _is_bound_to_lawyer(db, p.line_user_id)
    if bound:
        if text_in == "?":
            # user wants his/her own cases
            return ResolveRouteOut(route="AUTH", action="QUERY", message="查詢個人案件")
        else:
            # default route for lawyers: query by a person's name
            return ResolveRouteOut(route="AUTH", action="LAWYER_QUERY", message="律師查詢案件")

    # Case 3: guest (not bound)
    return ResolveRouteOut(route="GUEST", message="未綁定，請輸入「登錄 您的大名」或提供事務所暗號")


line_router = router
__all__ = ["line_router"]