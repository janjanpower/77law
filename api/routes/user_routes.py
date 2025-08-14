# api/routes/user_routes.py
# -*- coding: utf-8 -*-
"""
單租戶 LINE 用戶查案（n8n 零改動）
- 「?」 → /my-cases
- 其他（登錄 XXX / 是 / 否 / 數字選單）→ /register
- 多筆先出「案件類別選單」，單筆直接詳情
- 進度呈現：每一階段一行（含日期/時間），若有備註就緊接一行「💬 備註：…」
- 已特別支援時間欄位：progress_times（可為字串或 list）
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from typing import Optional, List, Dict, Any, Tuple, Literal
from datetime import datetime
from uuid import uuid4
import logging, traceback, re, json, os

from api.database import get_db
from api.models_cases import CaseRecord

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

user_router = APIRouter(prefix="/api/user", tags=["user"])

# ============================ 可調參數 ============================
SESSION_TTL_MINUTES = int(os.getenv("UQS_TTL_MINUTES", "30"))

# ============================ Pydantic Models ============================
class RegisterIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    user_name:   Optional[str] = None
    client_id:   Optional[str] = None
    text:        Optional[str] = None
    destination: Optional[str] = None

class RegisterOut(BaseModel):
    success: bool
    message: str
    expected_name: Optional[str] = None
    route: Literal[
        'REGISTER_PREPARE',
        'REGISTER_DONE',
        'REGISTER_RETRY',
        'MENU_CATEGORY',
        'MENU_LIST',
        'CASE_DETAIL',
        'INFO',
        'ERROR'
    ] = 'INFO'

class MyCasesIn(BaseModel):
    line_user_id: str
    include_as_opponent: Optional[bool] = False

# ============================ Helpers：一般 ============================
def _normalize_text(s: str) -> str:
    s = (s or "")
    s = s.replace("？", "?")
    s = re.sub(r"[０-９]", lambda m: chr(ord(m.group(0)) - 0xFEE0), s)
    return s.strip()

def _parse_intent(text_msg: str):
    msg = _normalize_text(text_msg)
    if not msg:
        return "none", None
    m = re.match(r"^(?:登錄|登陸|登入|登录)\s*(.+)$", msg, flags=re.I)
    if m:
        return "prepare", m.group(1).strip()
    if msg in ("是","yes","Yes","YES"): return "confirm_yes", None
    if msg in ("否","no","No","NO"):   return "confirm_no", None
    if msg == "?":                      return "show_cases", None
    return "none", None

def _fmt_dt(v):
    if not v:
        return "-"
    if isinstance(v, str):
        return v[:19].replace("T", " ")
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)

# ============================ Helpers：進度時間線（時間 + 備註） ============================
def _to_halfwidth(s: str) -> str:
    if not s: return s
    out = []
    for ch in str(s):
        code = ord(ch)
        if 0xFF10 <= code <= 0xFF19:
            out.append(chr(code - 0xFEE0))
        elif ch in "：．，／－":
            out.append({"：":":", "．":".", "，":",", "／":"/", "－":"-"}[ch])
        else:
            out.append(ch)
    return "".join(out)

def _normalize_hhmm(h: int, m: int, ampm: Optional[str]) -> str:
    ampm = (ampm or "").strip().lower()
    if ampm in ("pm", "p.m.", "下午"):
        if h % 12 != 0: h = (h % 12) + 12
        else: h = 12
    elif ampm in ("am", "a.m.", "上午"):
        if h == 12: h = 0
    return f"{max(0,min(23,h)):02d}:{max(0,min(59,m)):02d}"

def _extract_time_from_text(text: str) -> Optional[str]:
    s = _to_halfwidth(text or "")
    m = re.search(r"(上午|下午|AM|PM|am|pm)?\s*([0-2]?\d)[:：\.]([0-5]\d)", s, re.I)
    if m:
        return _normalize_hhmm(int(m.group(2)), int(m.group(3)), m.group(1))
    m = re.search(r"(上午|下午|AM|PM|am|pm)?\s*([0-2]?\d)\s*[點时時点]\s*([0-5]?\d)\s*(?:分)?", s, re.I)
    if m:
        return _normalize_hhmm(int(m.group(2)), int(m.group(3)), m.group(1))
    m = re.search(r"(?<!\d)([0-2]?\d)([0-5]\d)(?!\d)", s)
    if m:
        return _normalize_hhmm(int(m.group(1)), int(m.group(2)), None)
    return None

def _extract_time_from_any(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, (list, tuple)):
        for x in val:
            t = _extract_time_from_any(x)
            if t: return t
        return None
    if isinstance(val, dict):
        for v in val.values():
            t = _extract_time_from_any(v)
            if t: return t
        return None
    return _extract_time_from_text(str(val))

_COMMON_TIME_KEYS = {
    "time","schedule_time","court_time","hearing_time","session_time",
    "time_str","clock","progress_time","progress_times","開庭時間","時間","時刻","約定時間"
}

def _find_time_in_payload(obj) -> Optional[str]:
    if obj is None:
        return None
    if isinstance(obj, str):
        return _extract_time_from_text(obj)
    if isinstance(obj, dict):
        for k in _COMMON_TIME_KEYS:
            if k in obj and obj[k] not in (None, ""):
                t = _extract_time_from_any(obj[k])
                if t: return t
        for v in obj.values():
            t = _find_time_in_payload(v)
            if t: return t
        return None
    if isinstance(obj, (list, tuple)):
        for v in obj:
            t = _extract_time_from_any(v)
            if t: return t
        return None
    return None

def _as_list_of_str(val):
    if val is None:
        return []
    if isinstance(val, str):
        return [s.strip() for s in re.split(r"\r?\n", val) if s.strip()]
    if isinstance(val, (list, tuple)):
        out = []
        for x in val:
            out += _as_list_of_str(x)
        return [s for s in out if s]
    if isinstance(val, dict):
        return _as_list_of_str(list(val.values()))
    return [str(val).strip()] if str(val).strip() else []

def _pick(d: dict, *keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def _split_date_time_str(s: str):
    if not s:
        return None, None
    s = str(s).strip()
    if "T" in s:
        left, right = s.split("T", 1)
        return left.strip(), right.strip()
    if " " in s:
        left, right = s.split(" ", 1)
        return left.strip(), right.strip()
    return s, None

def _iter_stage_items(progress_stages, progress_times=None) -> List[Dict[str, Any]]:
    """
    展平成 list[{stage,date,time,notes_from_stage}]。
    支援 dict/list/JSON 字串；同時可用 progress_times 映射補上各階段的時間。
    """
    # 先處理 progress_times 可能的型別（dict / JSON 字串 / None）
    time_map = {}
    if isinstance(progress_times, str):
        try:
            time_map = json.loads(progress_times) or {}
        except Exception:
            time_map = {}
    elif isinstance(progress_times, dict):
        time_map = progress_times or {}

    def _get_time_from_map(stage_name: str) -> Optional[str]:
        if not time_map:
            return None
        # 直取
        val = time_map.get(stage_name)
        if val:
            return _extract_time_from_any(val)
        # 寬鬆比對（去空白、全半形與大小寫）
        norm = (stage_name or "").strip().lower()
        for k, v in time_map.items():
            if (k or "").strip().lower() == norm:
                return _extract_time_from_any(v)
        return None

    data = progress_stages
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return []

    if isinstance(data, dict) and any(k in data for k in ("stages", "items", "data")):
        for k in ("stages", "items", "data"):
            if k in data:
                data = data[k]
                break

    items: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        for stage, payload in data.items():
            if isinstance(payload, dict):
                raw_date = _pick(payload, "date", "at", "updated_at", "datetime", "schedule_date")
                raw_time = _pick(payload, "time", "schedule_time", "court_time", "hearing_time",
                                 "session_time", "time_str", "clock", "progress_time", "開庭時間", "時間")
                d, t = (None, None)
                if raw_date:
                    d, t = _split_date_time_str(raw_date)
                if not t:
                    # 先從 payload 內挖，再從 progress_times 補
                    t = _extract_time_from_any(raw_time) or _find_time_in_payload(payload) or _get_time_from_map(stage)
                notes = _as_list_of_str(
                    _pick(payload, "note", "notes", "progress_notes", "remark", "memo", "comment", "comments", "description", "desc")
                )
                items.append({"stage": stage, "date": d, "time": t, "notes_from_stage": notes})
            else:
                d, t = _split_date_time_str(str(payload))
                if not t:
                    t = _get_time_from_map(stage)
                items.append({"stage": stage, "date": d, "time": t, "notes_from_stage": []})
        return items

    if isinstance(data, list):
        for it in data:
            if not isinstance(it, dict):
                continue
            stage = _pick(it, "stage", "name", "label", "phase", "title") or "-"
            raw_date = _pick(it, "date", "at", "updated_at", "datetime", "schedule_date")
            raw_time = _pick(it, "time", "schedule_time", "court_time", "hearing_time",
                             "session_time", "time_str", "clock", "progress_time", "開庭時間", "時間")
            d, t = (None, None)
            if raw_date:
                d, t = _split_date_time_str(raw_date)
            if not t:
                t = _extract_time_from_any(raw_time) or _find_time_in_payload(it) or _get_time_from_map(stage)
            notes = _as_list_of_str(
                _pick(it, "note", "notes", "progress_notes", "remark", "memo", "comment", "comments", "description", "desc")
            )
            items.append({"stage": stage, "date": d, "time": t, "notes_from_stage": notes})
        return items

    return items


def _build_progress_timeline_with_notes(progress_stages, case_level_notes=None, progress_times=None) -> List[str]:
    """
    回傳列印用文字行：
      1. 2025-08-14  一審  13:00
      💬 備註：帶文件
    """
    items = _iter_stage_items(progress_stages, progress_times=progress_times)
    _merge_case_level_notes(items, case_level_notes)

    lines: List[str] = []
    for i, it in enumerate(items, 1):
        date_str = (it.get("date") or "-").strip()
        time_str = (it.get("time") or "").strip()
        stage    = (it.get("stage") or "-").strip()

        title = f"{i}. {date_str}  {stage}"
        if time_str:
            title += f"  {time_str}"
        lines.append(title)

        for s in it.get("notes") or []:
            s = str(s).strip()
            if s:
                lines.append(f"💬 備註：{s}")

    return lines


# ============================ Helpers：類別/選單 ============================
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

# ============================ Helpers：會話暫存 ============================
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
    db.execute(text("""DELETE FROM user_query_sessions WHERE line_user_id = :lid"""),
               {"lid": line_user_id})
    db.commit()

# ============================ 視圖：單筆詳情 ============================
def render_case_detail(case) -> str:
    case_number   = case.case_number or case.case_id or "-"
    client        = case.client or "-"
    case_type     = case.case_type or "-"
    case_reason   = case.case_reason or "-"
    court         = case.court or "-"
    division      = case.division or "-"
    legal_affairs = getattr(case, "legal_affairs", None) or "-"
    opposing      = case.opposing_party or "-"
    created_at    = _fmt_dt(getattr(case, "created_date", None))
    updated_at    = _fmt_dt(getattr(case, "updated_date", None) or getattr(case, "updated_at", None))

    lines: List[str] = []
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
    timeline = _build_progress_timeline_with_notes(
        getattr(case, "progress_stages", None),
        getattr(case, "progress_notes", None),
        getattr(case, "progress_times", None),    # <--- 新增這行
    )
    if timeline:
        lines.extend(timeline)
    else:
        lines.append("（目前沒有進度記錄）")

    lines.append("────────────────────")
    lines.append(f"🟥建立時間：{created_at}")
    lines.append(f"🟩更新時間：{updated_at}")
    return "\n".join(lines)
# --- END PATCH ---

# ============================ 1) /register ============================
@user_router.post("/register", response_model=RegisterOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        lid     = (payload.line_user_id or "").strip()
        text_in = _normalize_text(payload.text or "")

        # 數字選單
        if re.fullmatch(r"[1-9]\d*", text_in):
            choice = int(text_in)
            sess = _load_last_session(db, lid)
            if not sess:
                return RegisterOut(success=False, message="尚無有效選單，請先輸入「?」。", route='INFO')

            scope = sess["scope"]
            payload_json = sess["payload"]
            _consume_all_sessions(db, lid)

            if scope == "category_menu":
                menu   = payload_json["menu"]
                bytype = payload_json["by_type"]
                if not (1 <= choice <= len(menu)):
                    return RegisterOut(success=False, message="選項超出範圍，請重新輸入「?」。", route='INFO')

                chosen = menu[choice - 1]
                key = chosen["key"]
                bucket = bytype[key]
                items = bucket["items"]
                label = bucket["label"]

                _save_session(db, lid, f"case_list:{key}", {"label": label, "items": items})
                msg = _render_case_brief_list(items, label)
                return RegisterOut(success=True, message=msg, route='MENU_LIST')

            elif scope.startswith("case_list:"):
                items = payload_json["items"]
                if not (1 <= choice <= len(items)):
                    return RegisterOut(success=False, message="選項超出範圍，請輸入「?」重新載入。", route='INFO')

                case_id = items[choice - 1]["id"]
                case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
                if not case:
                    return RegisterOut(success=False, message="案件不存在或已移除，請輸入「?」重新載入。", route='INFO')

                return RegisterOut(success=True, message=render_case_detail(case), route='CASE_DETAIL')

            else:
                return RegisterOut(success=False, message="選單已失效，請重新輸入「?」。", route='INFO')

        # 意圖判斷
        intent, cname = _parse_intent(text_in)

        if intent == "show_cases":
            return RegisterOut(success=True, message="請輸入「?」以查詢案件。", route='INFO')

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
            _consume_all_sessions(db, lid)
            return RegisterOut(
                success=True,
                expected_name=candidate,
                message=f"請確認您的大名：{candidate}\n回覆「是」確認，回覆「否」重新輸入。",
                route='REGISTER_PREPARE'
            )

        if intent == "confirm_yes":
            row = db.execute(text("""
                SELECT expected_name
                FROM pending_line_users
                WHERE line_user_id = :lid
                ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
                LIMIT 1
            """), {"lid": lid}).first()
            if not row or not row[0]:
                return RegisterOut(success=False, message="尚未收到您的大名，請輸入「登錄 您的大名」。", route='INFO')

            final_name = row[0]
            db.execute(text("""
                UPDATE pending_line_users
                SET status = 'registered',
                    updated_at = NOW()
                WHERE line_user_id = :lid
            """), {"lid": lid})
            db.commit()
            _consume_all_sessions(db, lid)
            return RegisterOut(
                success=True,
                expected_name=final_name,
                message=f"歡迎 {final_name}！已完成登錄。\n輸入「?」即可查詢您的案件進度。",
                route='REGISTER_DONE'
            )

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
            return RegisterOut(success=True, message="好的，請重新輸入「登錄 您的大名」。", route='REGISTER_RETRY')

        # 其他輸入：登錄提示
        row = db.execute(text("""
            SELECT status FROM pending_line_users
            WHERE line_user_id = :lid
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            LIMIT 1
        """), {"lid": lid}).first()
        if row and row[0] == "registered":
            return RegisterOut(success=True, message="已登錄，用「?」可查詢您的案件。", route='INFO')
        else:
            return RegisterOut(success=False, message="您好，請輸入「登錄 您的大名」完成登錄。", route='INFO')

    except Exception as e:
        db.rollback()
        logger.error(f"/register 失敗: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="REG_500: 系統錯誤")

# ============================ 2) /my-cases ============================
@user_router.post("/my-cases")
def my_cases(payload: MyCasesIn, db: Session = Depends(get_db)):
    lid = (payload.line_user_id or "").strip()
    if not lid:
        raise HTTPException(status_code=400, detail="line_user_id 必填")

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
        return {"ok": False, "message": "尚未登錄，請輸入「登錄 您的大名」完成登錄。", "route": "INFO"}

    user_name = row[0].strip()
    if not user_name:
        return {"ok": False, "message": "目前查無姓名資訊，請輸入「登錄 您的大名」。", "route": "INFO"}

    if payload.include_as_opponent:
        q = db.query(CaseRecord).filter(or_(CaseRecord.client == user_name, CaseRecord.opposing_party == user_name))
    else:
        q = db.query(CaseRecord).filter(CaseRecord.client == user_name)

    q = q.order_by(text("updated_date DESC NULLS LAST, updated_at DESC NULLS LAST, id DESC"))
    rows: List[CaseRecord] = q.all()

    if not rows:
        return {"ok": True, "total": 0, "message": f"沒有找到「{user_name}」的案件。", "route": "INFO"}

    if len(rows) == 1:
        return {"ok": True, "total": 1, "message": render_case_detail(rows[0]), "route": "CASE_DETAIL"}

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

    if len(types_present) >= 2:
        menu_items = [{"key": k, "label": buckets[k]["label"], "count": len(buckets[k]["items"])}
                      for k in types_present]
        _save_session(db, lid, "category_menu", {"menu": menu_items, "by_type": buckets})
        msg = _render_category_menu(menu_items)
        return {"ok": True, "total": len(rows), "message": msg, "route": "MENU_CATEGORY"}

    only_key = types_present[0]
    items = buckets[only_key]["items"]
    label = buckets[only_key]["label"]
    _save_session(db, lid, f"case_list:{only_key}", {"label": label, "items": items})
    msg = _render_case_brief_list(items, label)
    return {"ok": True, "total": len(rows), "message": msg, "route": "MENU_LIST"}

# ============================ 健康檢查 ============================
@user_router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_routes", "timestamp": datetime.utcnow().isoformat()}

router = user_router
