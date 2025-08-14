
# api/services/engagement_service.py
# 記錄使用者最後互動時間，並判斷是否超過閒置門檻

from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, Integer, String, DateTime, func, text
from sqlalchemy.orm import Session
from typing import Optional

try:
    from api.database import Base, ENGINE
except ImportError:
    from database import Base  # type: ignore

from sqlalchemy import inspect

# 動態宣告，避免修改既有 models_control 結構
class UserEngagement(Base):
    __tablename__ = 'user_engagements'
    id = Column(Integer, primary_key=True)
    line_user_id = Column(String(64), unique=True, index=True, nullable=False)
    last_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    last_reminded_at = Column(DateTime, nullable=True)

def _ensure_table_exists(db: Session):
    # 若資料表不存在則建立（避免強依賴 Alembic）
    inspector = inspect(db.bind)
    if 'user_engagements' not in inspector.get_table_names():
        # 用 Base.metadata.create_all 只創建當前 model 對應的表
        UserEngagement.__table__.create(bind=db.bind, checkfirst=True)

def touch_and_check_idle(db: Session, line_user_id: str, idle_minutes: int = 60) -> bool:
    """
    更新 last_seen_at；回傳是否「應提醒」（超過 idle_minutes，且尚未提醒或距上次提醒超過 idle_minutes）。
    """
    if not line_user_id:
        return False
    _ensure_table_exists(db)
    now = datetime.now(timezone.utc)
    row: Optional[UserEngagement] = db.query(UserEngagement).filter_by(line_user_id=line_user_id).first()
    should_remind = False
    if not row:
        row = UserEngagement(line_user_id=line_user_id, last_seen_at=now, last_reminded_at=None)
        db.add(row)
        db.commit(); db.refresh(row)
        return False

    # 計算是否超過 idle
    last_seen = row.last_seen_at if isinstance(row.last_seen_at, datetime) else now
    last_reminded = row.last_reminded_at
    idle_delta = now - (last_seen if last_seen.tzinfo else last_seen.replace(tzinfo=timezone.utc))
    if idle_delta >= timedelta(minutes=idle_minutes):
        # 若未提醒過，或距上次提醒又超過門檻，則應提醒
        if (last_reminded is None) or (now - (last_reminded if last_reminded.tzinfo else last_reminded.replace(tzinfo=timezone.utc)) >= timedelta(minutes=idle_minutes)):
            should_remind = True

    # 更新 last_seen_at
    row.last_seen_at = now
    db.add(row)
    db.commit()
    return should_remind

def mark_reminded(db: Session, line_user_id: str):
    _ensure_table_exists(db)
    now = datetime.now(timezone.utc)
    row: Optional[UserEngagement] = db.query(UserEngagement).filter_by(line_user_id=line_user_id).first()
    if row:
        row.last_reminded_at = now
        db.add(row)
        db.commit()
