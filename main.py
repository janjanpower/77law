#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件管理系統 - 主程式入口（新 Services 架構版本）
"""

import locale
import os
import sys
import tkinter as tk
from tkinter import messagebox

from datetime import datetime

try:
    from services.services_controller import ServicesController
    from controllers.case_controller import CaseController  # 新的簡化版控制器
    from models.case_model import CaseData
    SERVICES_AVAILABLE = True
    print("✅ 新 Services 架構載入成功")
except ImportError as e:
    print(f"⚠️ 警告：新 Services 架構載入失敗 - {e}")
    print("🔄 嘗試使用舊版控制器...")
    try:
        from controllers.case_controller import CaseController
        SERVICES_AVAILABLE = False
        print("✅ 舊版控制器載入成功")
    except ImportError:
        print("❌ 無法載入任何控制器")
        SERVICES_AVAILABLE = False


def fix_encoding():
    """修正編碼問題"""
    try:
        # 設定系統預設編碼
        if sys.platform.startswith('win'):
            # Windows 系統
            try:
                locale.setlocale(locale.LC_ALL, 'Chinese_Taiwan.utf8')
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_ALL, 'zh_TW.UTF-8')
                except locale.Error:
                    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        else:
            # Linux/Mac 系統
            try:
                locale.setlocale(locale.LC_ALL, 'zh_TW.UTF-8')
            except locale.Error:
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')

        # 設定標準輸出編碼
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
            sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

        print("✅ 編碼設定完成")
        return True

    except Exception as e:
        print(f"⚠️ 編碼設定警告: {e}")
        # 編碼設定失敗不影響程式執行
        return True


def fix_import_path():
    """修正模組導入路徑"""
    try:
        # 處理 PyInstaller 打包後的路徑
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        # 確保基礎路徑在 sys.path 中
        if base_path not in sys.path:
            sys.path.insert(0, base_path)

        # 預載入關鍵模組以避免導入錯誤
        try:
            from config.settings import AppConfig
            print("✅ 配置模組載入成功")

            # 檢查是否有 GUI 相關模組
            try:
                from views.base_window import BaseWindow
                from views.dialogs import UnifiedMessageDialog
                print("✅ GUI 模組載入成功")
                return True
            except ImportError:
                print("⚠️ GUI 模組載入失敗，將使用命令列模式")
                return True

        except ImportError as e:
            print(f"⚠️ 警告：配置模組載入失敗 - {e}")
            return False

    except Exception as e:
        print(f"❌ 模組路徑修正失敗: {e}")
        return False


def create_error_dialog(message, title="系統錯誤"):
    """建立標準錯誤對話框 - 編碼安全版本"""
    try:
        root = tk.Tk()
        root.withdraw()

        # 確保訊息是 UTF-8 字串
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='ignore')
        if isinstance(title, bytes):
            title = title.decode('utf-8', errors='ignore')

        messagebox.showerror(title, message)
        root.destroy()

    except Exception as e:
        print(f"❌ 無法顯示錯誤對話框: {e}")
        print(f"原始錯誤: {message}")


def initialize_services_architecture(data_folder="./data"):
    """初始化新的 Services 架構"""
    try:
        print("\n🏗️ 初始化 Services 架構...")

        # 確保資料夾存在
        os.makedirs(data_folder, exist_ok=True)

        # 初始化 Services 控制器
        services = ServicesController(data_folder)

        # 初始化簡化的案件控制器
        controller = CaseController(data_folder)

        print("✅ Services 架構初始化完成")

        # 顯示系統狀態
        try:
            dashboard = services.get_system_dashboard()
            case_stats = dashboard.get('case_statistics', {})
            system_health = dashboard.get('system_health', {})

            print(f"\n📊 系統狀態:")
            print(f"   總案件數: {case_stats.get('total_cases', 0)}")
            print(f"   系統健康: {system_health.get('overall_status', 'unknown')}")
            print(f"   服務狀態: {len([s for s in system_health.get('services_status', {}).values() if s == 'healthy'])} 個服務正常")

        except Exception as e:
            print(f"⚠️ 系統狀態檢查失敗: {e}")

        return services, controller

    except Exception as e:
        print(f"❌ Services 架構初始化失敗: {e}")
        raise


def run_gui_mode():
    """執行 GUI 模式"""
    try:
        print("\n🖥️ 啟動 GUI 模式...")

        # 嘗試載入主視窗
        from views.main_window import MainWindow

        # 初始化 Services 架構
        services, controller = initialize_services_architecture()

        # 建立主視窗並傳入新的控制器
        app = MainWindow()

        # 如果主視窗支援新架構，更新控制器
        if hasattr(app, 'update_controller'):
            app.update_controller(controller)
            print("✅ 主視窗已更新為新架構")
        elif hasattr(app, 'case_controller'):
            app.case_controller = controller
            print("✅ 主視窗控制器已更新")
        else:
            print("⚠️ 主視窗未支援新架構，將使用預設控制器")

        print("✅ GUI 模式啟動完成")
        app.run()
        return True

    except ImportError:
        print("❌ GUI 模組不可用，將切換到命令列模式")
        return False
    except Exception as e:
        print(f"❌ GUI 模式啟動失敗: {e}")
        create_error_dialog(f"GUI 啟動失敗:\n{str(e)}", "GUI 錯誤")
        return False


def run_console_mode():
    """執行命令列模式"""
    try:
        print("\n💻 啟動命令列模式...")

        # 初始化 Services 架構
        services, controller = initialize_services_architecture()

        # 匯入並執行命令列應用程式
        from new_main_example import CaseManagementApp

        # 建立命令列應用程式實例
        console_app = CaseManagementApp(data_folder="./data")

        print("✅ 命令列模式啟動完成")

        # 詢問執行模式
        print("\n請選擇執行模式:")
        print("1. 互動式示範 (完整功能測試)")
        print("2. 快速示範 (自動建立測試資料)")
        print("3. 系統維護模式")
        print("4. API 模式 (僅啟動服務)")

        try:
            choice = input("請選擇 (1-4): ").strip()

            if choice == '1':
                console_app.run_interactive_demo()
            elif choice == '2':
                console_app.run_quick_demo()
            elif choice == '3':
                run_maintenance_mode(services, controller)
            elif choice == '4':
                run_api_mode(services, controller)
            else:
                print("❌ 無效的選擇，啟動互動式示範")
                console_app.run_interactive_demo()

        except KeyboardInterrupt:
            print("\n👋 使用者中斷程式")
        except Exception as e:
            print(f"❌ 命令列模式執行失敗: {e}")

        return True

    except Exception as e:
        print(f"❌ 命令列模式啟動失敗: {e}")
        return False


def run_maintenance_mode(services, controller):
    """執行系統維護模式"""
    print("\n🔧 系統維護模式")
    print("=" * 40)

    try:
        # 執行系統健康檢查
        print("1️⃣ 執行系統健康檢查...")
        dashboard = services.get_system_dashboard()
        system_health = dashboard.get('system_health', {})

        print(f"系統健康狀態: {system_health.get('overall_status', 'unknown')}")

        if system_health.get('issues'):
            print("發現的問題:")
            for issue in system_health['issues']:
                print(f"  - {issue}")

        # 執行資料驗證
        print("\n2️⃣ 執行資料完整性檢查...")
        validation_result = controller.validate_all_cases()

        if 'error' in validation_result:
            print(f"❌ 驗證失敗: {validation_result['error']}")
        else:
            print(f"總案件數: {validation_result['total_cases']}")
            print(f"有效案件: {validation_result['valid_cases']}")
            print(f"無效案件: {validation_result['invalid_cases']}")

        # 執行系統維護
        print("\n3️⃣ 執行系統維護...")
        maintenance_result = services.perform_system_maintenance()

        print(f"維護狀態: {maintenance_result['status']}")
        print(f"發現問題: {maintenance_result['total_issues_found']}")
        print(f"修復問題: {maintenance_result['total_issues_fixed']}")

        print("\n✅ 系統維護完成")

    except Exception as e:
        print(f"❌ 系統維護失敗: {e}")


def run_api_mode(services, controller):
    """執行 API 模式"""
    print("\n🔌 API 模式")
    print("=" * 40)

    try:
        print("🚀 服務已啟動，可以通過以下方式使用:")
        print("")
        print("📋 基本操作:")
        print("# 取得所有案件")
        print("cases = controller.get_cases()")
        print("")
        print("# 建立新案件")
        print("from models.case_model import CaseData")
        print("case = CaseData(case_id='', client='測試', case_type='民事')")
        print("success = controller.add_case(case, create_folder=True)")
        print("")
        print("# 取得系統狀態")
        print("dashboard = controller.get_system_dashboard()")
        print("")
        print("📊 進階操作:")
        print("# 套用進度範本")
        print("templates = controller.get_available_progress_templates()")
        print("controller.apply_progress_template(case_id, template_name)")
        print("")
        print("# 批量操作")
        print("result = controller.batch_create_folders(case_ids)")
        print("")
        print("# 匯入匯出")
        print("controller.import_from_excel(file_path)")
        print("controller.export_to_excel(file_path)")

        # 顯示當前狀態
        dashboard = services.get_system_dashboard()
        case_stats = dashboard.get('case_statistics', {})

        print(f"\n📈 當前狀態:")
        print(f"總案件數: {case_stats.get('total_cases', 0)}")
        print(f"緊急案件: {case_stats.get('urgent_cases', 0)}")

        print(f"\n💡 服務已準備就緒，您可以開始使用 API")
        print(f"按 Ctrl+C 停止服務")

        # 保持服務運行
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 API 服務已停止")

    except Exception as e:
        print(f"❌ API 模式啟動失敗: {e}")


def check_services_compatibility():
    """檢查 Services 架構相容性"""
    try:
        print("\n🔍 檢查 Services 架構相容性...")

        # 檢查必要的模組
        required_modules = [
            'services.services_controller',
            'services.case_service',
            'services.folder_service',
            'services.notification_service'
        ]

        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
                print(f"  ✅ {module}")
            except ImportError:
                missing_modules.append(module)
                print(f"  ❌ {module}")

        if missing_modules:
            print(f"\n⚠️ 缺少以下 Services 模組:")
            for module in missing_modules:
                print(f"   - {module}")
            print(f"\n將使用舊版架構...")
            return False
        else:
            print(f"✅ Services 架構相容性檢查通過")
            return True

    except Exception as e:
        print(f"❌ 相容性檢查失敗: {e}")
        return False


def main():
    """主程式入口"""
    print("🎯 案件管理系統啟動")
    print("版本: Services 架構版本")
    print("=" * 50)

    try:
        # 步驟 1: 修正編碼問題
        print("🔧 步驟 1: 修正編碼設定")
        if not fix_encoding():
            print("⚠️ 編碼設定有問題，但將嘗試繼續執行")

        # 步驟 2: 修正模組導入路徑
        print("\n📁 步驟 2: 初始化模組路徑")
        if not fix_import_path():
            create_error_dialog(
                "模組路徑初始化失敗！\n\n請確認程式檔案結構完整",
                "初始化失敗"
            )
            return False

        # 步驟 3: 檢查 Services 架構
        print("\n🏗️ 步驟 3: 檢查 Services 架構")
        services_available = check_services_compatibility()

        if not services_available:
            print("⚠️ Services 架構不完整，將嘗試使用舊版功能")

        # 步驟 4: 選擇啟動模式
        print("\n🚀 步驟 4: 選擇啟動模式")

        # 嘗試啟動 GUI 模式
        gui_success = run_gui_mode()

        if not gui_success:
            print("\n🔄 GUI 模式不可用，切換到命令列模式")
            console_success = run_console_mode()

            if not console_success:
                print("❌ 所有啟動模式都失敗")
                create_error_dialog(
                    "系統無法啟動！\n\n請檢查程式檔案完整性",
                    "啟動失敗"
                )
                return False

        return True

    except KeyboardInterrupt:
        print("\n👋 程式被使用者中斷")
        return True
    except Exception as e:
        error_msg = f"程式啟動失敗:\n{str(e)}"
        print(f"❌ 程式啟動失敗: {e}")
        create_error_dialog(error_msg, "啟動失敗")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 確保在正確的工作目錄中執行
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 執行主程式
    success = main()

    if success:
        print("\n✅ 程式正常結束")
    else:
        print("\n❌ 程式異常結束")

    sys.exit(0 if success else 1)