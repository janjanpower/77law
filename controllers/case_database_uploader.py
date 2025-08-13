# -*- coding: utf-8 -*-
"""
與 CaseOverviewWindow._on_upload_to_database 相容的上傳器
- 非同步上傳（thread）
- 進度回呼（progress_callback）
- 批次上傳 + 簡易重試
- 支援 CaseData 物件或 dict
端點：POST {API_BASE_URL}/api/cases/upsert  -> public.case_records
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable, Union
import os
import json
import threading
import time
import requests

API_DEFAULT = os.getenv("API_BASE_URL", "https://law-controller-4a92b3cfcb5d.herokuapp.com").rstrip("/")

JsonDict = Dict[str, Any]
CaseLike = Union[JsonDict, Any]  # 支援 dict 或具屬性的 CaseData

def _as_json_obj(v: Any) -> Optional[dict]:
    if v is None or v == "":
        return None
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return None

def _norm_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None

def _serialize_case(case: CaseLike) -> JsonDict:
    """把 CaseData 或 dict 統一轉成上傳欄位 Key"""
    # 物件屬性讀取
    def g(name: str, *aliases: str) -> Any:
        # dict
        if isinstance(case, dict):
            for k in (name, *aliases):
                if k in case and case[k] not in (None, ""):
                    return case[k]
            return None
        # 物件屬性
        for k in (name, *aliases):
            if hasattr(case, k):
                v = getattr(case, k)
                if v not in (None, ""):
                    return v
        return None

    return {
        "case_id":         _norm_str(g("case_id", "流水號", "id")),
        "client":          _norm_str(g("client", "當事人", "當事人姓名")),
        "case_type":       _norm_str(g("case_type", "案件類型", "類型")),
        "progress":        _norm_str(g("progress", "案件進度", "進度")),
        "case_reason":     _norm_str(g("case_reason", "案由")),
        "case_number":     _norm_str(g("case_number", "案號")),
        "opposing_party":  _norm_str(g("opposing_party", "對造當事人")),
        "lawyer":          _norm_str(g("lawyer", "負責律師")),
        "legal_affairs":   _norm_str(g("legal_affairs", "承辦法務")),
        "court":           _norm_str(g("court", "法院")),
        "division":        _norm_str(g("division", "股別")),
        "created_date":    _norm_str(g("created_date", "建立日期", "created_at")),
        "updated_date":    _norm_str(g("updated_date", "更新日期", "updated_at")),
        "progress_date":   _norm_str(g("progress_date", "進度日期")),
        # 三個 JSON 欄位
        "progress_stages": _as_json_obj(g("progress_stages", "進度階段")),
        "progress_notes":  _as_json_obj(g("progress_notes", "備註")),
        "progress_times":  _as_json_obj(g("progress_times", "時間戳")),
    }

class CaseDatabaseUploader:
    def __init__(self, api_base: Optional[str] = None, token: Optional[str] = None):
        self.api_base = (api_base or API_DEFAULT).rstrip("/")
        self.token = token  # 可在 upload_cases_async 時從 user_data 補
        self._cancel = False
        self._thread: Optional[threading.Thread] = None

        self._uploaded_count = 0
        self._failed_count = 0

        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        if self.token:
            self._session.headers.update({"Authorization": f"Bearer {self.token}"})

        self._upsert_url = f"{self.api_base}/api/cases/upsert"

    # ========= 對外介面，與 CaseOverviewWindow 相容 =========
    def upload_cases_async(
        self,
        cases: List[CaseLike],
        user_data: Dict[str, Any],
        progress_callback: Callable[[int, str], None],
        complete_callback: Callable[[bool, Dict[str, Any]], None],
        chunk_size: int = 100,
        per_chunk_retry: int = 2,
    ) -> None:
        """啟動背景執行緒，非同步上傳"""
        self._cancel = False
        self._uploaded_count = 0
        self._failed_count = 0

        # 從 user_data 補 token（若有）
        token = user_data.get("token")
        if token:
            self.token = token
            self._session.headers["Authorization"] = f"Bearer {token}"

        args = (cases, user_data, progress_callback, complete_callback, chunk_size, per_chunk_retry)
        self._thread = threading.Thread(target=self._worker, args=args, daemon=True)
        self._thread.start()

    def cancel_upload(self) -> None:
        self._cancel = True

    def get_upload_status(self) -> Dict[str, int]:
        return {
            "uploaded_count": self._uploaded_count,
            "failed_count": self._failed_count,
        }

    # ========= 內部實作 =========
    def _worker(
        self,
        cases: List[CaseLike],
        user_data: Dict[str, Any],
        progress_cb: Callable[[int, str], None],
        complete_cb: Callable[[bool, Dict[str, Any]], None],
        chunk_size: int,
        per_chunk_retry: int,
    ) -> None:
        try:
            total = len(cases)
            if total == 0:
                complete_cb(False, {"message": "沒有案件可上傳"})
                return

            client_id = user_data.get("client_id") or user_data.get("client") or user_data.get("username")
            uploaded_by = user_data.get("client_name") or user_data.get("username") or "未命名使用者"

            # 前處理：序列化＋注入 client_id / uploaded_by
            normalized: List[JsonDict] = []
            for c in cases:
                if self._cancel:
                    progress_cb(100, "已取消上傳")
                    complete_cb(False, {"message": "用戶取消"})
                    return

                d = _serialize_case(c)
                if not d.get("case_id"):
                    continue
                if client_id:
                    d["client_id"] = str(client_id)
                if uploaded_by:
                    d["uploaded_by"] = str(uploaded_by)
                normalized.append(d)

            if not normalized:
                complete_cb(False, {"message": "沒有有效案件（缺少 case_id）"})
                return

            # 批次上傳
            batches = [normalized[i:i + max(1, chunk_size)] for i in range(0, len(normalized), max(1, chunk_size))]
            total_batches = len(batches)

            for idx, batch in enumerate(batches, start=1):
                if self._cancel:
                    progress_cb(100, "已取消上傳")
                    complete_cb(False, {"message": "用戶取消"})
                    return

                ok, err = self._post_upsert_with_retry(batch, per_chunk_retry)

                if ok:
                    self._uploaded_count += len(batch)
                    pct = min(99, int((idx / total_batches) * 100))
                    progress_cb(pct, f"第 {idx}/{total_batches} 批上傳成功（{len(batch)} 筆）")
                else:
                    self._failed_count += len(batch)
                    pct = min(99, int((idx / total_batches) * 100))
                    progress_cb(pct, f"第 {idx}/{total_batches} 批上傳失敗：{err}")

            # 完成
            progress_cb(100, "上傳完成")
            complete_cb(True, {
                "total": len(normalized),
                "uploaded": self._uploaded_count,
                "failed": self._failed_count
            })

        except Exception as e:
            complete_cb(False, {"message": f"例外：{e}"})

    def _post_upsert_with_retry(self, payload: List[JsonDict], retry: int) -> (bool, str):
        for attempt in range(retry + 1):
            try:
                resp = self._session.post(self._upsert_url, json=payload, timeout=25)
                if 200 <= resp.status_code < 300:
                    return True, ""
                err = f"HTTP {resp.status_code} {resp.text[:200]}"
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            # backoff
            if attempt < retry:
                time.sleep(1.2 * (attempt + 1))
            else:
                return False, err
