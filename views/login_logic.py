# -*- coding: utf-8 -*-
"""
views/login_logic.py (完善增強版)
法律案件管理系統 - 登入驗證邏輯層
整合您的需求：事務所認證、方案驗證、LINE用戶管理
"""

import os
import json
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import logging

class LoginLogic:
    """登入驗證邏輯層 - 專注於業務邏輯，不直接操作資料庫"""

    def __init__(self, api_base_url: str = "https://law-controller-4a92b3cfcb5d.herokuapp.com"):
        """
        初始化登入邏輯

        Args:
            api_base_url: Heroku API 基礎網址
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.session_timeout = timedelta(hours=8)

        # 本地設定檔路徑
        self.config_dir = Path.home() / ".law_system_config"
        self.config_dir.mkdir(exist_ok=True)
        self.session_file = self.config_dir / "session.json"
        self.config_file = self.config_dir / "app_config.json"

        # HTTP 會話設定
        self.session = requests.Session()
        self.session.timeout = 30
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'LawSystem-Client/1.0'
        })

        # 設定日誌
        self._setup_logging()

    def _setup_logging(self):
        """設定日誌系統"""
        log_file = self.config_dir / "login.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )
        self.logger = logging.getLogger(__name__)

    # ==================== 主要認證邏輯 ====================

    def authenticate_user(self, client_id: str, password: str) -> Dict[str, Any]:
        """
        主要認證方法 - 完整的業務邏輯驗證

        Args:
            client_id: 事務所帳號
            password: 密碼

        Returns:
            認證結果字典，包含 success, message, user_data
        """
        try:
            # 📝 記錄登入嘗試
            self.logger.info(f"登入嘗試: {client_id}")

            # 1️⃣ 基本輸入驗證
            validation_result = self._validate_login_input(client_id, password)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': validation_result['message'],
                    'user_data': {}
                }

            # # 2️⃣ 本地測試帳號檢查
            # if self._is_test_account(client_id, password):
            #     result = self._handle_test_account_login(client_id)
            #     self.logger.info(f"測試帳號登入成功: {client_id}")
            #     return result

            # 3️⃣ 網路連線檢查
            if not self._check_api_connectivity():
                return {
                    'success': False,
                    'message': '無法連接到認證伺服器，請檢查網路連線',
                    'user_data': {}
                }

            # 4️⃣ 呼叫API進行線上認證
            api_result = self._perform_online_authentication(client_id, password)

            # 5️⃣ 處理認證結果
            if api_result['success']:
                # 🎯 核心業務邏輯：付費狀態與方案驗證
                validated_result = self._validate_business_rules(api_result)

                if validated_result['success']:
                    # 儲存登入會話
                    self._save_login_session(validated_result['user_data'])
                    self.logger.info(f"登入成功: {client_id}")

                return validated_result
            else:
                self.logger.warning(f"登入失敗: {client_id} - {api_result['message']}")
                return api_result

        except Exception as e:
            self.logger.error(f"登入過程異常: {client_id} - {str(e)}")
            return {
                'success': False,
                'message': f'登入過程發生錯誤：{str(e)}',
                'user_data': {}
            }

    def _validate_login_input(self, client_id: str, password: str) -> Dict[str, Any]:
        """驗證登入輸入資料"""
        # 清理輸入
        client_id = client_id.strip()
        password = password.strip()

        if not client_id or not password:
            return {'valid': False, 'message': '請輸入完整的帳號和密碼'}

        if len(client_id) < 3:
            return {'valid': False, 'message': '帳號長度至少需要3個字元'}

        if len(password) < 3:
            return {'valid': False, 'message': '密碼長度至少需要3個字元'}

        # 檢查特殊字元 - 基本安全驗證
        if any(char in client_id for char in ['<', '>', '"', "'", ';', '&']):
            return {'valid': False, 'message': '帳號包含不允許的字元'}

        return {'valid': True, 'message': '驗證通過'}

    def _perform_online_authentication(self, client_id: str, password: str) -> Dict[str, Any]:
        """執行線上 API 認證（同時支援扁平與巢狀回傳格式），並保證回傳 user_data 有 client_id/client_name。"""
        try:
            auth_data = {
                "client_id": client_id,
                "password": password,
            }

            resp = self.session.post(
                f"{self.api_base_url}/api/auth/client-login",
                json=auth_data,
                timeout=15,
            )

            # --- 正常回應 ---
            if resp.status_code == 200:
                data = resp.json() if resp.content else {}

                # 兼容兩種回傳格式：
                # 1) 巢狀：{"success":true, "client_data": {...}}
                # 2) 扁平：{"success":true, "client_id":"...", "client_name":"...", "token":"..."}
                if isinstance(data.get("client_data"), dict):
                    user_data = dict(data["client_data"])  # 複製一份避免直接引用
                else:
                    user_data = {
                        "client_id":        data.get("client_id"),
                        "client_name":      data.get("client_name"),
                        "plan_type":        data.get("plan_type"),
                        "max_users":        data.get("max_users"),
                        "current_users":    data.get("current_users"),
                        "available_slots":  data.get("available_slots"),
                        "usage_percentage": data.get("usage_percentage"),
                        "last_login":       data.get("last_login"),
                        "user_status":      data.get("user_status"),
                        # JWT
                        "token":            data.get("token"),
                        "token_type":       data.get("token_type", "bearer"),
                        "expires_at":       data.get("expires_at"),
                    }

                # 後備：一定補上關鍵欄位，避免前端顯示 unknown
                if not (user_data.get("client_id") or "").strip():
                    user_data["client_id"] = client_id
                if not (user_data.get("client_name") or "").strip():
                    user_data["client_name"] = f"事務所_{user_data['client_id']}"

                return {
                    "success": True,
                    "message": data.get("message", "登入成功"),
                    "user_data": user_data,
                }

            # --- 錯誤情況（狀態碼） ---
            if resp.status_code == 401:
                return {"success": False, "message": "帳號或密碼錯誤，請重新輸入", "user_data": {}}
            if resp.status_code == 403:
                return {"success": False, "message": "帳號已被停用，請聯繫管理員", "user_data": {}}

            return {
                "success": False,
                "message": f"伺服器回應異常 (HTTP {resp.status_code})",
                "user_data": {},
            }

        except requests.exceptions.ConnectTimeout:
            return {"success": False, "message": "連線逾時，請檢查網路連線", "user_data": {}}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "無法連接到伺服器，請稍後再試", "user_data": {}}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"網路連線發生問題：{str(e)}", "user_data": {}}
        except Exception as e:
            return {"success": False, "message": f"認證過程發生錯誤：{str(e)}", "user_data": {}}


    # ==================== 🎯 核心業務邏輯：您的需求實現 ====================

    def _validate_business_rules(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """信任後端API驗證結果的簡單版本"""
        try:
            if api_result.get('success', False):
                user_data = api_result.get('user_data', {})
                client_id = user_data.get('client_id', '')

                self.logger.info(f"後端驗證成功，信任API結果: {client_id}")

                return {
                    'success': True,
                    'message': api_result.get('message', '登入成功'),
                    'user_data': user_data
                }
            else:
                return {
                    'success': False,
                    'message': api_result.get('message', '認證失敗'),
                    'user_data': {}
                }
        except Exception as e:
            return {
                'success': False,
                'message': '驗證異常',
                'user_data': {}
            }

    def _validate_plan_limits(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證方案限制"""
        try:
            plan_type = user_data.get('plan_type', 'basic')
            current_users = user_data.get('current_users', 0)
            max_users = user_data.get('max_users', 5)

            # 🎯 您的方案定義
            plan_configs = {
                'basic': {'max_users': 5, 'display_name': 'Basic (1-5人)'},
                'standard': {'max_users': 10, 'display_name': 'Standard (6-10人)'},
                'premium': {'max_users': 15, 'display_name': 'Premium (11-15人)'},
                'unlimited': {'max_users': 999, 'display_name': 'Unlimited (16人以上)'}
            }

            # 標準化方案類型
            normalized_plan = self._normalize_plan_type(plan_type)
            plan_config = plan_configs.get(normalized_plan, plan_configs['basic'])

            # 檢查是否超出限制
            if current_users >= max_users:
                return {
                    'valid': False,
                    'message': f'您的方案 ({plan_config["display_name"]}) 已達到用戶數上限 ({max_users}人)，無法再新增用戶'
                }

            return {
                'valid': True,
                'message': '方案驗證通過',
                'plan_config': plan_config
            }

        except Exception as e:
            return {
                'valid': False,
                'message': f'方案驗證失敗：{str(e)}'
            }

    def _normalize_plan_type(self, plan_type: str) -> str:
        """標準化方案類型名稱"""
        plan_type = plan_type.lower().strip()

        # 處理各種可能的命名
        if 'basic' in plan_type or '1-5' in plan_type or plan_type == '5':
            return 'basic'
        elif 'standard' in plan_type or '6-10' in plan_type or plan_type == '10':
            return 'standard'
        elif 'premium' in plan_type or '11-15' in plan_type or plan_type == '15':
            return 'premium'
        elif 'unlimited' in plan_type or '16' in plan_type or 'unlimit' in plan_type:
            return 'unlimited'
        else:
            return 'basic'  # 預設為基本方案

    def _enhance_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """增強用戶資料，添加計算欄位和顯示格式"""
        try:
            enhanced_data = user_data.copy()

            # 計算剩餘名額
            current_users = enhanced_data.get('current_users', 0)
            max_users = enhanced_data.get('max_users', 5)
            available_slots = max(0, max_users - current_users)

            # 計算使用率
            usage_percentage = round((current_users / max_users * 100), 1) if max_users > 0 else 0

            # 添加計算欄位
            enhanced_data.update({
                'available_slots': available_slots,
                'usage_percentage': usage_percentage,
                'usage_display': f"{current_users}/{max_users}",
                'is_full': current_users >= max_users,
                'is_near_limit': usage_percentage >= 80,
                'login_time': datetime.now().isoformat(),
                'session_id': self._generate_session_id(),
                'login_method': 'online_api',
                'permissions': self._get_user_permissions(enhanced_data)
            })

            # 確保關鍵欄位存在
            essential_fields = {
                'client_id': enhanced_data.get('client_id', 'unknown'),
                'client_name': enhanced_data.get('client_name', '未知事務所'),
                'plan_type': enhanced_data.get('plan_type', 'basic'),
                'tenant_status': enhanced_data.get('tenant_status', True),
                'user_status': enhanced_data.get('user_status', 'active')
            }
            enhanced_data.update(essential_fields)

            return enhanced_data

        except Exception as e:
            self.logger.error(f"增強用戶資料失敗: {str(e)}")
            return user_data

    def _get_user_permissions(self, user_data: Dict[str, Any]) -> List[str]:
        """根據用戶資料決定權限"""
        permissions = ['login', 'view_cases']

        # 根據方案添加權限
        plan_type = user_data.get('plan_type', 'basic')
        if plan_type in ['premium', 'unlimited']:
            permissions.extend(['export_data', 'advanced_reports'])

        # 檢查管理員權限
        client_id = user_data.get('client_id', '')
        if client_id == 'admin' or 'admin' in client_id.lower():
            permissions.extend(['admin_panel', 'user_management'])
            user_data['is_admin'] = True
        else:
            user_data['is_admin'] = False

        return permissions


    # ==================== 工具方法 ====================

    def _check_api_connectivity(self) -> bool:
        """檢查API連線狀態"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=10)
            return response.status_code == 200
        except:
            return False

    def check_api_connection(self) -> Tuple[bool, str]:
        """檢查API連線並返回詳細狀態"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=10)
            if response.status_code == 200:
                return True, "API連線正常"
            else:
                return False, f"API回應異常 (HTTP {response.status_code})"
        except requests.exceptions.ConnectTimeout:
            return False, "連線逾時"
        except requests.exceptions.ConnectionError:
            return False, "無法連接到伺服器"
        except Exception as e:
            return False, f"連線錯誤：{str(e)}"

    def _generate_session_id(self) -> str:
        """產生會話ID"""
        import uuid
        return str(uuid.uuid4())[:16]

    def _save_login_session(self, user_data: Dict[str, Any]):
        """儲存登入會話"""
        try:
            session_data = {
                'user_data': user_data,
                'login_time': datetime.now().isoformat(),
                'expires_at': (datetime.now() + self.session_timeout).isoformat()
            }

            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.warning(f"儲存會話失敗: {str(e)}")

    def check_session_validity(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """檢查會話是否有效"""
        try:
            if not self.session_file.exists():
                return False, None

            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            expires_at = datetime.fromisoformat(session_data['expires_at'])

            if datetime.now() > expires_at:
                # 會話過期
                self.session_file.unlink(missing_ok=True)
                return False, None

            return True, session_data['user_data']

        except Exception as e:
            self.logger.warning(f"會話檢查失敗: {str(e)}")
            return False, None

    def clear_session(self):
        """清除登入會話"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            self.logger.info("會話已清除")
        except Exception as e:
            self.logger.warning(f"清除會話失敗: {str(e)}")

    def save_user_credentials(self, client_id: str, password: str, remember: bool = False):
        """儲存用戶登入資訊（如果用戶選擇記住）"""
        try:
            config = self._load_config()

            if remember:
                # 簡單編碼（實際應用中建議使用更安全的方式）
                encoded_password = hashlib.md5(password.encode()).hexdigest()
                config['saved_credentials'] = {
                    'client_id': client_id,
                    'password_hash': encoded_password,
                    'remember': True,
                    'saved_at': datetime.now().isoformat()
                }
            else:
                config.pop('saved_credentials', None)

            self._save_config(config)

        except Exception as e:
            self.logger.warning(f"儲存登入資訊失敗: {str(e)}")

    def load_saved_credentials(self) -> Tuple[Optional[str], bool]:
        """載入儲存的登入資訊"""
        try:
            config = self._load_config()
            saved_creds = config.get('saved_credentials', {})

            if saved_creds.get('remember'):
                return saved_creds.get('client_id'), True
            else:
                return None, False

        except Exception as e:
            self.logger.warning(f"載入登入資訊失敗: {str(e)}")
            return None, False

    def _load_config(self) -> Dict[str, Any]:
        """載入設定檔"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}

    def _save_config(self, config: Dict[str, Any]):
        """儲存設定檔"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"儲存設定檔失敗: {str(e)}")

    def get_system_info(self) -> Dict[str, Any]:
        """獲取系統診斷資訊"""
        try:
            config = self._load_config()
            return {
                'api_url': self.api_base_url,
                'config_dir': str(self.config_dir),
                'has_saved_credentials': bool(self.load_saved_credentials()[0]),
                'has_active_session': self.check_session_validity()[0],
                'session_timeout_hours': self.session_timeout.total_seconds() / 3600,
                'last_config_update': config.get('last_update', 'never'),
                'version': '2.0-enhanced'
            }
        except Exception as e:
            return {'error': str(e)}

# ==================== LINE 用戶綁定相關方法 ====================

    def check_line_user_binding_availability(self, client_id: str) -> Dict[str, Any]:
        """檢查事務所是否還能綁定更多LINE用戶"""
        try:
            # 呼叫API檢查當前用戶數
            response = self.session.get(
                f"{self.api_base_url}/api/auth/client-status/{client_id}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    client_data = data.get('data', {})
                    current_users = client_data.get('current_users', 0)
                    max_users = client_data.get('max_users', 5)

                    return {
                        'can_bind': current_users < max_users,
                        'current_users': current_users,
                        'max_users': max_users,
                        'available_slots': max(0, max_users - current_users),
                        'plan_type': client_data.get('plan_type', 'basic')
                    }

            return {'can_bind': False, 'message': '無法取得事務所資訊'}

        except Exception as e:
            self.logger.error(f"檢查LINE用戶綁定可用性失敗: {str(e)}")
            return {'can_bind': False, 'message': f'檢查失敗：{str(e)}'}

