
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api.models_control import LoginUser, ClientLineUsers

def _is_bound_to_lawyer(db: Session, line_user_id: str) -> bool:
    if not line_user_id:
        return False
    row = db.query(ClientLineUsers).filter(
        ClientLineUsers.line_user_id == line_user_id,
        ClientLineUsers.is_active == True  # noqa: E712
    ).first()
    return bool(row)

def _lookup_client_by_code(db: Session, code: str) -> Optional[Dict[str, str]]:
    if not code:
        return None
    tenant = db.query(LoginUser).filter(
        and_(LoginUser.secret_code == code, LoginUser.is_active == True)  # noqa: E712
    ).first()
    if not tenant:
        return None
    return {
        "client_id": tenant.client_id,
        "client_name": tenant.client_name,
    }

def _bind_line_user_to_client(db: Session, line_user_id: str, tenant: Dict[str, str]) -> bool:
    if not tenant or not line_user_id:
        return False
    exists = db.query(ClientLineUsers).filter(
        ClientLineUsers.line_user_id == line_user_id
    ).first()
    if exists:
        return True
    db.add(ClientLineUsers(
        client_id=tenant["client_id"],
        line_user_id=line_user_id,
        is_active=True
    ))
    db.commit()
    return True
