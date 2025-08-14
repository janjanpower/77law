# api/routes/user_routes.py
# -*- coding: utf-8 -*-
"""
LINE 一般用戶/律師查案路由（單租戶版，n8n 無需新增節點）
- 「?」→ /my-cases
- 其餘（登錄/是/否/數字選單）→ 全部走 /register
  • 數字：自動辨識並處理最近一筆有效選單（類別選單 or 案件列表）
  • 登錄/是/否：維持原有流程
- 會話選單：user_query_sessions（TTL 預設 30 分鐘），過期自清、同 scope 只留最新、用後即刪
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
SESSION_TTL_MINUTES = int(os.getenv("UQS_TTL_MINUTES", "30"))

# ============================ Pydantic ============================
class LookupIn(BaseModel):
    line_user_id: Optional[str] = None
    user_name:   Optional[str] = None
    destination: Optional[str] = None
    text:        Optional[str] = None

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

class MyCasesIn(BaseModel):
    line_user_id: str
    include_as_opponent: Optional[bool] = False  # 是否把對造人也算進來（預設關閉）

# ============================ Helpers ============================
def _normalize_text(s: str) -> str:
    """全形數字→半形、全形問號→半形、trim"""
    s = (s or "")
    # 全形問號
    s = s.replace("？", "?")
    # 全形數字
    s = re.sub(r"[０-９]", lambda m: chr(ord(m.group(0)) - 0xFEE0), s)
    return s.strip()

def _parse_intent(text_msg: str):
    """登錄/確認/? 三類意圖，其餘交給數字或預設"""
    msg = _normalize_text(text_msg)
    if not msg:
        return "none", None
    m = re.match(r"^(?:登錄|登陸|登入|登录)\s*(.+)$", msg, flags=re.I)
    if m:
        return "prepare", m.group(1).strip()
    if msg in ("是","yes","Yes","YES"): return "confirm_yes", None
    if msg in ("否","no","No","NO"):   return "confirm_no", None
    if msg == "?":                      return "show_cases", None
    return "none", None  # 可能是數字或其他

def _fmt_dt(v):
    if not v:
        return "-"
    if isinstance(v, str):
        return v[:19].replace("T", " ")
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)

def _build_progress_view(progress_stages):
    """
    解析進度資料並回傳：
    - lines: ["1. 2025-08-05 調解 13:00", "2. 2025-08-07 確定 15:00", ...]
    - notes: ["帶刀子", ...]   # 彙整各階段 note/remark/memo
    - count: 已完成階段數

    支援格式：
    A) dict: {"偵查中": "2025-08-10", "準備程序": {"date":"2025-09-01", "time":"15:00", "note":"已送卷"}}
    B) list: [{"stage":"偵查中","date":"2025-08-10","time":"13:00","note":"..."}, ...]
    C) str  : 原樣回傳為單一行
    """
    if not progress_stages:
        return {"lines": ["尚無進度階段記錄"], "notes": [], "count": 0}

    try:
        data = progress_stages
        if isinstance(progress_stages, str):
            try:
                data = json.loads(progress_stages)
            except Exception:
                # 純文字就直接當作唯一一行
                return {"lines": [str(progress_stages)], "notes": [], "count": 1}

        lines, notes = [], []

        def push(stage, date=None, time=None, note=None):
            stage = (stage or "-").strip()
            date  = (date  or "-").strip()
            time  = (time  or "").strip()
            tpart = f" {time}" if time else ""
            lines.append(f"{len(lines)+1}. {date} {stage}{tpart}")
            if note:
                n = str(note).strip()
                if n:
                    notes.append(n)

        if isinstance(data, dict):
            # 依照 dict 插入順序輸出
            for stage, v in data.items():
                if isinstance(v, dict):
                    push(stage,
                         v.get("date") or v.get("at") or v.get("updated_at") or v.get("time") or "-",
                         v.get("time"),
                         v.get("note") or v.get("remark") or v.get("memo"))
                else:
                    # v 是日期字串；若含時間（例如 "2025-08-05 13:00"），自動切開
                    vv = str(v)
                    d, t = (vv.split(" ", 1) + [""])[:2] if " " in vv else (vv, "")
                    push(stage, d, t, None)

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    stage = item.get("stage") or item.get("name") or item.get("label")
                    date  = item.get("date")  or item.get("at")   or item.get("updated_at")
                    time  = item.get("time")
                    note  = item.get("note")  or item.get("remark") or item.get("memo")
                    push(stage, date, time, note)
                else:
                    # 非 dict 元素，直接當作一行
                    lines.append(f"{len(lines)+1}. {item}")

        else:
            return {"lines": [str(data)], "notes": [], "count": 1}

        if not lines:
            lines = ["尚無進度階段記錄"]

        return {"lines": lines, "notes": notes, "count": len(lines)}

    except Exception:
        return {"lines": [str(progress_stages)], "notes": [], "count": 1}

def render_case_detail(case) -> str:
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
    # 進度清單 + 備註 + 統計
    pv = _build_progress_view(getattr(case, "progress_stages", None))
    lines.append("📈 案件進度歷程：")
    lines.extend(pv["lines"])

    # ↙️ 就是你要的這種顯示：在清單下方獨立一行「備註」
    if pv["notes"]:
        lines.append(f"🌿 備註：{'；'.join(pv['notes'])}")

    lines.append(f"📊 進度統計：共完成 {pv['count']} 個階段")

    # （如果你還想保留「最新進度」就留著這行）
    lines.append(f"⚠️ 最新進度：{progress}")
    lines.append("────────────────────")
    lines.append("📁 案件資料夾：")
    # lines.append("🔢 輸入編號瀏覽（1–2）檔案")
    # lines.append("")
    # lines.append("  1. 案件資訊（2 個檔案）")
    # lines.append("  2. 進度總覽（1 個檔案）")
    lines.append("（稍後開放）")
    lines.append("────────────────────")
    lines.append(f"🟥建立時間：{created_at}")
    lines.append(f"🟩更新時間：{updated_at}")
    return "\n".join(lines)

# —— 類別歸一：回 (key, label)
def _type_key_label(case_type: Optional[str]) -> Tuple[str, str]:
    t = (case_type or "").strip()
    if "刑" in t:
        return "CRIM", "刑事"
    if "民" in t:
        return "CIVIL", "民事"
    return "OTHER", "其他"

def _render_category_menu(menu_items: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append("🗂 案件類別選單")
    lines.append("────────────────────")
    for i, m in enumerate(menu_items, 1):
        lines.append(f"{i}. {m['label']}案件列表（{m['count']} 件）")
    lines.append("")
    lines.append(f"💡 請輸入選項號碼 (1-{len(menu_items)})")
    return "\n".join(lines)

def _render_case_brief_list(items: List[Dict[str, Any]], label: str) -> str:
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

# ============================ 會話暫存（user_query_sessions） ============================
def _cleanup_expired_sessions(db: Session, line_user_id: Optional[str] = None):
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

def _save_session(db: Session, line_user_id: str, scope: str, payload: Dict[str, Any]) -> None:
    # 逾時自清 + 同 scope 只留最新
    _cleanup_expired_sessions(db, line_user_id)
    db.execute(
        text("""DELETE FROM user_query_sessions WHERE line_user_id = :lid AND scope = :scope"""),
        {"lid": line_user_id, "scope": scope},
    )
    db.execute(
        text("""
        INSERT INTO user_query_sessions (line_user_id, session_key, scope, payload_json)
        VALUES (:lid, :skey, :scope, :payload)
        """),
        {"lid": line_user_id, "skey": str(uuid4()), "scope": scope, "payload": json.dumps(payload, ensure_ascii=False)},
    )
    db.commit()

def _load_last_session(db: Session, line_user_id: str) -> Optional[Dict[str, Any]]:
    # 取用戶最近一筆未過期的選單
    row = db.execute(
        text(f"""
            SELECT session_key, scope, payload_json, created_at
            FROM user_query_sessions
            WHERE line_user_id = :lid
              AND created_at >= NOW() - (CAST(:ttl AS TEXT) || ' minutes')::interval
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"lid": line_user_id, "ttl": SESSION_TTL_MINUTES},
    ).first()
    if not row:
        return None
    _, scope, payload, created_at = row
    if isinstance(payload, str):
        payload = json.loads(payload)
    return {"scope": scope, "payload": payload, "created_at": created_at}

def _consume_all_sessions(db: Session, line_user_id: str):
    db.execute(
        text("""DELETE FROM user_query_sessions WHERE line_user_id = :lid"""),
        {"lid": line_user_id},
    )
    db.commit()

# ============================ 2) 註冊（含數字選單處理） ============================
@user_router.post("/register", response_model=RegisterOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)):
    """
    這支同時處理：
    - 「登錄 XXX」→ pending
    - 「是 / 否」→ registered 或重輸
    - 「數字」→ 依最近有效選單（類別選單 or 案件列表）做選擇
    你在 n8n 不用加新節點；所有非「?」輸入都打這支即可。
    """
    try:
        lid     = (payload.line_user_id or "").strip()
        text_in = _normalize_text(payload.text or "")

        # ---------- 0) 判斷是否為純數字（選單選擇） ----------
        if re.fullmatch(r"[1-9]\d*", text_in):
            choice = int(text_in)
            sess = _load_last_session(db, lid)
            if not sess:
                return RegisterOut(success=False, message="尚無有效選單，請先輸入「?」。")

            scope = sess["scope"]
            payload_json = sess["payload"]
            # 用後即刪（全部清掉，避免混亂）
            _consume_all_sessions(db, lid)

            # A. 類別選單 → 回該類別案件列表，並建立新的列表選單（但不再要求 n8n 帶 key）
            if scope == "category_menu":
                menu   = payload_json["menu"]
                bytype = payload_json["by_type"]
                if not (1 <= choice <= len(menu)):
                    return RegisterOut(success=False, message="選項超出範圍，請重新輸入「?」。")

                chosen = menu[choice - 1]  # {"key": "...", "label": "...", "count": ...}
                key = chosen["key"]
                bucket = bytype[key]
                items = bucket["items"]
                label = bucket["label"]

                # 產生新列表選單（不存 key，因為我們改成「永遠讀最近一筆」）
                _save_session(db, lid, f"case_list:{key}", {"label": label, "items": items})
                msg = _render_case_brief_list(items, label)
                return RegisterOut(success=True, message=msg)

            # B. 案件列表 → 回單筆詳細
            elif scope.startswith("case_list:"):
                items = payload_json["items"]
                if not (1 <= choice <= len(items)):
                    return RegisterOut(success=False, message="選項超出範圍，請重新輸入「?」。")

                case_id = items[choice - 1]["id"]
                case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
                if not case:
                    return RegisterOut(success=False, message="案件不存在或已移除，請輸入「?」重新載入。")

                return RegisterOut(success=True, message=render_case_detail(case))

            else:
                return RegisterOut(success=False, message="選單已失效，請重新輸入「?」。")

        # ---------- 1) 解析文字意圖（登錄/確認/問號） ----------
        intent, cname = _parse_intent(text_in)

        # （可選）如果有人把「?」也丟進來，直接提示去用 /my-cases
        if intent == "show_cases":
            return RegisterOut(success=True, message="請輸入「?」以查詢案件。")

        # 1a) 「登錄 XXX」→ 寫/更新 pending（不立刻成為正式）
        if intent == "prepare" and cname:
            candidate = re.sub(r"^(?:登錄|登陸|登入|登录)\s+", "", cname).strip()
            db.execute(text("""
                INSERT INTO pending_line_users (line_user_id, expected_name, status, created_at, updated_at)
                VALUES (:lid, :name, 'pending', NOW(), NOW())
                ON CONFLICT (line_user_id)
                DO UPDATE
                SET expected_name = :name,
                    status        = 'pending',
                    updated_at    = NOW();
            """), {"lid": lid, "name": candidate})
            db.commit()
            # 新輸入登錄時，清掉舊選單
            _consume_all_sessions(db, lid)
            return RegisterOut(
                success=True,
                expected_name=candidate,
                message=f"請確認您的大名：{candidate}\n回覆「是」確認，回覆「否」重新輸入。"
            )

        # 1b) 「是」→ 將 pending → registered
        if intent == "confirm_yes":
            row = db.execute(text("""
                SELECT expected_name
                FROM pending_line_users
                WHERE line_user_id = :lid
                ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
                LIMIT 1
            """), {"lid": lid}).first()
            if not row or not row[0]:
                return RegisterOut(success=False, message="尚未收到您的大名，請輸入「登錄 您的大名」。")

            final_name = row[0]
            db.execute(text("""
                UPDATE pending_line_users
                SET status = 'registered',
                    updated_at = NOW()
                WHERE line_user_id = :lid
            """), {"lid": lid})
            db.commit()
            # 完成登錄後，清掉舊選單
            _consume_all_sessions(db, lid)
            return RegisterOut(
                success=True,
                expected_name=final_name,
                message=f"歡迎 {final_name}！已完成登錄。\n輸入「?」即可查詢您的案件進度。"
            )

        # 1c) 「否」→ 清候選姓名，維持 pending
        if intent == "confirm_no":
            db.execute(text("""
                UPDATE pending_line_users
                SET expected_name = NULL,
                    status        = 'pending',
                    updated_at    = NOW()
                WHERE line_user_id = :lid
            """), {"lid": lid})
            db.commit()
            _consume_all_sessions(db, lid)
            return RegisterOut(success=True, message="好的，請重新輸入「登錄 您的大名」。")

        # 1d) 其他文字 → 若已 registered 給提示；否則引導登錄
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

    # 取使用者已確認的姓名
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

    # 查案件
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

    # 多件 → 依類別歸群並產生「類別選單」
    buckets: Dict[str, Dict[str, Any]] = {}
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
    menu_items = [{"key": k, "label": buckets[k]["label"], "count": len(buckets[k]["items"])}
                  for k in types_present]

    # 存一筆「類別選單」session，後續數字輸入會由 /register 讀取最近一筆
    _save_session(
        db, lid, "category_menu",
        {"menu": menu_items, "by_type": buckets}
    )
    msg = _render_category_menu(menu_items)
    return {"ok": True, "total": len(rows), "message": msg}

# ============================ 健康檢查 ============================
@user_router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_routes", "timestamp": datetime.utcnow().isoformat()}

# 供 main.py 引用
router = user_router
