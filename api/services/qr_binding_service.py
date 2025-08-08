#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
services/qr_binding_service.py
法律案件管理系統 - QR綁定服務層
負責處理QR Code生成、綁定狀態檢查等邏輯
"""

import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime
import time


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
start_local.py (修正版)
法律案件管理系統 - 本地啟動檔案
智能處理模組缺失，提供向後相容性
"""

import sys
import os
import traceback
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, Any

# 添加專案根目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 設定環境變數
os.environ.setdefault('PYTHONPATH', current_dir)

# 檢查QR綁定功能是否可用
QR_BINDING_AVAILABLE = False

def check_qr_binding_availability():
    """檢查QR綁定相關模組是否可用"""
    global QR_BINDING_AVAILABLE

    try:
        # 檢查必要的檔案是否存在
        required_files = [
            os.path.join(current_dir, 'controllers', 'qr_binding_controller.py'),
            os.path.join(current_dir, 'views', 'binding_success_dialog.py')
        ]

        files_exist = all(os.path.exists(f) for f in required_files)

        if files_exist:
            # 嘗試導入模組
            from controllers.qr_binding_controller import QRBindingController
            from views.binding_success_dialog import BindingSuccessDialog
            QR_BINDING_AVAILABLE = True
            print("✅ QR綁定功能可用")
        else:
            print("⚠️ QR綁定相關檔案不存在")

    except ImportError as e:
        print(f"⚠️ QR綁定模組導入失敗: {e}")
    except Exception as e:
        print(f"⚠️ QR綁定功能檢查異常: {e}")

def create_error_dialog(message: str, title: str = "系統錯誤"):
    """建立錯誤對話框"""
    try:
        root = tk.Tk()
        root.withdraw()  # 隱藏主視窗
        messagebox.showerror(title, message)
        root.destroy()
    except Exception as e:
        print(f"❌ 顯示錯誤對話框失敗: {e}")

def show_login_window():
    """顯示登入視窗 - 智能處理QR綁定功能"""
    try:
        print("🔐 啟動登入系統...")

        # 檢查QR綁定功能可用性
        check_qr_binding_availability()

        # 導入登入控制器
        from controllers.login_controller import LoginController

        # 建立登入視窗實例
        login_window = LoginController(
            api_base_url="https://law-controller.herokuapp.com",
            on_login_success=show_main_window  # 登入成功後顯示主視窗
        )

        print("✅ 登入視窗建立完成")

        if QR_BINDING_AVAILABLE:
            print("🔗 QR綁定功能已啟用")
        else:
            print("⚠️ QR綁定功能不可用，將使用傳統登入流程")

        # 執行登入視窗
        login_window.run()

        # 取得登入結果
        user_data = login_window.get_user_data()

        if user_data:
            print(f"✅ 登入成功: {user_data.get('client_name', 'unknown')}")
            return user_data
        else:
            print("ℹ️ 用戶取消登入")
            return None

    except ImportError as e:
        error_msg = f"""登入系統載入失敗:
{str(e)}

可能的原因:
1. 缺少必要的模組檔案
2. 檔案路徑設定錯誤
3. 相依套件未安裝

請確認以下檔案存在:
- controllers/login_controller.py
- views/login_logic.py
- config/settings.py

如果是QR綁定相關錯誤，系統將使用傳統登入模式。"""

        print(f"❌ 登入系統載入失敗: {e}")
        create_error_dialog(error_msg, "登入系統載入失敗")
        return None

    except Exception as e:
        error_msg = f"""登入系統啟動失敗:
{str(e)}

可能的原因:
1. 網路連線問題
2. 伺服器暫時無法存取
3. 配置檔案錯誤

請檢查網路連線後重試，或聯繫技術支援。"""

        print(f"❌ 登入系統啟動失敗: {e}")
        create_error_dialog(error_msg, "系統啟動失敗")
        return None

def show_main_window(user_data: Dict[str, Any]):
    """顯示主視窗 - 增強版"""
    try:
        print("🏠 啟動主視窗...")
        print(f"👤 當前用戶: {user_data.get('client_name', 'unknown')}")

        if 'current_users' in user_data and 'max_users' in user_data:
            print(f"👥 使用人數: {user_data.get('current_users', 0)}/{user_data.get('max_users', 5)}")

        # 導入主視窗
        from views.main_window import MainWindow

        # 建立主視窗實例
        main_window = MainWindow()

        # 傳遞完整的用戶資料給主視窗
        if hasattr(main_window, 'set_user_data'):
            main_window.set_user_data(user_data)
            print("✅ 用戶資料已傳遞給主視窗")

        # 更新主視窗標題顯示當前用戶
        username = user_data.get('username') or user_data.get('client_id', 'unknown')
        client_name = user_data.get('client_name', '')

        if hasattr(main_window, 'window') and hasattr(main_window.window, 'title'):
            if client_name:
                new_title = f"法律案件管理系統 - {client_name} ({username})"
            else:
                new_title = f"法律案件管理系統 - {username}"
            main_window.window.title(new_title)

        # 如果主視窗支援登入事件，呼叫它
        if hasattr(main_window, 'on_user_login'):
            main_window.on_user_login(user_data)

        # 設定登出回調
        if hasattr(main_window, 'set_logout_callback'):
            main_window.set_logout_callback(handle_user_logout)

        print(f"👋 歡迎使用法律案件管理系統，{client_name or username}！")
        print("✅ 主視窗載入完成")

        # 啟動主視窗事件循環
        if hasattr(main_window, 'run'):
            main_window.run()
        elif hasattr(main_window, 'mainloop'):
            main_window.mainloop()
        elif hasattr(main_window, 'window'):
            main_window.window.mainloop()
        else:
            print("⚠️ 主視窗沒有標準的啟動方法，嘗試直接顯示")

        return True

    except ImportError as e:
        error_msg = f"""主視窗載入失敗:
{str(e)}

請確認 views/main_window.py 檔案存在且格式正確。

如果是第一次執行，請確認所有必要檔案都已正確安裝。"""

        print(f"❌ 主視窗載入失敗: {e}")
        create_error_dialog(error_msg, "主視窗錯誤")
        return False

    except Exception as e:
        error_msg = f"""主視窗啟動失敗:
{str(e)}

可能的原因:
1. 視窗系統不相容
2. 顯示器設定問題
3. 記憶體不足

請嘗試重新啟動程式，或聯繫技術支援。"""

        print(f"❌ 主視窗啟動失敗: {e}")
        create_error_dialog(error_msg, "主視窗錯誤")
        return False

def handle_user_logout():
    """處理用戶登出"""
    print("👋 用戶登出，返回登入畫面...")

    try:
        # 重新啟動登入流程
        main()
    except Exception as e:
        print(f"❌ 登出處理失敗: {e}")
        sys.exit(1)

def setup_environment():
    """設定執行環境"""
    try:
        # 檢查Python版本
        if sys.version_info < (3, 7):
            raise RuntimeError("此系統需要 Python 3.7 或更高版本")

        # 檢查必要模組
        required_modules = [
            'tkinter',
        ]

        # 可選模組（QR綁定功能需要）
        optional_modules = {
            'requests': 'API通訊功能',
            'PIL': 'QR Code圖片處理 (請使用: pip install Pillow)',
            'qrcode': 'QR Code生成 (請使用: pip install qrcode[pil])'
        }

        missing_required = []
        missing_optional = []

        # 檢查必要模組
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_required.append(module)

        # 檢查可選模組
        for module, description in optional_modules.items():
            try:
                __import__(module)
            except ImportError:
                missing_optional.append(f"{module} - {description}")

        if missing_required:
            error_msg = f"""缺少必要的套件:
{', '.join(missing_required)}

請執行以下命令安裝:
pip install {' '.join(missing_required)}"""

            raise ImportError(error_msg)

        if missing_optional:
            print("⚠️ 以下可選模組未安裝，部分功能可能不可用:")
            for module_info in missing_optional:
                print(f"   - {module_info}")
            print("\n🔧 安裝這些模組可啟用完整功能:")
            print("   pip install requests Pillow qrcode[pil]\n")

        print("✅ 執行環境檢查完成")
        return True

    except Exception as e:
        error_msg = f"""執行環境設定失敗:
{str(e)}

請確認:
1. Python 版本 >= 3.7
2. 已安裝所有必要套件
3. 檔案權限正確"""

        print(f"❌ 執行環境設定失敗: {e}")
        create_error_dialog(error_msg, "環境設定錯誤")
        return False

def main():
    """主程式入口"""
    try:
        print("=" * 60)
        print("🚀 法律案件管理系統 - 本地版本啟動")
        print(f"📍 工作目錄: {current_dir}")
        print(f"🐍 Python 版本: {sys.version}")
        print("=" * 60)

        # 設定執行環境
        if not setup_environment():
            sys.exit(1)

        # 顯示登入視窗並啟動整個流程
        user_data = show_login_window()

        if not user_data:
            print("ℹ️ 程式結束")
            sys.exit(0)

        print("✅ 程式執行完成")

    except KeyboardInterrupt:
        print("\n⚠️ 用戶中斷程式執行")
        sys.exit(0)

    except Exception as e:
        error_msg = f"""系統啟動失敗:
{str(e)}

錯誤詳情:
{traceback.format_exc()}

請聯繫技術支援並提供此錯誤資訊。"""

        print(f"❌ 系統啟動失敗: {e}")
        print(traceback.format_exc())
        create_error_dialog(error_msg, "系統啟動失敗")
        sys.exit(1)

if __name__ == "__main__":
    main()
    def refresh_user_data(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        重新取得最新的用戶資料

        Args:
            client_id: 事務所客戶端ID

        Returns:
            Optional[Dict]: 最新的用戶資料
        """
        try:
            url = f"{self.api_base_url}/api/auth/plan-info/{client_id}"

            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 用戶資料刷新成功")
                return {
                    "client_id": result.get('client_id'),
                    "client_name": result.get('client_name'),
                    "plan_type": result.get('plan_type'),
                    "current_users": result.get('current_users', 0),
                    "max_users": result.get('max_users', 5),
                    "available_slots": result.get('available_slots', 0),
                    "usage_percentage": result.get('usage_percentage', 0),
                    "user_status": result.get('user_status', 'active')
                }

            else:
                print(f"❌ 刷新用戶資料失敗: HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 刷新用戶資料異常: {e}")
            return None

    def validate_qr_code(self, binding_code: str) -> Optional[Dict[str, Any]]:
        """
        驗證QR Code是否有效

        Args:
            binding_code: 綁定代碼

        Returns:
            Optional[Dict]: 驗證結果
        """
        try:
            url = f"{self.api_base_url}/api/tenant-management/bind-user"

            params = {"code": binding_code}

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "valid": True,
                    "binding_data": result.get('binding_data', {})
                }

            elif response.status_code == 404:
                return {
                    "success": False,
                    "valid": False,
                    "message": "QR Code 無效或已過期"
                }

            elif response.status_code == 410:
                return {
                    "success": False,
                    "valid": False,
                    "message": "QR Code 已過期"
                }

            elif response.status_code == 409:
                return {
                    "success": False,
                    "valid": False,
                    "message": "QR Code 已被使用"
                }

            else:
                print(f"❌ QR Code驗證失敗: HTTP {response.status_code}")
                return {
                    "success": False,
                    "valid": False,
                    "message": f"驗證失敗 ({response.status_code})"
                }

        except Exception as e:
            print(f"❌ QR Code驗證異常: {e}")
            return {
                "success": False,
                "valid": False,
                "message": f"驗證異常: {str(e)}"
            }

    def get_client_line_users(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        取得事務所的所有LINE用戶清單

        Args:
            client_id: 事務所客戶端ID

        Returns:
            Optional[Dict]: LINE用戶清單
        """
        try:
            url = f"{self.api_base_url}/api/tenant-routes/client-users/{client_id}"

            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "client_info": result.get('client_info', {}),
                    "line_users": result.get('line_users', [])
                }

            else:
                print(f"❌ 取得LINE用戶清單失敗: HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 取得LINE用戶清單異常: {e}")
            return None

    def cleanup_expired_qr_codes(self) -> bool:
        """
        清理過期的QR Code

        Returns:
            bool: 是否清理成功
        """
        try:
            url = f"{self.api_base_url}/api/tenant-management/cleanup-expired-qr"

            response = self.session.post(url, timeout=10)

            if response.status_code == 200:
                result = response.json()
                cleaned_count = result.get('cleaned_count', 0)
                print(f"✅ 已清理 {cleaned_count} 個過期的QR Code")
                return True

            else:
                print(f"❌ 清理過期QR Code失敗: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 清理過期QR Code異常: {e}")
            return False

    def test_connection(self) -> bool:
        """
        測試API連線狀態

        Returns:
            bool: 是否連線成功
        """
        try:
            url = f"{self.api_base_url}/api/health"

            response = self.session.get(url, timeout=5)

            if response.status_code == 200:
                print(f"✅ API連線正常")
                return True
            else:
                print(f"❌ API連線異常: HTTP {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"❌ 無法連接到API伺服器")
            return False

        except requests.exceptions.Timeout:
            print(f"❌ API連線逾時")
            return False

        except Exception as e:
            print(f"❌ API連線測試異常: {e}")
            return False