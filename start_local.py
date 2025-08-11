# -*- coding: utf-8 -*-
"""
start_local.py
法律案件管理系統 v4.1 - 簡化版（可從環境變數/.env 讀取 API_BASE_URL）
"""
try:
    from utils.updater import check_and_update
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    MANIFEST_URL = "https://你的伺服器/manifest.json"  # 你發布更新的 JSON
    if check_and_update(MANIFEST_URL, APP_ROOT):
        # 已更新，重新啟動自己
        import subprocess, sys
        python = sys.executable
        subprocess.Popen([python] + sys.argv)
        sys.exit(0)
except Exception as e:
    print(f"[Updater] 更新檢查失敗：{e}")

import locale
import platform
import os
import sys
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, Optional

# --- 新增：讀取 .env（可選） ---
try:
    from pathlib import Path
    from dotenv import load_dotenv  # 若沒裝也不影響
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 讀取 .env：{env_path}")
except Exception as _e:
    pass

# --- 新增：統一取得 API Base URL ---
DEFAULT_API_BASE = "https://law-controller-4a92b3cfcb5d.herokuapp.com"
API_BASE_URL = os.getenv("API_BASE_URL", DEFAULT_API_BASE).rstrip("/")

def fix_encoding():
    try:
        if platform.system() == "Windows":
            locale.setlocale(locale.LC_ALL, 'Chinese_Taiwan.utf8')
        else:
            locale.setlocale(locale.LC_ALL, 'zh_TW.UTF-8')
        return True
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
            return True
        except locale.Error:
            print("⚠️ 編碼設定警告，但不影響主要功能")
            return True

def fix_import_path():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        paths_to_add = [
            current_dir,
            os.path.join(current_dir, 'views'),
            os.path.join(current_dir, 'controllers'),
            os.path.join(current_dir, 'models'),
            os.path.join(current_dir, 'utils'),
            os.path.join(current_dir, 'config')
        ]
        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)
        print("✅ Python 路徑設定完成")
        return True
    except Exception as e:
        print(f"❌ 路徑設定失敗: {e}")
        return False

def create_error_dialog(message: str, title: str = "系統錯誤"):
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message, parent=root)
        root.destroy()
    except Exception as e:
        print(f"錯誤對話框顯示失敗: {e}")
        print(f"原始錯誤訊息: {message}")

def show_login_window() -> Optional[Dict[str, Any]]:
    """顯示登入視窗"""
    try:
        print("🔐 啟動登入系統...")
        print(f"🌐 API_BASE_URL = {API_BASE_URL}")

        from controllers.login_controller import LoginController

        login_result = {'success': False, 'user_data': None}

        def on_login_success(user_data: Dict[str, Any]):
            """登入成功回調：確保顯示正確名稱"""
            login_result['success'] = True
            login_result['user_data'] = user_data

            # 後端 /client-login 會回: client_name / client_id / token ...
            client_name = (user_data.get('client_name') or "").strip()
            client_id   = (user_data.get('client_id') or "").strip()
            username    = (user_data.get('username') or "").strip()

            # 顯示優先順序：client_name > client_id > username > 'unknown'
            display_name = client_name or client_id or username or 'unknown'
            print(f"✅ 登入成功: {display_name}")

            global current_user_data
            current_user_data = user_data

        # <<< 這裡改成讀環境變數，不再寫死 >>>
        login_controller = LoginController(
            api_base_url=API_BASE_URL,
            on_login_success=on_login_success
        )

        print("⏳ 等待使用者登入...")
        login_controller.show()

        if login_result['success']:
            return login_result['user_data']
        else:
            print("❌ 登入失敗或使用者取消")
            return None

    except ImportError as e:
        error_msg = f"""登入系統載入失敗:
{str(e)}

請確認以下檔案存在:
• views/login_logic.py
• controllers/login_controller.py
"""
        print(f"❌ 登入系統載入失敗: {e}")
        create_error_dialog(error_msg, "登入系統錯誤")
        return None
    except Exception as e:
        error_msg = f"""登入系統啟動失敗:
{str(e)}

可能的原因:
1. 網路連線問題
2. 伺服器暫時無法存取
3. 配置檔案錯誤
"""
        print(f"❌ 登入系統啟動失敗: {e}")
        create_error_dialog(error_msg, "系統啟動失敗")
        return None

def show_main_window(user_data: Dict[str, Any]) -> bool:
    """顯示主視窗 - 加強版除錯"""
    try:
        print("🏠 啟動主視窗...")
        print(f"🔍 收到的用戶資料: {user_data}")

        from views.main_window import MainWindow
        main_window = MainWindow()
        print("✅ 主視窗物件建立成功")

        if hasattr(main_window, 'set_user_data'):
            print("🔍 主視窗有 set_user_data 方法，準備傳遞資料")
            main_window.set_user_data(user_data)
            print("✅ 用戶資料已傳遞給主視窗")
        else:
            print("❌ 主視窗沒有 set_user_data 方法")

        username = (user_data.get('username') or "").strip()
        client_id = (user_data.get('client_id') or "").strip()
        client_name = (user_data.get('client_name') or "").strip()

        display_name = client_name or client_id or username or 'unknown'

        if hasattr(main_window, 'window') and hasattr(main_window.window, 'title'):
            if client_name:
                new_title = f"法律案件管理系統 - {client_name} ({client_id or username})"
            else:
                new_title = f"法律案件管理系統 - {display_name}"
            main_window.window.title(new_title)
            print(f"✅ 主視窗標題已更新: {new_title}")

        if hasattr(main_window, 'on_user_login'):
            print("🔍 主視窗有 on_user_login 方法，準備調用")
            main_window.on_user_login(user_data)
            print("✅ on_user_login 已調用")
        else:
            print("⚠️ 主視窗沒有 on_user_login 方法")

        if hasattr(main_window, 'set_logout_callback'):
            main_window.set_logout_callback(handle_user_logout)

        print(f"👋 歡迎使用法律案件管理系統，{display_name}！")
        print("✅ 主視窗載入完成")

        if hasattr(main_window, 'run'):
            main_window.run()
        elif hasattr(main_window, 'mainloop'):
            main_window.mainloop()
        elif hasattr(main_window, 'window'):
            main_window.window.mainloop()

        return True

    except Exception as e:
        error_msg = f"主視窗啟動失敗: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False

def check_system_integrity() -> bool:
    print("🔍 檢查系統完整性...")
    critical_files = [
        "config/settings.py",
        "views/base_window.py",
        "controllers/login_controller.py",
        "views/login_logic.py",
        "views/main_window.py"
    ]
    missing_files = [p for p in critical_files if not os.path.exists(p)]
    if missing_files:
        error_msg = f"""系統檔案完整性檢查失敗:

缺少關鍵檔案:
{chr(10).join(f"• {f}" for f in missing_files)}
"""
        create_error_dialog(error_msg, "系統檔案缺失")
        return False
    print("✅ 系統完整性檢查完成")
    return True

def main():
    print("=" * 70)
    print("📋 法律案件管理系統 v4.1")
    print("🏢 專業Python工程團隊開發")
    print("🔐 Heroku資料庫登入驗證系統")
    print("🚀 簡化版 - 直接進入主視窗")
    print("=" * 70)

    try:
        print("\n🔧 步驟 1: 修正編碼設定")
        if not fix_encoding():
            print("⚠️ 編碼設定有問題，但將嘗試繼續執行")

        print("\n📁 步驟 2: 初始化模組路徑")
        if not fix_import_path():
            create_error_dialog("模組路徑初始化失敗！\n\n請確認程式檔案結構完整", "初始化失敗")
            return False

        print("\n📋 步驟 3: 檢查系統完整性")
        if not check_system_integrity():
            return False

        print("\n🔐 步驟 4: 啟動使用者登入")
        user_data = show_login_window()
        if not user_data:
            print("❌ 登入失敗或使用者取消，程式結束")
            return False

        print("\n🏠 步驟 5: 直接啟動主視窗")
        success = show_main_window(user_data)
        if success:
            print("\n🎉 系統啟動完成！")
            return True
        else:
            print("\n❌ 主視窗啟動失敗")
            return False

    except KeyboardInterrupt:
        print("\n⚠️ 使用者中斷程式執行")
        return False
    except Exception as e:
        print(f"\n❌ 系統啟動失敗: {e}")
        create_error_dialog(
            f"程式執行發生嚴重錯誤:\n{str(e)}\n\n請重新啟動或聯繫技術支援。",
            "嚴重錯誤"
        )
        return False

# ==================== 全域變數和輔助功能 ====================
current_user_data: Optional[Dict[str, Any]] = None

def get_current_user() -> Optional[Dict[str, Any]]:
    return current_user_data

def handle_user_logout():
    global current_user_data
    try:
        print("🔓 處理用戶登出...")
        current_user_data = None
        try:
            from views.login_logic import LoginLogic
            LoginLogic().clear_session()
            print("✅ 本地會話已清除")
        except Exception as e:
            print(f"⚠️ 清除會話時發生錯誤: {e}")
        main()
    except Exception as e:
        print(f"❌ 登出處理失敗: {e}")
        sys.exit(1)

# ==================== 程式入口點 ====================
if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 程式執行發生嚴重錯誤: {e}")
        try:
            create_error_dialog(
                f"程式執行發生嚴重錯誤:\n{str(e)}\n\n請重新啟動程式或聯繫技術支援。",
                "嚴重錯誤"
            )
        except Exception:
            pass
        sys.exit(2)
