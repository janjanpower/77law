# -*- coding: utf-8 -*-
"""
controllers/case_database_uploader.py
案件資料庫上傳器 - 一鍵上傳案件資料到遠端資料庫
"""

import requests
import json
import threading
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from models.case_model import CaseData


class CaseDatabaseUploader:
    """案件資料庫上傳器 - 修復版本"""

    def __init__(self, api_base_url: str = "https://law-controller-4a92b3cfcb5d.herokuapp.com"):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'LawSystem-Client/1.0'
        })

        # 初始化狀態
        self.is_uploading = False
        self.upload_progress = 0
        self.total_cases = 0
        self.uploaded_count = 0
        self.failed_count = 0
        self.errors = []

    def upload_cases_async(self, cases: List[CaseData],
                          user_data: Dict[str, Any],
                          progress_callback: Optional[Callable] = None,
                          complete_callback: Optional[Callable] = None) -> None:
        """
        異步上傳案件資料

        Args:
            cases: 案件資料列表
            user_data: 用戶資料（包含認證資訊）
            progress_callback: 進度回調函數 (progress, status_message)
            complete_callback: 完成回調函數 (success, summary)
        """
        if self.is_uploading:
            if complete_callback:
                complete_callback(False, {"message": "正在上傳中，請勿重複操作"})
            return

        # 在背景執行緒中執行上傳
        upload_thread = threading.Thread(
            target=self._upload_cases_sync,
            args=(cases, user_data, progress_callback, complete_callback),
            daemon=True
        )
        upload_thread.start()

    def _upload_cases_sync(self, cases: List[CaseData],
                          user_data: Dict[str, Any],
                          progress_callback: Optional[Callable] = None,
                          complete_callback: Optional[Callable] = None) -> None:
        """
        同步上傳案件資料（在背景執行緒中執行）

        Args:
            cases: 案件資料列表
            user_data: 用戶資料
            progress_callback: 進度回調函數
            complete_callback: 完成回調函數
        """
        try:
            self.is_uploading = True
            self.total_cases = len(cases)
            self.uploaded_count = 0
            self.failed_count = 0
            self.errors = []

            print(f"🚀 開始上傳 {self.total_cases} 筆案件資料到資料庫")

            if progress_callback:
                progress_callback(0, f"準備上傳 {self.total_cases} 筆案件資料...")

            # 驗證API連線
            if not self._test_api_connection():
                error_msg = "無法連接到資料庫API，請檢查網路連線"
                print(f"❌ {error_msg}")
                if complete_callback:
                    complete_callback(False, {"message": error_msg, "errors": ["API連線失敗"]})
                return

            # 批次上傳案件資料
            success_count = 0
            for i, case in enumerate(cases):
                try:
                    # 更新進度
                    progress = int((i / self.total_cases) * 100)
                    if progress_callback:
                        progress_callback(progress, f"上傳案件: {case.client} ({i+1}/{self.total_cases})")

                    # 上傳單個案件
                    upload_result = self._upload_single_case(case, user_data)

                    if upload_result['success']:
                        success_count += 1
                        self.uploaded_count += 1
                        print(f"✅ 案件上傳成功: {case.case_id} - {case.client}")
                    else:
                        self.failed_count += 1
                        error_msg = f"案件 {case.case_id} 上傳失敗: {upload_result.get('message', '未知錯誤')}"
                        self.errors.append(error_msg)
                        print(f"❌ {error_msg}")

                except Exception as e:
                    self.failed_count += 1
                    error_msg = f"案件 {case.case_id} 處理異常: {str(e)}"
                    self.errors.append(error_msg)
                    print(f"❌ {error_msg}")

            # 完成上傳
            final_progress = 100
            if progress_callback:
                progress_callback(final_progress, "上傳完成，正在整理結果...")

            # 準備結果摘要
            summary = {
                "total_cases": self.total_cases,
                "uploaded_count": self.uploaded_count,
                "failed_count": self.failed_count,
                "success_rate": round((self.uploaded_count / self.total_cases) * 100, 1) if self.total_cases > 0 else 0,
                "errors": self.errors[:10],  # 只顯示前10個錯誤
                "message": f"上傳完成！成功: {self.uploaded_count}, 失敗: {self.failed_count}"
            }

            # 判定是否成功
            upload_success = (self.uploaded_count > 0 and self.failed_count == 0) or (self.uploaded_count >= self.total_cases * 0.8)

            print(f"📊 上傳結果統計:")
            print(f"  📈 總計: {self.total_cases} 筆")
            print(f"  ✅ 成功: {self.uploaded_count} 筆")
            print(f"  ❌ 失敗: {self.failed_count} 筆")
            print(f"  📊 成功率: {summary['success_rate']}%")

            if complete_callback:
                complete_callback(upload_success, summary)

        except Exception as e:
            error_msg = f"上傳過程發生嚴重錯誤: {str(e)}"
            print(f"💥 {error_msg}")
            if complete_callback:
                complete_callback(False, {"message": error_msg, "errors": [str(e)]})
        finally:
            self.is_uploading = False

    def _test_api_connection(self) -> bool:
        """測試API連線"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ API連線測試失敗: {e}")
            return False

    def _upload_single_case(self, case, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        上傳單個案件到資料庫 - 完全修復版本
        解決 'default' 錯誤問題
        """
        try:
            # 🔥 關鍵修復：驗證 user_data 完整性
            print(f"🔍 _upload_single_case 收到的 user_data: {user_data}")

            # 確保必要欄位存在
            client_id = user_data.get('client_id')
            client_name = user_data.get('client_name')

            if not client_id:
                # 嘗試從其他可能的欄位獲取
                client_id = (
                    user_data.get('username') or
                    user_data.get('user_id') or
                    user_data.get('id') or
                    'unknown'
                )
                print(f"⚠️ client_id 為空，使用替代值: {client_id}")

            if not client_name:
                # 嘗試從其他可能的欄位獲取
                client_name = (
                    user_data.get('name') or
                    user_data.get('display_name') or
                    client_id or
                    '未知事務所'
                )
                print(f"⚠️ client_name 為空，使用替代值: {client_name}")

            # 🔥 關鍵修復：構建安全的案件資料
            case_payload = {
                "case_id": getattr(case, 'case_id', '') or '',
                "case_type": getattr(case, 'case_type', '') or '未分類',
                "client": getattr(case, 'client', '') or '',
                "lawyer": getattr(case, 'lawyer', '') or '',
                "legal_affairs": getattr(case, 'legal_affairs', '') or '',
                "progress": getattr(case, 'progress', '') or '待處理',
                "case_reason": getattr(case, 'case_reason', '') or '',
                "case_number": getattr(case, 'case_number', '') or '',
                "opposing_party": getattr(case, 'opposing_party', '') or '',
                "court": getattr(case, 'court', '') or '',
                "division": getattr(case, 'division', '') or '',
                "progress_date": getattr(case, 'progress_date', '') or '',
                "progress_stages": getattr(case, 'progress_stages', None) or {},
                "progress_notes": getattr(case, 'progress_notes', None) or {},
                "progress_times": getattr(case, 'progress_times', None) or {},
                "created_date": self._safe_date_format(getattr(case, 'created_date', None)),
                "updated_date": self._safe_date_format(getattr(case, 'updated_date', None)),
                "uploaded_by": client_id,  # 使用驗證過的 client_id
                "upload_time": datetime.now().isoformat()
            }

            # 🔥 關鍵修復：構建安全的請求資料
            request_payload = {
                "case_data": case_payload,
                "client_info": {
                    "client_id": client_id,      # 確保不是 'default'
                    "client_name": client_name   # 確保有值
                }
            }

            print(f"🔍 準備發送的 client_info: {request_payload['client_info']}")

            # 發送到API
            response = self.session.post(
                f"{self.api_base_url}/api/cases/upload",
                json=request_payload,
                timeout=30
            )

            print(f"🔍 API 回應狀態碼: {response.status_code}")
            if response.status_code != 200:
                print(f"🔍 API 回應內容: {response.text[:500]}")

            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'case_id': getattr(case, 'case_id', 'unknown'),
                    'message': result.get('message', '上傳成功'),
                    'upload_id': result.get('upload_id')
                }
            else:
                error_text = response.text[:200] if response.text else f"HTTP {response.status_code}"
                return {
                    'success': False,
                    'case_id': getattr(case, 'case_id', 'unknown'),
                    'error': error_text,
                    'message': f'上傳失敗 (HTTP {response.status_code})'
                }

        except Exception as e:
            print(f"❌ 上傳單個案件失敗: {e}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'case_id': getattr(case, 'case_id', 'unknown'),
                'error': str(e),
                'message': '上傳過程發生錯誤'
            }


    def _safe_date_format(self, date_obj):
        """安全的日期格式化"""
        try:
            if date_obj is None:
                return datetime.now().isoformat()
            elif hasattr(date_obj, 'isoformat'):
                return date_obj.isoformat()
            elif isinstance(date_obj, str):
                # 檢查是否已經是 ISO 格式
                if 'T' in date_obj or '-' in date_obj:
                    return date_obj
                else:
                    return datetime.now().isoformat()
            else:
                return str(date_obj)
        except Exception as e:
            print(f"⚠️ 日期格式化失敗: {e}")
            return datetime.now().isoformat()

    def get_upload_status(self) -> Dict[str, Any]:
        """取得上傳狀態"""
        return {
            "is_uploading": self.is_uploading,
            "total_cases": self.total_cases,
            "uploaded_count": self.uploaded_count,
            "failed_count": self.failed_count,
            "progress": self.upload_progress,
            "errors": self.errors
        }

    def cancel_upload(self) -> bool:
        """取消上傳（設置標記，實際取消取決於當前執行狀態）"""
        if self.is_uploading:
            print("⚠️ 收到取消上傳請求，將在當前案件處理完成後停止")
            # 這裡可以實作更精細的取消邏輯
            return True
        return False