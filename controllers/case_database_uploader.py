# -*- coding: utf-8 -*-
"""
controllers/case_database_uploader_fixed.py

前端「上傳雲端」功能（穩定版）
- 專責把案件清單整理成 API 需要的格式，並呼叫後端上傳
- 自動補齊 client_id / uploaded_by
- 支援分批上傳（避免一次 payload 過大）
- 明確回傳 summary 與 details，方便前端顯示／記錄
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import time
import math
import requests


class UploadError(Exception):
    pass


def _normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """把單筆案件資料轉為後端 /api/cases/upload 接受的欄位格式。
    後端欄位（建議）:
        case_type, client, lawyer, legal_affairs, progress,
        case_reason, case_number, opposing_party, court, division,
        progress_date, progress_stages(json), progress_notes(json), progress_times(json),
        case_id (自訂案件編號/流水號)
    """
    # 容錯處理：允許大小寫/不同 key 寫法
    def pick(*keys, default=None):
        for k in keys:
            if k in raw and raw[k] not in (None, ""):
                return raw[k]
        return default

    return {
        "case_type": pick("case_type", "類型"),
        "client": pick("client", "當事人", "客戶"),
        "lawyer": pick("lawyer", "律師"),
        "legal_affairs": pick("legal_affairs", "法務"),
        "progress": pick("progress", "進度"),
        "case_reason": pick("case_reason", "案由"),
        "case_number": pick("case_number", "案號"),
        "opposing_party": pick("opposing_party", "對造"),
        "court": pick("court", "法院"),
        "division": pick("division", "股別"),
        "progress_date": pick("progress_date", "日期"),
        "progress_stages": pick("progress_stages", "進度階段") or {},
        "progress_notes": pick("progress_notes", "備註") or {},
        "progress_times": pick("progress_times", "時間戳") or {},
        "case_id": pick("case_id", "id", "流水號"),
    }


def _chunk(items: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [items[i:i+size] for i in range(0, len(items), size)]


class CaseDatabaseUploader:
    """
    使用方式：
        uploader = CaseDatabaseUploader(api_base="https://your-app.herokuapp.com", token="...", client_id="1234", uploaded_by="admin")
        result = uploader.upload_cases(items, chunk_size=100)
    """
    def __init__(self, api_base: str, token: Optional[str], client_id: str, uploaded_by: str = "frontend"):
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.client_id = client_id
        self.uploaded_by = uploaded_by or "frontend"

    # ---- 公用工具 ----
    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _endpoint(self) -> str:
        # 前端預期的後端端點
        return f"{self.api_base}/api/cases/upload"

    # ---- 對外主函式 ----
    def upload_cases(self, items: List[Dict[str, Any]], chunk_size: int = 150, timeout: int = 30) -> Dict[str, Any]:
        if not items:
            return {"summary": {"total": 0, "success": 0, "failed": 0}, "batches": []}

        # 正規化
        normalized = [_normalize_item(x) for x in items]

        # ✅ 每筆補上 client_id / uploaded_by（舊相容）
        for it in normalized:
            it["client_id"] = str(self.client_id)
            it["uploaded_by"] = self.uploaded_by

        batches = _chunk(normalized, max(1, int(chunk_size)))
        success_total = failed_total = 0
        results = []

        for idx, batch in enumerate(batches, start=1):
            # ✅ 重點：在「頂層」也帶 client_id / uploaded_by（新需求）
            payload = {
                "client_id": str(self.client_id),
                "uploaded_by": self.uploaded_by,
                "items": batch,
            }
            try:
                resp = requests.post(self._endpoint(), headers=self._headers(), json=payload, timeout=timeout)
                if resp.status_code >= 400:
                    # 後端可能回 400/422，錯誤內容直接帶出
                    raise UploadError(f"HTTP {resp.status_code}: {resp.text}")

                data = resp.json() if resp.content else {}
                b_success = int(data.get("summary", {}).get("success", 0))
                b_failed  = int(data.get("summary", {}).get("failed", 0))
                success_total += b_success
                failed_total  += b_failed
                results.append({
                    "index": idx,
                    "count": len(batch),
                    "success": b_success,
                    "failed": b_failed,
                    "errors": data.get("errors", []),
                })
            except Exception as e:
                failed_total += len(batch)
                results.append({
                    "index": idx,
                    "count": len(batch),
                    "success": 0,
                    "failed": len(batch),
                    "errors": [str(e)],
                })

        return {
            "summary": {"total": sum(len(b) for b in batches), "success": success_total, "failed": failed_total},
            "batches": results,
        }

