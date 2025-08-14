# api/routes/user_routes.py
# -*- coding: utf-8 -*-
"""
LINE 一般用戶/律師查案路由（單租戶版）
- 一般用戶「?」查詢：
  • 只有 1 件 → 直接回「案件詳細資訊」卡片
  • 超過 1 件 → 先出「案件類別選單」（刑事/民事/其他），再列出該類別清單，最後回單筆詳細
- 「案件資料夾」區塊先保留為註解（未啟用）
- 簡單會話暫存：user_query_sessions（TTL 預設 30 分鐘），過期自清、同 scope 只留最新、用後即刪
"""

import logging, traceback, re, json, os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4

from api.database import get_db
from api.models_cases import CaseRecord  # 你專案的案件 ORM
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text, or_
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

user_router = APIRouter(prefix="/api/user", tags=["user"])

# ============================ 可調參數 ============================
# 選單有效時間（分鐘），可用環境變數 UQS_TTL_MINUTES 覆寫
SESSION_TTL_MINUTES = int(os.getenv("UQS_TTL_MINUTES", "30"))

# ============================ Pydantic ============================
class LookupIn(BaseModel):
    line_user_id: Optional[str] = None
    user_name:   Optional[str] = None
    destination: Optional[str] = None
    text:        Optional[str] = None

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

class ChooseCategoryIn(BaseModel):
    line_user_id: str
    session_key: str
    choice: int  # 1,2,...

class ChooseCaseIn(BaseModel):
    line_user_id: str
    session_key: str
    choice: int  # 1..N

# ============================ Helpers ============================
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
    progress_stages:
    - JSON string like {"偵查中": "2025-08-10"}
    - dict
    - None / ""
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
    單筆案件輸出樣式（符合你給的截圖）
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
    lines.append("（稍後開放）")
    lines.append("────────────────────")
    lines.append(f"⌛ 建立時間：{created_at}")
    lines.append(f"🛠 更新時間：{updated_at}")
    return "\n".join(lines)

def render_cases_list(cases) -> str:
    """多筆案件連續輸出（若要一次回多筆詳細）"""
    return "\n\n".join(render_case_detail(c) for c in cases)

# —— 案件類別歸一：回 (key, label)
def _type_key_label(case_type: Optional[str]) -> Tuple[str, str]:
    t = (case_type or "").strip()
    if "刑" in t:
        return "CRIM", "刑事"
    if "民" in t:
        return "CIVIL", "民事"
    return "OTHER", "其他"

def _render_category_menu(menu_items: List[Dict[str, Any]], session_key: str) -> str:
    """
    menu_items: [{"key":"CRIM","label":"刑事","count":N}, ...]（只列有資料的）
    """
    lines = []
    lines.append("🗂 案件類別選單")
    lines.append("────────────────────")
    for i, m in enumerate(menu_items, 1):
        lines.append(f"{i}. {m['label']}案件列表（{m['count']} 件）")
    lines.append("")
    lines.append(f"💡 請輸入選項號碼 (1-{len(menu_items)})")
    lines.append(f"#KEY:{session_key}")  # 讓 n8n 從訊息中擷取 session_key
    return "\n".join(lines)

def _render_case_brief_list(items: List[Dict[str, Any]], label: str, session_key: str) -> str:
    """
    items: [{"id":..., "case_number":..., "case_reason":..., "case_type":..., "updated_at":...}, ...]
    """
    lines = []
    lines.append(f"📂 {label}案件列表")
    lines.append("────────────────────")
    for i, it in enumerate(items, 1):
        num = it.get("case_number") or "-"
        reason = it.get("case_reason") or "-"
        lines.append(f"{i}. {reason}（案件編號：{num}）")
    lines.append("")
    lines.append(f"💡 請輸入選項號碼 (1-{len(items)})")
    return "\n".join(lines)

# ============================ 會話暫存：清理策略 ============================
def _cleanup_expired_sessions(db: Session, line_user_id: Optional[str] = None):
    # 刪過期的（全部或指定用戶）
    params = {"ttl": SESSION_TTL_MINUTES}
    where_user = ""
    if line_user_id:
        where_user = "AND line_user_id = :lid"
        params["lid"] = line_user_id
    db.execute(
        text(f"""
        DELETE FROM user_query_sessions
        WHERE created_at < NOW() - (CAST(:ttl AS TEXT) || ' minutes')::interval
        {where_user}
        """),
        params,
    )
    db.commit()

def _save_session(db: Session, line_user_id: str, scope: str, payload: Dict[str, Any]) -> str:
    # 逾時自清 + 同 scope 只留最新
    _cleanup_expired_sessions(db, line_user_id)
    db.execute(
        text("""DELETE FROM user_query_sessions WHERE line_user_id = :lid AND scope = :scope"""),
        {"lid": line_user_id, "scope": scope},
    )
    skey = str(uuid4())
    db.execute(
        text("""
        INSERT INTO user_query_sessions (line_user_id, session_key, scope, payload_json)
        VALUES (:lid, :skey, :scope, :payload)
        """),
        {"lid": line_user_id, "skey": skey, "scope": scope, "payload": json.dumps(payload, ensure_ascii=False)},
    )
    db.commit()
    return skey

def _load_session(db: Session, line_user_id: str, session_key: str) -> Dict[str, Any]:
    _cleanup_expired_sessions(db, line_user_id)
    row = db.execute(
        text("""SELECT scope, payload_json, created_at
                FROM user_query_sessions
                WHERE line_user_id = :lid AND session_key = :skey
                ORDER BY created_at DESC LIMIT 1"""),
        {"lid": line_user_id, "skey": session_key},
    ).first()
    if not row:
        raise HTTPException(status_code=400, detail="選單已失效，請重新輸入「?」")
    scope, payload, created_at = row[0], row[1], row[2]
    if isinstance(payload, str):
        payload = json.loads(payload)
    # 再檢查 TTL（避免 race）
    ttl_ok = db.execute(
        text("""SELECT (NOW() - :created_at) <= (CAST(:ttl AS TEXT) || ' minutes')::interval"""),
        {"created_at": created_at, "ttl": SESSION_TTL_MINUTES},
    ).scalar()
    if not ttl_ok:
        db.execute(
            text("""DELETE FROM user_query_sessions WHERE line_user_id = :lid AND session_key = :skey"""),
            {"lid": line_user_id, "skey": session_key},
        )
        db.commit()
        raise HTTPException(status_code=400, detail="選單已過期，請重新輸入「?」")
    return {"scope": scope, "payload": payload}

def _consume_session(db: Session, line_user_id: str, session_key: str):
    db.execute(
        text("""DELETE FROM user_query_sessions WHERE line_user_id = :lid AND session_key = :skey"""),
        {"lid": line_user_id, "skey": session_key},
    )
    db.commit()

# ============================ 1) 查 client_id（n8n 用） ============================
@user_router.post("/lookup-client", response_model=LookupOut)
def lookup_client(payload: LookupIn, db: Session = Depends(get_db)):
    line_user_id = (payload.line_user_id or "").strip()
    user_name    = (payload.user_name   or "").strip()
    destination  = (payload.destination or "").strip()

    # 先用 LINE destination 找事務所
    if destination:
        row = db.execute(text("""
            SELECT client_id
            FROM line_channel_bindings
            WHERE destination_id = :dest AND is_active = TRUE
            LIMIT 1
        """), {"dest": destination}).first()
        if row and row[0]:
            return {"client_id": row[0]}

    # 其次：line_user_id 是否已在綁定表
    row = db.execute(text("""
        SELECT client_id
        FROM client_line_users
        WHERE line_user_id = :lid AND is_active = TRUE
        LIMIT 1
    """), {"lid": line_user_id}).first()
    if row and row[0]:
        return {"client_id": row[0]}

    # 最後保底：把「登錄 」前綴去掉再對 login_users.client_name
    name = re.sub(r"^(?:登錄|登陸|登入|登录)\s+", "", user_name).strip()
    row = db.execute(text("""
        SELECT client_id
        FROM login_users
        WHERE client_name = :name
          AND is_active = TRUE
        LIMIT 1
    """), {"name": name}).first()

    return {"client_id": row[0] if row else None}

# ============================ 2) 註冊（登錄/確認） ============================
@user_router.post("/register", response_model=RegisterOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        lid     = (payload.line_user_id or "").strip()
        name_in = (payload.user_name   or "").strip()
        cid     = (payload.client_id   or "").strip()
        text_in = (payload.text        or "").strip()
        dest    = (payload.destination or "").strip()

        # 回推 client_id（destination → client_id；或從既有綁定表）
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

        # 解析意圖
        intent, cname = _parse_intent(text_in)  # prepare / confirm_yes / confirm_no / show_cases / none

        # 使用者說了「登錄 XXX」=> 寫/更新 pending（不立刻成為正式）
        if intent == "prepare" and cname:
            candidate = re.sub(r"^(?:登錄|登陸|登入|登录)\s+", "", cname).strip()
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

        # 使用者回「是」=> 將 pending → registered
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

        # 使用者回「否」=> 清掉候選姓名，維持 pending
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

        # 其他文字：僅提示
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

# ============================ 3) ? 查個人案件（>1 先選類別） ============================
@user_router.post("/my-cases")
def my_cases(payload: MyCasesIn, db: Session = Depends(get_db)):
    lid = (payload.line_user_id or "").strip()
    if not lid:
        raise HTTPException(status_code=400, detail="line_user_id 必填")

    # 取使用者已確認的姓名（pending_line_users 裡 status='registered'）
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

    # 只用當事人姓名查 case_records.client（可選含對造）
    if payload.include_as_opponent:
        q = db.query(CaseRecord).filter(
            or_(CaseRecord.client == user_name, CaseRecord.opposing_party == user_name)
        )
    else:
        q = db.query(CaseRecord).filter(CaseRecord.client == user_name)

    q = q.order_by(text("updated_date DESC NULLS LAST, updated_at DESC NULLS LAST, id DESC"))
    rows: List[CaseRecord] = q.all()

    if not rows:
        return {"ok": True, "total": 0, "message": f"沒有找到「{user_name}」的案件。"}

    if len(rows) == 1:
        # 只有 1 件 → 直接詳細
        return {"ok": True, "total": 1, "message": render_case_detail(rows[0])}

    # 多件 → 依類別歸群
    buckets: Dict[str, Dict[str, Any]] = {}  # key -> {"label":..., "items":[...] }
    for r in rows:
        key, label = _type_key_label(r.case_type)
        buckets.setdefault(key, {"label": label, "items": []})
        buckets[key]["items"].append({
            "id": r.id,
            "case_number": r.case_number or r.case_id,
            "case_reason": r.case_reason,
            "case_type": r.case_type,
            "updated_at": _fmt_dt(getattr(r, "updated_date", None) or getattr(r, "updated_at", None))
        })

    types_present = [k for k in ["CRIM", "CIVIL", "OTHER"] if k in buckets]
    if len(types_present) >= 2:
        # 類別選單
        menu_items = [{"key": k, "label": buckets[k]["label"], "count": len(buckets[k]["items"])}
                      for k in types_present]
        skey = _save_session(
            db, lid, "category_menu",
            {"menu": menu_items, "by_type": buckets}
        )
        msg = _render_category_menu(menu_items, skey)
        return {"ok": True, "total": len(rows), "message": msg}

    # 只剩一種類別 → 直接列出該類別清單
    only_key = types_present[0]
    items = buckets[only_key]["items"]
    label = buckets[only_key]["label"]
    skey = _save_session(
        db, lid, f"case_list:{only_key}",
        {"label": label, "items": items}
    )
    msg = _render_case_brief_list(items, label, skey)
    return {"ok": True, "total": len(rows), "message": msg}

# ============================ 4) 選了「類別」 → 回該類別清單 ============================
@user_router.post("/choose-category")
def choose_category(payload: ChooseCategoryIn, db: Session = Depends(get_db)):
    lid  = (payload.line_user_id or "").strip()
    skey = (payload.session_key or "").strip()
    idx  = int(payload.choice)

    sess = _load_session(db, lid, skey)
    # 用後即刪舊類別選單
    _consume_session(db, lid, skey)

    if sess["scope"] != "category_menu":
        raise HTTPException(status_code=400, detail="選單已失效，請重新輸入「?」")

    menu   = sess["payload"]["menu"]
    bytype = sess["payload"]["by_type"]

    if not (1 <= idx <= len(menu)):
        raise HTTPException(status_code=400, detail="選項超出範圍")

    chosen = menu[idx - 1]  # {"key": "...", "label": "...", "count": ...}
    key = chosen["key"]
    bucket = bytype[key]
    items = bucket["items"]
    label = bucket["label"]

    # 開新列表 session
    new_key = _save_session(db, lid, f"case_list:{key}", {"label": label, "items": items})
    msg = _render_case_brief_list(items, label, new_key)
    return {"ok": True, "total": len(items), "message": msg}

# ============================ 5) 選了清單中的案件 → 回單筆詳細 ============================
@user_router.post("/choose-case")
def choose_case(payload: ChooseCaseIn, db: Session = Depends(get_db)):
    lid  = (payload.line_user_id or "").strip()
    skey = (payload.session_key or "").strip()
    idx  = int(payload.choice)

    sess = _load_session(db, lid, skey)
    # 用後即刪案件列表選單
    _consume_session(db, lid, skey)

    if not sess["scope"].startswith("case_list:"):
        raise HTTPException(status_code=400, detail="列表已失效，請重新輸入「?」")

    items = sess["payload"]["items"]
    if not (1 <= idx <= len(items)):
        raise HTTPException(status_code=400, detail="選項超出範圍")

    case_id = items[idx - 1]["id"]
    case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在或已移除")

    return {"ok": True, "message": render_case_detail(case)}


# ========= NEW: 6) 單一選單選擇端點（自動判斷類別選單/案件列表） =========
class MenuSelectIn(BaseModel):
    line_user_id: str
    choice: int  # 1..N

@user_router.post("/menu-select")
def menu_select(payload: MenuSelectIn, db: Session = Depends(get_db)):
    lid  = (payload.line_user_id or "").strip()
    idx  = int(payload.choice)

    # 抓該用戶最近一筆未過期的選單
    row = db.execute(
        text(f"""
            SELECT session_key, scope, payload_json, created_at
            FROM user_query_sessions
            WHERE line_user_id = :lid
              AND created_at >= NOW() - (CAST(:ttl AS TEXT) || ' minutes')::interval
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"lid": lid, "ttl": SESSION_TTL_MINUTES},
    ).first()

    if not row:
        raise HTTPException(status_code=400, detail="尚無有效選單，請重新輸入「?」")

    skey, scope, payload, created_at = row
    if isinstance(payload, str):
        payload = json.loads(payload)

    # 用後即刪舊選單
    _consume_session(db, lid, skey)

    # 依 scope 分流
    if scope == "category_menu":
        menu   = payload["menu"]
        bytype = payload["by_type"]
        if not (1 <= idx <= len(menu)):
            raise HTTPException(status_code=400, detail="選項超出範圍")

        chosen = menu[idx - 1]  # {"key": "...", "label": "...", "count": ...}
        key = chosen["key"]
        bucket = bytype[key]
        items = bucket["items"]
        label = bucket["label"]

        # 建立新的「案件列表」session
        new_key = _save_session(db, lid, f"case_list:{key}", {"label": label, "items": items})
        msg = _render_case_brief_list(items, label, new_key)
        return {"ok": True, "total": len(items), "message": msg}

    elif scope.startswith("case_list:"):
        items = payload["items"]
        if not (1 <= idx <= len(items)):
            raise HTTPException(status_code=400, detail="選項超出範圍")

        case_id = items[idx - 1]["id"]
        case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="案件不存在或已移除")

        return {"ok": True, "message": render_case_detail(case)}

    else:
        raise HTTPException(status_code=400, detail="選單已失效，請重新輸入「?」")

# ============================ 健康檢查 ============================
@user_router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_routes", "timestamp": datetime.utcnow().isoformat()}

# 供 main.py 引用
router = user_router
