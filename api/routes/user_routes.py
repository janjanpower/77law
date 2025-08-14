# api/routes/user_routes.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from typing import Optional, List, Dict, Any, Tuple, Literal
from datetime import datetime
import json, re, os

from api.database import get_db
from api.models_cases import CaseRecord  # 你現有的案件 ORM

user_router = APIRouter(prefix="/api/user", tags=["user"])

# ========= I/O Models =========
class RegisterIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    text: Optional[str] = None
    user_name: Optional[str] = None
    client_id: Optional[str] = None
    destination: Optional[str] = None

class RegisterOut(BaseModel):
    success: bool
    message: str
    expected_name: Optional[str] = None
    route: Literal["REGISTER_PREPARE","REGISTER_DONE","REGISTER_RETRY","INFO","ERROR"] = "INFO"

class MyCaseIn(BaseModel):
    line_user_id: str = Field(..., min_length=5)
    text: Optional[str] = None
    include_as_opponent: Optional[bool] = False

class MyCaseOut(BaseModel):
    success: bool
    message: str
    route: Literal["MENU_CATEGORY","MENU_LIST","CASE_DETAIL","INFO","ERROR"] = "INFO"

# ========= 小工具 =========
SESSION_TTL_MINUTES = int(os.getenv("UQS_TTL_MINUTES", "30"))

def _normalize_text(s: Optional[str]) -> str:
    s = (s or "").strip()
    s = s.replace("？", "?")
    # 轉半形數字
    s = re.sub(r"[０-９]", lambda m: chr(ord(m.group(0)) - 0xFEE0), s)
    return s

def _fmt_dt(v):
    if not v: return "-"
    if isinstance(v, str): return v[:19].replace("T"," ")
    if isinstance(v, datetime): return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)

def _ensure_session_table(db: Session):
    db.execute(text("""
    CREATE TABLE IF NOT EXISTS user_query_sessions(
      id BIGSERIAL PRIMARY KEY,
      line_user_id TEXT NOT NULL,
      scope TEXT NOT NULL,
      payload_json JSONB,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """))
    db.commit()

def _save_session(db: Session, lid: str, scope: str, payload: Dict[str, Any]):
    _ensure_session_table(db)
    db.execute(text("DELETE FROM user_query_sessions WHERE line_user_id=:lid"),
               {"lid": lid})
    db.execute(text("""
        INSERT INTO user_query_sessions(line_user_id,scope,payload_json)
        VALUES(:lid,:scope,CAST(:payload AS JSONB))
    """), {"lid": lid, "scope": scope, "payload": json.dumps(payload, ensure_ascii=False)})
    db.commit()

def _load_session(db: Session, lid: str) -> Optional[Dict[str, Any]]:
    _ensure_session_table(db)
    r = db.execute(text(f"""
      SELECT scope, payload_json
      FROM user_query_sessions
      WHERE line_user_id=:lid
        AND created_at >= NOW() - (CAST(:ttl AS TEXT)||' minutes')::interval
      ORDER BY id DESC LIMIT 1
    """), {"lid": lid, "ttl": SESSION_TTL_MINUTES}).first()
    if not r: return None
    scope, payload = r
    if isinstance(payload, str):
        payload = json.loads(payload)
    return {"scope": scope, "payload": payload}

def _clear_session(db: Session, lid: str):
    db.execute(text("DELETE FROM user_query_sessions WHERE line_user_id=:lid"), {"lid": lid})
    db.commit()

# ========= 進度時間（含 progress_times） =========
_COMMON_TIME_KEYS = {
    "time","schedule_time","court_time","hearing_time","session_time",
    "time_str","clock","progress_time","progress_times","開庭時間","時間","時刻"
}

def _normalize_hhmm(h: int, m: int, ampm: Optional[str]) -> str:
    ampm = (ampm or "").strip().lower()
    if ampm in ("pm","p.m.","下午"):
        if h % 12 != 0: h = (h % 12) + 12
        else: h = 12
    elif ampm in ("am","a.m.","上午"):
        if h == 12: h = 0
    h = max(0, min(23, int(h))); m = max(0, min(59, int(m)))
    return f"{h:02d}:{m:02d}"

def _extract_time_from_text(s: str) -> Optional[str]:
    if not s: return None
    s = s.replace("：",":").replace("．",".")
    m = re.search(r"(上午|下午|AM|PM|am|pm)?\s*([0-2]?\d)[:\.]([0-5]\d)", s)
    if m: return _normalize_hhmm(m.group(2), m.group(3), m.group(1))
    m = re.search(r"(上午|下午|AM|PM|am|pm)?\s*([0-2]?\d)\s*[點时時点]\s*([0-5]?\d)\s*(?:分)?", s)
    if m: return _normalize_hhmm(m.group(2), m.group(3), m.group(1))
    m = re.search(r"(?<!\d)([0-2]?\d)([0-5]\d)(?!\d)", s)
    if m: return _normalize_hhmm(m.group(1), m.group(2), None)
    return None

def _extract_time_from_any(v) -> Optional[str]:
    if v is None: return None
    if isinstance(v, (list,tuple)):
        for x in v:
            t = _extract_time_from_any(x)
            if t: return t
        return None
    if isinstance(v, dict):
        for x in v.values():
            t = _extract_time_from_any(x)
            if t: return t
        return None
    return _extract_time_from_text(str(v))

def _find_time_in_payload(obj) -> Optional[str]:
    if obj is None: return None
    if isinstance(obj, dict):
        for k in _COMMON_TIME_KEYS:
            if k in obj and obj[k]:
                t = _extract_time_from_any(obj[k])
                if t: return t
        for v in obj.values():
            t = _find_time_in_payload(v)
            if t: return t
        return None
    if isinstance(obj, (list,tuple)):
        for v in obj:
            t = _extract_time_from_any(v)
            if t: return t
        return None
    if isinstance(obj, str):
        return _extract_time_from_text(obj)
    return None

def _split_date_time_str(s: str):
    if not s: return None, None
    s = str(s).strip()
    if "T" in s: left, right = s.split("T",1); return left.strip(), right.strip()
    if " " in s: left, right = s.split(" ",1); return left.strip(), right.strip()
    return s, None

def _as_list(val) -> List[str]:
    if val is None: return []
    if isinstance(val, str):
        return [x for x in re.split(r"\r?\n", val) if x.strip()]
    if isinstance(val, (list,tuple)):
        out = []
        for x in val: out += _as_list(x)
        return [s for s in out if s]
    if isinstance(val, dict):
        return _as_list(list(val.values()))
    s = str(val).strip()
    return [s] if s else []

def _pick(d: dict, *keys):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] not in (None, ""):
            return d[k]
    return None

def _iter_stage_items(progress_stages, progress_times=None) -> List[Dict[str, Any]]:
    # 轉 time map
    tmap = {}
    if isinstance(progress_times, str):
        try: tmap = json.loads(progress_times) or {}
        except Exception: tmap = {}
    elif isinstance(progress_times, dict):
        tmap = progress_times or {}

    def _time_from_map(stage: str) -> Optional[str]:
        if not tmap: return None
        if stage in tmap and tmap[stage]: return _extract_time_from_any(tmap[stage])
        norm = (stage or "").strip().lower()
        for k,v in tmap.items():
            if (k or "").strip().lower() == norm:
                return _extract_time_from_any(v)
        return None

    data = progress_stages
    if isinstance(data, str):
        try: data = json.loads(data)
        except Exception: return []

    if isinstance(data, dict) and any(k in data for k in ("stages","items","data")):
        for k in ("stages","items","data"):
            if k in data: data = data[k]; break

    out: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for stage, payload in data.items():
            if isinstance(payload, dict):
                raw_date = _pick(payload, "date","at","updated_at","datetime","schedule_date")
                raw_time = _pick(payload, "time","schedule_time","court_time","hearing_time","session_time",
                                 "time_str","clock","progress_time","開庭時間","時間")
                d,t = (None,None)
                if raw_date: d,t = _split_date_time_str(raw_date)
                if not t:
                    t = _extract_time_from_any(raw_time) or _find_time_in_payload(payload) or _time_from_map(stage)
                notes = _as_list(_pick(payload, "note","notes","progress_notes","remark","memo","comment","comments","description","desc"))
                out.append({"stage": stage, "date": d, "time": t, "notes_from_stage": notes})
            else:
                d,t = _split_date_time_str(str(payload))
                if not t: t = _time_from_map(stage)
                out.append({"stage": stage, "date": d, "time": t, "notes_from_stage": []})
        return out

    if isinstance(data, list):
        for it in data:
            if not isinstance(it, dict): continue
            stage = _pick(it, "stage","name","label","phase","title") or "-"
            raw_date = _pick(it, "date","at","updated_at","datetime","schedule_date")
            raw_time = _pick(it, "time","schedule_time","court_time","hearing_time","session_time",
                             "time_str","clock","progress_time","開庭時間","時間")
            d,t = (None,None)
            if raw_date: d,t = _split_date_time_str(raw_date)
            if not t:
                t = _extract_time_from_any(raw_time) or _find_time_in_payload(it) or _time_from_map(stage)
            notes = _as_list(_pick(it, "note","notes","progress_notes","remark","memo","comment","comments","description","desc"))
            out.append({"stage": stage, "date": d, "time": t, "notes_from_stage": notes})
        return out
    return out

def _merge_case_level_notes(items: List[Dict[str, Any]], case_level_notes):
    extra = _as_list(case_level_notes)
    if not extra: return
    if not items:
        items.append({"stage":"-","date":"-","time":None,"notes_from_stage":[]})
    items[0].setdefault("notes", [])
    items[0]["notes"] += extra

def _build_timeline(progress_stages, case_level_notes=None, progress_times=None) -> List[str]:
    items = _iter_stage_items(progress_stages, progress_times)
    _merge_case_level_notes(items, case_level_notes)
    lines: List[str] = []
    for i, it in enumerate(items, 1):
        date_str = (it.get("date") or "-").strip()
        stage    = (it.get("stage") or "-").strip()
        time_str = (it.get("time") or "")
        head = f"{i}. {date_str}  {stage}"
        if time_str: head += f"  {time_str}"
        lines.append(head)
        for note in it.get("notes") or []:
            note = str(note).strip()
            if note:
                lines.append(f"💬 備註：{note}")
    return lines

# ========= 視圖輸出 =========
def _type_key_label(case_type: Optional[str]) -> Tuple[str,str]:
    t = (case_type or "")
    if "刑" in t: return "CRIM","刑事"
    if "民" in t: return "CIVIL","民事"
    return "OTHER","其他"

def _render_case_detail(case: CaseRecord) -> str:
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
    tl = _build_timeline(getattr(case, "progress_stages", None),
                         getattr(case, "progress_notes", None),
                         getattr(case, "progress_times", None))
    if tl: lines += tl
    else: lines.append("（目前沒有進度記錄）")
    lines.append("────────────────────")
    lines.append(f"🟥建立時間：{created_at}")
    lines.append(f"🟩更新時間：{updated_at}")
    return "\n".join(lines)

def _render_category_menu(menu: List[Dict[str, Any]]) -> str:
    lines = ["🗂 案件類別選單","────────────────────"]
    for i, m in enumerate(menu, 1):
        lines.append(f"{i}. {m['label']}案件列表（{m['count']} 件）")
    lines.append("")
    lines.append(f"💡 請輸入選項號碼 (1-{len(menu)})")
    return "\n".join(lines)

def _render_case_list(items: List[Dict[str, Any]], label: str) -> str:
    lines = [f"📂 {label}案件列表","────────────────────"]
    for i, it in enumerate(items, 1):
        num = it.get("case_number") or "-"
        reason = it.get("case_reason") or "-"
        lines.append(f"{i}. {reason}（案件編號：{num}）")
    lines.append("")
    lines.append(f"💡 請輸入選項號碼 (1-{len(items)})")
    return "\n".join(lines)

# ========= 資料層 =========
def _get_registered_name(db: Session, lid: str) -> Optional[str]:
    r = db.execute(text("""
      SELECT expected_name
      FROM pending_line_users
      WHERE line_user_id=:lid AND status='registered'
      ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
      LIMIT 1
    """), {"lid": lid}).first()
    return r[0].strip() if r and r[0] else None

def _set_pending_name(db: Session, lid: str, name: str):
    db.execute(text("""
      INSERT INTO pending_line_users(line_user_id, expected_name, status, created_at, updated_at)
      VALUES (:lid, :name, 'confirming', NOW(), NOW())
      ON CONFLICT (line_user_id) DO UPDATE
      SET expected_name = EXCLUDED.expected_name,
          status = 'confirming',
          updated_at = NOW()
    """), {"lid": lid, "name": name})
    db.commit()

def _confirm_register(db: Session, lid: str):
    db.execute(text("""
      UPDATE pending_line_users
      SET status='registered', updated_at=NOW()
      WHERE line_user_id=:lid
    """), {"lid": lid})
    db.commit()

def _retry_register(db: Session, lid: str):
    db.execute(text("""
      UPDATE pending_line_users
      SET status='retry', updated_at=NOW()
      WHERE line_user_id=:lid
    """), {"lid": lid})
    db.commit()

# ========= /register：只處理登錄 =========
@user_router.post("/register", response_model=RegisterOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)):
    lid  = payload.line_user_id
    text = _normalize_text(payload.text)

    # 1) 登錄 XXX
    m = re.match(r"^(?:登錄|登陸|登入|登录)\s+(.+?)\s*$", text or "", flags=re.I)
    if m:
        name = m.group(1).strip()
        if not name:
            return RegisterOut(success=False, message="請輸入「登錄 您的大名」完成登錄。", route="INFO")
        _set_pending_name(db, lid, name)
        return RegisterOut(success=True, message=f"請確認您的大名「{name}」。回覆「是」確認，「否」重新輸入。", expected_name=name, route="REGISTER_PREPARE")

    # 2) 是 / 否
    if text in ("是","yes","Yes","YES"):
        _confirm_register(db, lid)
        name = _get_registered_name(db, lid)
        tip = "（回覆「?」可查詢案件）" if name else ""
        return RegisterOut(success=True, message=f"已完成登錄{name and '：'+name or ''}。{tip}".strip(), expected_name=name, route="REGISTER_DONE")
    if text in ("否","no","No","NO"):
        _retry_register(db, lid)
        return RegisterOut(success=True, message="已取消，請重新輸入「登錄 您的大名」。", route="REGISTER_RETRY")

    # 其餘：不在 /register 處理
    return RegisterOut(success=True, message="如需登錄，請輸入「登錄 您的大名」。查詢請改用「/api/user/my-case」。", route="INFO")

# ========= /my-case：只處理查詢 =========
@user_router.post("/my-case", response_model=MyCaseOut)
def my_case(payload: MyCaseIn, db: Session = Depends(get_db)):
    lid  = payload.line_user_id
    text = _normalize_text(payload.text)
    include_as_opponent = bool(payload.include_as_opponent)

    # 必須先完成登錄
    reg_name = _get_registered_name(db, lid)
    if not reg_name:
        return MyCaseOut(success=False, message="尚未登錄，請先輸入「登錄 您的大名」。", route="INFO")

    # 數字選單處理
    if re.fullmatch(r"[1-9]\d*", text or ""):
        sess = _load_session(db, lid)
        if not sess:
            return MyCaseOut(success=False, message="選單已失效，請先回覆「?」重新取得列表。", route="INFO")
        scope = sess["scope"]; data = sess["payload"]

        # 選類別
        if scope == "CAT_MENU":
            idx = int(text) - 1
            cats = data.get("categories") or []
            if idx < 0 or idx >= len(cats):
                return MyCaseOut(success=False, message="選項超出範圍，請重新輸入。", route="INFO")
            chosen = cats[idx]
            items = chosen.get("items") or []
            if len(items) == 1:
                # 只有一筆 → 直接詳情
                case_id = items[0]["id"]
                case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
                _clear_session(db, lid)
                return MyCaseOut(success=True, message=_render_case_detail(case), route="CASE_DETAIL")
            # 多筆 → 顯示清單並進入 CASE_MENU
            _save_session(db, lid, "CASE_MENU", {"items": items, "label": chosen["label"]})
            return MyCaseOut(success=True, message=_render_case_list(items, chosen["label"]), route="MENU_LIST")

        # 選案件
        if scope == "CASE_MENU":
            idx = int(text) - 1
            items = data.get("items") or []
            if idx < 0 or idx >= len(items):
                return MyCaseOut(success=False, message="選項超出範圍，請重新輸入。", route="INFO")
            case_id = items[idx]["id"]
            case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
            _clear_session(db, lid)
            return MyCaseOut(success=True, message=_render_case_detail(case), route="CASE_DETAIL")

        return MyCaseOut(success=False, message="選單狀態無效，請回覆「?」重新開始。", route="ERROR")

    # 「?」或其他文字 → 拉清單
    if text == "?":
        # 抓名下案件
        if include_as_opponent:
            q = db.query(CaseRecord).filter(or_(CaseRecord.client == reg_name,
                                                CaseRecord.opposing_party == reg_name))
        else:
            q = db.query(CaseRecord).filter(CaseRecord.client == reg_name)
        q = q.order_by(text("updated_date DESC NULLS LAST, updated_at DESC NULLS LAST, id DESC"))
        rows: List[CaseRecord] = q.all()

        if not rows:
            _clear_session(db, lid)
            return MyCaseOut(success=True, message=f"沒有找到「{reg_name}」的案件。", route="INFO")

        if len(rows) == 1:
            _clear_session(db, lid)
            return MyCaseOut(success=True, message=_render_case_detail(rows[0]), route="CASE_DETAIL")

        # 分類（刑/民/其他）
        buckets: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            key, label = _type_key_label(r.case_type)
            buckets.setdefault(key, {"label": label, "items": []})
            buckets[key]["items"].append({
                "id": r.id,
                "case_number": r.case_number or r.case_id,
                "case_reason": r.case_reason,
                "case_type": r.case_type,
            })

        cats = []
        for key in ["CRIM","CIVIL","OTHER"]:
            if key in buckets:
                cats.append({"key": key,
                             "label": buckets[key]["label"],
                             "count": len(buckets[key]["items"]),
                             "items": buckets[key]["items"]})

        if len(cats) == 1:
            # 只有單一類別 → 直接進入清單
            items = cats[0]["items"]
            _save_session(db, lid, "CASE_MENU", {"items": items, "label": cats[0]["label"]})
            return MyCaseOut(success=True, message=_render_case_list(items, cats[0]["label"]), route="MENU_LIST")

        # 多類別 → 顯示類別選單
        _save_session(db, lid, "CAT_MENU", {"categories": cats})
        return MyCaseOut(success=True, message=_render_category_menu(
            [{"label": c["label"], "count": c["count"]} for c in cats]
        ), route="MENU_CATEGORY")

    # 其他文字不在這支處理
    return MyCaseOut(success=True, message="查詢請回覆「?」，或輸入清單的數字選項。", route="INFO")
