# api/local_cases.py
# -*- coding: utf-8 -*-
"""
處理本地案件資料檔案（cases.json 與相容舊檔 case_data.json）
- upsert_case_local(data)  : 單筆更新或新增到 cases.json
- migrate_case_json()      : 如果還有舊檔 case_data.json，遷移到 cases.json
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # law_controller 專案根目錄
DATA_FILE_NEW = BASE_DIR / "cases.json"
DATA_FILE_OLD = BASE_DIR / "case_data.json"

def _read_json(path: Path) -> list:
    """讀取 JSON 檔，若不存在回傳空陣列"""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def _write_json(path: Path, data: list) -> None:
    """寫入 JSON 檔（確保縮排、美化）"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def migrate_case_json() -> bool:
    """
    如果有舊檔 case_data.json，但 cases.json 不存在 → 複製成 cases.json
    """
    if DATA_FILE_OLD.exists() and not DATA_FILE_NEW.exists():
        shutil.copy2(DATA_FILE_OLD, DATA_FILE_NEW)
        print(f"[migrate_case_json] case_data.json 已複製為 cases.json")
        return True
    return False

def upsert_case_local(case_data: dict) -> dict:
    """
    更新或新增案件到 cases.json
    case_data 需包含至少 client_id 與 case_id
    """
    if not case_data.get("client_id") or not case_data.get("case_id"):
        return {"ok": False, "message": "缺少 client_id 或 case_id"}

    # 讀取現有資料
    data = _read_json(DATA_FILE_NEW)

    # 檢查是否已存在該案件
    updated = False
    for idx, row in enumerate(data):
        if row.get("client_id") == case_data["client_id"] and row.get("case_id") == case_data["case_id"]:
            data[idx] = case_data
            updated = True
            break

    if not updated:
        case_data["local_saved_at"] = datetime.now().isoformat()
        data.append(case_data)

    # 寫回檔案
    _write_json(DATA_FILE_NEW, data)

    return {
        "ok": True,
        "updated": updated,
        "total_cases": len(data),
        "file": str(DATA_FILE_NEW)
    }
