# api/routes/user_routes.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, true, or_
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging, traceback, re, json

from sqlalchemy.sql import func

from api.database import get_db
from api.models_control import ClientLineUsers
from api.models_cases import CaseRecord  # ORM for cases

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

user_router = APIRouter(prefix="/api/user", tags=["user"])

# -------------------- Pydantic --------------------
class LookupIn(BaseModel):
    line_user_id: Optional[str] = None
    user_name:   Optional[str] = None
    destination: Optional[str] = None
    text:        Optional[str] = None  # 可有可無

    class Config:
        allow_population_by_field_name = True

class LookupOut(BaseModel):
    client_id: Optional[str] = None

class RegisterIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    user_name:   Optional[str] = None
    client_id:   Optional[str] = None
    text:        Optional[str] = None
    destination: Optional[str] = None  # 相容舊流程（原始文字）

class RegisterOut(BaseModel):
    success: bool
    message: str
    expected_name: Optional[str] = None
    cases: Optional[List[Dict[str, Any]]] = None

class MyCasesIn(BaseModel):
    line_user_id: str
    include_as_opponent: Optional[bool] = False  # 是否把對造人也算進來（預設關閉）

class MyCasesOut(BaseModel):
    success: bool
    message: str
    count: Optional[int] = None
    name: Optional[str] = None


# -------------------- Helpers --------------------
def _parse_intent(text_msg: str):
    msg = (text_msg or "").strip()
    if not msg:
        return "none", None
    m = re.match(r"^(?:登錄|登陸|登入|登录)\s*(.+)$", msg, flags=re.I)
    if m:
        return "prepare", m.group(1).strip()
    if msg in ("是","yes","Yes","YES"): return "confirm_yes", None
    if msg in ("否","no","No","NO"):   return "confirm_no", None
    if msg in ("?","？"):               return "show_cases", None
    return "none", None


def _fmt_dt(v):
    if not v:
        return "-"
    if isinstance(v, str):
        return v[:19].replace("T", " ")
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)


def _fmt_stages(progress_stages):
    """
    progress_stages may be:
    - JSON string like {"偵查中": "2025-08-10", "準備程序": "2025-09-01"}
    - Python dict already
    - empty / None
    """
    if not progress_stages:
        return "尚無進度階段記錄"
    try:
        data = progress_stages
        if isinstance(progress_stages, str):
            data = json.loads(progress_stages)
        if isinstance(data, dict) and data:
            lines = [f"．{k}：{v}" for k, v in data.items()]
            return "\n".join(lines)
        return "尚無進度階段記錄"
    except Exception:
        return str(progress_stages)


def render_case_detail(case) -> str:
    """
    Render ONE case to LINE text matching your screenshot style.
    '案件資料夾' section is kept but commented out for now.
    """
    case_number   = case.case_number or case.case_id or "-"
    client        = case.client or "-"
    case_type     = case.case_type or "-"
    case_reason   = case.case_reason or "-"
    court         = case.court or "-"
    division      = case.division or "-"
    legal_affairs = getattr(case, "legal_affairs", None) or "-"
    opposing      = case.opposing_party or "-"
    progress      = case.progress or "待處理"
    stages_text   = _fmt_stages(getattr(case, "progress_stages", None))
    created_at    = _fmt_dt(getattr(case, "created_date", None))
    updated_at    = _fmt_dt(getattr(case, "updated_date", None) or getattr(case, "updated_at", None))

    lines = []
    lines.append("ℹ️ 案件詳細資訊")
    lines.append("────────────────────")
    lines.append(f"📌 案件編號：{case_number}")
    lines.append(f"👤 當事人：{client}")
    lines.append("────────────────────")
    lines.append(f"案件類型：{case_type}")
    lines.append(f"案由：{case_reason}")
    lines.append(f"法院：{court}")
    lines.append(f"法務：{legal_affairs}")
    lines.append(f"對造：{opposing}")
    lines.append(f"負責股別：{division}")
    lines.append("────────────────────")
    lines.append("📈 案件進度歷程：")
    lines.append(stages_text)
    lines.append(f"⚠️ 最新進度：{progress}")
    lines.append("────────────────────")
    lines.append("📁 案件資料夾：")
    # lines.append("🔢 輸入編號瀏覽（1–2）檔案")   # ← 之後開啟時再把這些註解移除
    # lines.append("")
    # lines.append("  1. 案件資訊（2 個檔案）")
    # lines.append("  2. 進度總覽（1 個檔案）")
    lines.append("（稍後開放）")  # 目前先顯示提示
    lines.append("────────────────────")
    lines.append(f"⌛ 建立時間：{created_at}")
    lines.append(f"🛠 更新時間：{updated_at}")

    return "\n".join(lines)


def render_cases_list(cases) -> str:
    """Render multiple cases by concatenating blocks with a blank line between."""
    return "\n\n".join(render_case_detail(c) for c in cases)


# ==================================================
# 1) 依 LINE 或姓名查 client_id（給 n8n 的「查 client_id」節點）
# ==================================================
@user_router.post("/lookup-client", response_model=LookupOut)
def lookup_client(payload: LookupIn, db: Session = Depends(get_db)):
    line_user_id = (payload.line_user_id or "").strip()
    user_name    = (payload.user_name   or "").strip()
    destination  = (payload.destination or "").strip()

    # 0) 先試：用 LINE Webhook 的 destination 直接映射到事務所
    if destination:
        row = db.execute(text("""
            SELECT client_id
            FROM line_channel_bindings
            WHERE destination_id = :dest AND is_active = TRUE
            LIMIT 1
        """), {"dest": destination}).first()
        if row and row[0]:
            return {"client_id": row[0]}

    # 1) 其次：line_user_id 是否已綁定
    row = db.execute(text("""
        SELECT client_id
        FROM client_line_users
        WHERE line_user_id = :lid AND is_active = TRUE
        LIMIT 1
    """), {"lid": line_user_id}).first()
    if row and row[0]:
        return {"client_id": row[0]}

    # 2) 最後保底：把「登錄 」前綴去掉再對 login_users
    name = re.sub(r"^(?:登錄|登陸|登入|登录)\s+", "", user_name).strip()
    row = db.execute(text("""
        SELECT client_id
        FROM login_users
        WHERE client_name = :name
          AND is_active = TRUE
        LIMIT 1
    """), {"name": name}).first()

    return {"client_id": row[0] if row else None}


# ==================================================
# 2) 註冊（n8n 的「用戶確認註冊」會呼叫）
# ==================================================
@user_router.post("/register", response_model=RegisterOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        lid     = (payload.line_user_id or "").strip()
        # 注意：這裡先不要信任 user_name，只有在「登錄 XXX」被辨識時才採用
        name_in = (payload.user_name   or "").strip()
        cid     = (payload.client_id   or "").strip()
        text_in = (payload.text        or "").strip()
        dest    = (payload.destination or "").strip()

        # 0) 先回推 client_id（destination → client_id；或從既有綁定表）
        if not cid and dest:
            row = db.execute(text("""
                SELECT client_id FROM line_channel_bindings
                WHERE destination_id = :dest AND is_active = TRUE
                LIMIT 1
            """), {"dest": dest}).first()
            if row and row[0]:
                cid = row[0]
        if not cid and lid:
            row = db.execute(text("""
                SELECT client_id FROM client_line_users
                WHERE line_user_id = :lid AND is_active = TRUE
                LIMIT 1
            """), {"lid": lid}).first()
            if row and row[0]:
                cid = row[0]

        # 1) 解析意圖
        intent, cname = _parse_intent(text_in)  # prepare / confirm_yes / confirm_no / show_cases / none

        # 1a) 使用者說了「登錄 XXX」=> 建立/更新 pending，但不立刻註冊
        if intent == "prepare" and cname:
            candidate = re.sub(r"^(?:登錄|登陸|登入|登录)\s+", "", cname).strip()

            # 以 line_user_id 為唯一鍵，寫入「候選姓名」與 pending 狀態；client_id 有就一併帶上
            db.execute(text("""
                INSERT INTO pending_line_users (line_user_id, client_id, expected_name, status, created_at, updated_at)
                VALUES (:lid, NULLIF(:cid,''), :name, 'pending', NOW(), NOW())
                ON CONFLICT (line_user_id)
                DO UPDATE
                SET expected_name = :name,
                    client_id     = COALESCE(pending_line_users.client_id, NULLIF(:cid,'')),
                    status        = 'pending',
                    updated_at    = NOW();
            """), {"lid": lid, "cid": cid, "name": candidate})
            db.commit()

            return RegisterOut(
                success=True,
                expected_name=candidate,
                message=f"請確認您的大名：{candidate}\n回覆「是」確認，回覆「否」重新輸入。"
            )

        # 1b) 使用者回「是」=> 將 pending → registered，必要時回填 client_id
        if intent == "confirm_yes":
            row = db.execute(text("""
                SELECT expected_name, client_id
                FROM pending_line_users
                WHERE line_user_id = :lid
                ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
                LIMIT 1
            """), {"lid": lid}).first()
            if not row or not row[0]:
                return RegisterOut(success=False, message="尚未收到您的大名，請輸入「登錄 您的大名」。")

            final_name, existed_cid = row[0], row[1]
            if cid and (existed_cid is None or existed_cid == ""):
                existed_cid = cid

            # 轉正：registered；僅在 client_id 為空時回填
            db.execute(text("""
                UPDATE pending_line_users
                SET status = 'registered',
                    client_id = COALESCE(client_id, NULLIF(:cid,'')),
                    updated_at = NOW()
                WHERE line_user_id = :lid
            """), {"cid": existed_cid or "", "lid": lid})
            db.commit()

            return RegisterOut(
                success=True,
                expected_name=final_name,
                message=f"歡迎 {final_name}！已完成登錄。\n輸入「?」即可查詢您的案件進度。"
            )

        # 1c) 使用者回「否」=> 清掉候選姓名，維持 pending，請他重輸入
        if intent == "confirm_no":
            db.execute(text("""
                UPDATE pending_line_users
                SET expected_name = NULL,
                    status        = 'pending',
                    updated_at    = NOW()
                WHERE line_user_id = :lid
            """), {"lid": lid})
            db.commit()
            return RegisterOut(success=True, message="好的，請重新輸入「登錄 您的大名」。")

        # 1d) 其他文字：不做任何寫入；回引導訊息
        row = db.execute(text("""
            SELECT status FROM pending_line_users
            WHERE line_user_id = :lid
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            LIMIT 1
        """), {"lid": lid}).first()
        if row and row[0] == "registered":
            return RegisterOut(success=True, message="已登錄，用「?」可查詢您的案件。")
        else:
            return RegisterOut(success=False, message="您好，請輸入「登錄 您的大名」完成登錄。")

    except Exception as e:
        db.rollback()
        logger.error(f"/register 失敗: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="REG_500: 系統錯誤")


# ==================================================
# 3) 查個人案件（n8n 的「?」分支）— 單租戶：只用 client 欄位；統一回覆樣式
# ==================================================
@user_router.post("/my-cases")
def my_cases(payload: MyCasesIn, db: Session = Depends(get_db)):
    lid = (payload.line_user_id or "").strip()
    if not lid:
        raise HTTPException(status_code=400, detail="line_user_id 必填")

    # 1) 取使用者已確認的姓名（以 pending_line_users 的 registered 狀態為準）
    row = db.execute(text("""
        SELECT expected_name
        FROM pending_line_users
        WHERE line_user_id = :lid
          AND status = 'registered'
          AND expected_name IS NOT NULL
        ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
        LIMIT 1
    """), {"lid": lid}).first()

    if not row or not row[0]:
        return {"ok": False, "message": "尚未登錄，請輸入「登錄 您的大名」完成登錄。"}

    user_name = row[0].strip()
    if not user_name:
        return {"ok": False, "message": "目前查無姓名資訊，請輸入「登錄 您的大名」。"}

    # 2) 只用當事人姓名查 case_records.client（可選含對造）
    if payload.include_as_opponent:
        q = (
            db.query(CaseRecord)
            .filter(or_(CaseRecord.client == user_name, CaseRecord.opposing_party == user_name))
        )
    else:
        q = db.query(CaseRecord).filter(CaseRecord.client == user_name)

    q = q.order_by(text("updated_date DESC NULLS LAST, updated_at DESC NULLS LAST, id DESC")).limit(50)
    rows: List[CaseRecord] = q.all()

    if not rows:
        return {"ok": True, "total": 0, "message": f"沒有找到「{user_name}」的案件。"}

    # 統一樣式輸出（多筆皆顯示）
    msg = render_cases_list(rows)
    # 若想只回最新一筆，改為：
    # msg = render_case_detail(rows[0])

    return {"ok": True, "total": len(rows), "message": msg}


@user_router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_routes", "timestamp": datetime.utcnow().isoformat()}

# 供 main.py 引用
router = user_router
