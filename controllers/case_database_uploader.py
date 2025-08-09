# -*- coding: utf-8 -*-
"""
controllers/case_database_uploader.py
案件資料庫上傳器 - 重寫版本
完全重新設計，確保與現有資料庫結構完美匹配
"""

import requests
import json
import threading
import time
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from models.case_model import CaseData


class CaseDatabaseUploader:
    """案件資料庫上傳器 - 重寫版本"""

    def __init__(self, api_base_url: str = "https://law-controller-4a92b3cfcb5d.herokuapp.com"):
        """
        初始化上傳器

        Args:
            api_base_url: API 基礎 URL
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'LawSystem-Desktop-Client/1.0'
        })

        # 狀態追蹤
        self.is_uploading = False
        self.upload_progress = 0
        self.total_cases = 0
        self.uploaded_count = 0
        self.failed_count = 0
        self.errors = []
        self.current_case_index = 0

        print(f"🔧 上傳器初始化完成，API URL: {self.api_base_url}")

    def upload_cases_async(self,
                          cases: List[CaseData],
                          user_data: Dict[str, Any],
                          progress_callback: Optional[Callable] = None,
                          complete_callback: Optional[Callable] = None) -> None:
        """
        異步上傳案件資料

        Args:
            cases: 案件資料列表
            user_data: 用戶認證資料
            progress_callback: 進度回調函數 (progress: int, message: str)
            complete_callback: 完成回調函數 (success: bool, summary: Dict)
        """
        print(f"🚀 開始異步上傳 {len(cases)} 筆案件")

        if self.is_uploading:
            print("⚠️ 已有上傳任務在進行中")
            if complete_callback:
                complete_callback(False, {"message": "已有上傳任務在進行中，請稍後再試"})
            return

        # 啟動上傳線程
        upload_thread = threading.Thread(
            target=self._upload_cases_sync,
            args=(cases, user_data, progress_callback, complete_callback),
            daemon=True,
            name="CaseUploadThread"
        )
        upload_thread.start()

    def _upload_cases_sync(self,
                          cases: List[CaseData],
                          user_data: Dict[str, Any],
                          progress_callback: Optional[Callable] = None,
                          complete_callback: Optional[Callable] = None) -> None:
        """
        同步上傳案件資料（在子線程中執行）
        """
        try:
            self._reset_upload_state()
            self.is_uploading = True
            self.total_cases = len(cases)

            print(f"📊 開始上傳任務: {self.total_cases} 筆案件")

            # 前置檢查
            if not self._pre_upload_checks(cases, user_data, progress_callback, complete_callback):
                return

            # 提取 client_id
            client_id = self._extract_client_id(user_data)
            if not client_id:
                error_msg = "無法從用戶資料中提取 client_id"
                print(f"❌ {error_msg}")
                print(f"🔍 用戶資料: {user_data}")
                if complete_callback:
                    complete_callback(False, {"message": error_msg, "errors": ["認證失敗"]})
                return

            print(f"✅ 用戶認證成功，client_id: {client_id}")

            # 開始上傳每個案件
            self._upload_all_cases(cases, client_id, progress_callback)

            # 整理上傳結果
            summary = self._generate_upload_summary()
            upload_success = self._determine_upload_success()

            print(f"📋 上傳任務完成:")
            print(f"  📈 總計: {self.total_cases} 筆")
            print(f"  ✅ 成功: {self.uploaded_count} 筆")
            print(f"  ❌ 失敗: {self.failed_count} 筆")


            if complete_callback:
                complete_callback(upload_success, summary)

        except Exception as e:
            error_msg = f"上傳過程發生嚴重錯誤: {str(e)}"
            print(f"💥 {error_msg}")
            import traceback
            traceback.print_exc()

            if complete_callback:
                complete_callback(False, {
                    "message": error_msg,
                    "errors": [str(e)],
                    "total_cases": self.total_cases,
                    "uploaded_count": self.uploaded_count,
                    "failed_count": self.failed_count
                })
        finally:
            self.is_uploading = False

    def _reset_upload_state(self):
        """重置上傳狀態"""
        self.upload_progress = 0
        self.uploaded_count = 0
        self.failed_count = 0
        self.errors = []
        self.current_case_index = 0

    def _pre_upload_checks(self, cases, user_data, progress_callback, complete_callback) -> bool:
        """前置檢查"""

        # 檢查案件數量
        if not cases:
            error_msg = "沒有案件資料可上傳"
            print(f"❌ {error_msg}")
            if complete_callback:
                complete_callback(False, {"message": error_msg})
            return False

        if progress_callback:
            progress_callback(0, f"正在準備上傳 {len(cases)} 筆案件...")

        # 檢查 API 連線
        if not self._test_api_connection():
            error_msg = "無法連接到雲端 API，請檢查網路連線"
            print(f"❌ {error_msg}")
            if complete_callback:
                complete_callback(False, {"message": error_msg, "errors": ["API 連線失敗"]})
            return False

        print("✅ API 連線測試成功")
        return True

    def _test_api_connection(self) -> bool:
        """測試 API 連線"""
        test_endpoints = [
            f"{self.api_base_url}/api/cases/health",
            f"{self.api_base_url}/health",
            f"{self.api_base_url}/docs"
        ]

        for endpoint in test_endpoints:
            try:
                print(f"🔍 測試連線: {endpoint}")
                response = self.session.get(endpoint, timeout=10)
                if response.status_code in [200, 404]:  # 404 也算連線成功
                    print(f"✅ 連線測試成功: {endpoint} ({response.status_code})")
                    return True
            except Exception as e:
                print(f"⚠️ 連線測試失敗: {endpoint} - {e}")
                continue

        print("❌ 所有連線測試都失敗")
        return False

    def _extract_client_id(self, user_data: Any) -> str:
        """🔥 修復：更健壯的 client_id 提取邏輯，處理字串和字典"""
        # 如果 user_data 本身就是字串，直接返回
        if isinstance(user_data, str) and user_data.strip():
            print(f"✅ user_data 是字串，直接使用: {user_data}")
            return user_data.strip()

        # 如果是字典，按優先順序嘗試提取
        if isinstance(user_data, dict):
            possible_keys = ['client_id', 'username', 'user_id', 'id', 'clientId']

            for key in possible_keys:
                value = user_data.get(key)
                if value and str(value).strip():
                    extracted_id = str(value).strip()
                    print(f"✅ 從字典的 '{key}' 提取到 client_id: {extracted_id}")
                    return extracted_id

        # 如果都失敗，嘗試轉換為字串
        if user_data:
            try:
                str_value = str(user_data).strip()
                if str_value and str_value != 'None':
                    print(f"✅ 將 user_data 轉換為字串: {str_value}")
                    return str_value
            except:
                pass

        print(f"❌ 無法從 user_data 提取 client_id: {user_data} (type: {type(user_data)})")
        return ""

    def _upload_all_cases(self, cases: List[CaseData], client_id: str, progress_callback: Optional[Callable]):
        """上傳所有案件"""

        for i, case in enumerate(cases):
            self.current_case_index = i + 1

            try:
                # 計算進度
                progress_percent = int((i / self.total_cases) * 100)
                case_display_name = self._get_case_display_name(case)

                if progress_callback:
                    progress_callback(
                        progress_percent,
                        f"上傳案件: {case_display_name} ({self.current_case_index}/{self.total_cases})"
                    )

                # 上傳單個案件
                result = self._upload_single_case(case, client_id)

                if result['success']:
                    self.uploaded_count += 1
                    print(f"✅ [{self.current_case_index}/{self.total_cases}] 上傳成功: {case_display_name}")
                else:
                    self.failed_count += 1
                    error_msg = f"[{self.current_case_index}/{self.total_cases}] {case_display_name} 上傳失敗: {result.get('message', '未知錯誤')}"
                    self.errors.append(error_msg)
                    print(f"❌ {error_msg}")

            except Exception as e:
                self.failed_count += 1
                error_msg = f"[{self.current_case_index}/{self.total_cases}] 案件處理異常: {str(e)}"
                self.errors.append(error_msg)
                print(f"💥 {error_msg}")

        # 最終進度更新
        if progress_callback:
            progress_callback(100, "上傳完成，正在整理結果...")

    def _get_case_display_name(self, case: CaseData) -> str:
        """取得案件顯示名稱"""
        case_id = getattr(case, 'case_id', '')
        client_name = getattr(case, 'client', '')

        if case_id and client_name:
            return f"{case_id} - {client_name}"
        elif case_id:
            return case_id
        elif client_name:
            return client_name
        else:
            return f"案件{self.current_case_index}"

    def _upload_single_case(self, case: CaseData, client_id: str) -> Dict[str, Any]:
        """
        上傳單個案件

        Args:
            case: 案件資料
            client_id: 事務所 ID

        Returns:
            Dict: {"success": bool, "message": str, "case_id": str}
        """
        case_id = getattr(case, 'case_id', '') or f"AUTO_{int(time.time())}_{self.current_case_index}"

        try:
            print(f"📤 準備上傳案件: {client_id}/{case_id}")

            # 構建案件資料 - 完全匹配現有資料庫結構
            case_data = self._build_case_data(case)

            # 構建 API 請求
            request_payload = {
                "client_id": client_id,
                "case_id": case_id,
                "data": case_data
            }

            print(f"🔍 請求資料: client_id={client_id}, case_id={case_id}")
            print(f"🔍 案件資料欄位: {list(case_data.keys())}")

            # 發送 HTTP 請求
            response = self.session.post(
                f"{self.api_base_url}/api/cases/upload",
                json=request_payload,
                timeout=30
            )

            return self._handle_upload_response(response, case_id)

        except requests.RequestException as e:
            error_msg = f"網路請求失敗: {str(e)}"
            print(f"🌐 {error_msg}")
            return {
                'success': False,
                'case_id': case_id,
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"上傳案件時發生異常: {str(e)}"
            print(f"💥 {error_msg}")
            return {
                'success': False,
                'case_id': case_id,
                'message': error_msg
            }

    def _build_case_data(self, case: CaseData) -> Dict[str, Any]:
        """
        構建案件資料 - 修復：完全匹配現有資料庫結構，移除不存在的欄位
        """
        # 取得案件屬性，沒有則使用預設值
        def get_attr(attr_name: str, default: Any = '') -> Any:
            return getattr(case, attr_name, default) or default

        case_data = {
            # 基本案件資訊 - 完全匹配資料庫欄位，移除不存在的 title, plaintiff, defendant
            "case_type": get_attr('case_type'),
            "client": get_attr('client'),
            "lawyer": get_attr('lawyer'),
            "legal_affairs": get_attr('legal_affairs'),

            # 案件狀態
            "progress": get_attr('progress', '待處理'),
            "case_reason": get_attr('case_reason'),
            "case_number": get_attr('case_number'),
            "opposing_party": get_attr('opposing_party'),
            "court": get_attr('court'),
            "division": get_attr('division'),
            "progress_date": get_attr('progress_date'),

            # JSON 欄位 - 確保是字典格式
            "progress_stages": get_attr('progress_stages', {}),
            "progress_notes": get_attr('progress_notes', {}),
            "progress_times": get_attr('progress_times', {}),

            # 時間戳記
            "created_date": get_attr('created_date'),
            "updated_date": get_attr('updated_date')
        }

        # 處理時間格式
        for time_field in ['created_date', 'updated_date']:
            if case_data[time_field] and hasattr(case_data[time_field], 'isoformat'):
                case_data[time_field] = case_data[time_field].isoformat()

        # 過濾掉空值 (但保留空字串和空字典)
        return {k: v for k, v in case_data.items() if v is not None}

    def _handle_upload_response(self, response: requests.Response, case_id: str) -> Dict[str, Any]:
        """處理上傳回應"""

        print(f"📨 API 回應: {response.status_code}")

        if response.status_code == 200:
            try:
                result = response.json()
                return {
                    'success': True,
                    'case_id': case_id,
                    'message': result.get('message', '上傳成功'),
                    'database_id': result.get('database_id')
                }
            except json.JSONDecodeError:
                # 即使 JSON 解析失敗，200 狀態碼仍視為成功
                print(f"⚠️ API 回應不是有效 JSON，但狀態碼為 200")
                return {
                    'success': True,
                    'case_id': case_id,
                    'message': '上傳成功 (回應格式異常)'
                }
        else:
            # 處理錯誤回應
            error_detail = self._extract_error_detail(response)
            print(f"❌ API 錯誤 ({response.status_code}): {error_detail}")

            return {
                'success': False,
                'case_id': case_id,
                'message': f"伺服器錯誤 ({response.status_code}): {error_detail}"
            }

    def _extract_error_detail(self, response: requests.Response) -> str:
        """提取錯誤詳情"""
        try:
            error_data = response.json()
            # 嘗試多種錯誤格式
            return (error_data.get('detail') or
                   error_data.get('message') or
                   error_data.get('error') or
                   str(error_data))
        except:
            # JSON 解析失敗，返回文字內容
            text = response.text.strip()
            return text[:200] if text else f"HTTP {response.status_code}"

    def _generate_upload_summary(self) -> Dict[str, Any]:
        """生成上傳摘要"""
        success_rate = 0
        if self.total_cases > 0:
            success_rate = round((self.uploaded_count / self.total_cases) * 100, 1)

        return {
            "total_cases": self.total_cases,
            "uploaded_count": self.uploaded_count,
            "failed_count": self.failed_count,
            "success_rate": success_rate,
            "errors": self.errors[-10:],  # 只保留最後 10 個錯誤
            "message": f"上傳完成！成功: {self.uploaded_count}, 失敗: {self.failed_count}"
        }

    def _determine_upload_success(self) -> bool:
        """判斷上傳是否成功"""
        if self.total_cases == 0:
            return False

        # 完全成功 或 成功率 >= 80%
        return (self.failed_count == 0) or (self.uploaded_count >= self.total_cases * 0.8)

    def get_upload_status(self) -> Dict[str, Any]:
        """取得上傳狀態"""
        return {
            'is_uploading': self.is_uploading,
            'progress': self.upload_progress,
            'total_cases': self.total_cases,
            'uploaded_count': self.uploaded_count,
            'failed_count': self.failed_count,
            'current_case_index': self.current_case_index,
            'recent_errors': self.errors[-3:] if self.errors else []
        }

    def cancel_upload(self):
        """取消上傳（軟取消，設定標記）"""
        print("⚠️ 收到取消上傳請求")
        # 注意：由於使用 threading，實際停止需要在上傳迴圈中檢查此狀態
        # 這裡只是設定標記，實際實作需要在上傳迴圈中檢查
        self.is_uploading = False

    def __del__(self):
        """清理資源"""
        if hasattr(self, 'session'):
            self.session.close()