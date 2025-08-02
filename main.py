#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件管理系統 - 主程式入口（相容版本）
保持原有介面不變，後端使用新的Repository架構
"""

import locale
import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox


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
        return True


def fix_import_path():
    """修正模組導入路徑"""
    try:
        # 處理 PyInstaller 打包後的路徑
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        # 添加到路徑
        if base_path not in sys.path:
            sys.path.insert(0, base_path)

        print(f"✅ 路徑設定完成: {base_path}")
        return True

    except Exception as e:
        print(f"⚠️ 路徑設定警告: {e}")
        return True


def create_error_dialog(message, title="系統錯誤"):
    """建立標準錯誤對話框"""
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


def initialize_backend_architecture():
    """初始化後端架構（不影響前端介面）"""
    try:
        print("🔧 正在初始化後端Repository架構...")

        # 設定資料夾
        data_folder = "./data"
        os.makedirs(data_folder, exist_ok=True)

        # 嘗試初始化新的Repository架構
        backend_initialized = False

        try:
            from repositories.case_repository import CaseRepository
            from repositories.progress_repository import ProgressRepository
            from repositories.file_repository import FileRepository

            # 初始化Repository層
            case_repo = CaseRepository(os.path.join(data_folder, "cases.json"))
            progress_repo = ProgressRepository(data_folder)
            file_repo = FileRepository(data_folder)

            print("✅ Repository層初始化成功")
            backend_initialized = True

        except ImportError as e:
            print(f"⚠️ Repository層載入失敗: {e}")

        # 嘗試初始化服務層（可選）
        try:
            from services.services_controller import ServicesController
            services = ServicesController(data_folder)
            print("✅ Services層初始化成功")
        except ImportError as e:
            print(f"⚠️ Services層載入失敗，使用基本功能: {e}")
            services = None

        return {
            'backend_initialized': backend_initialized,
            'data_folder': data_folder,
            'services': services
        }

    except Exception as e:
        print(f"❌ 後端架構初始化失敗: {e}")
        return {
            'backend_initialized': False,
            'data_folder': "./data",
            'services': None
        }


def create_compatible_controller(backend_info):
    """創建相容的控制器（保持原有介面）"""
    try:
        data_folder = backend_info['data_folder']

        # 優先使用新架構的控制器
        if backend_info['backend_initialized']:
            try:
                # 嘗試使用更新版本的控制器
                from controllers.case_controller import CaseController
                controller = CaseController(data_folder)
                print("✅ 使用新架構控制器")
                return controller
            except ImportError:
                print("⚠️ 新架構控制器不可用")

        # 回退到舊版控制器或創建相容版本
        try:
            # 檢查是否有舊版控制器
            from controllers.case_controller import CaseController
            controller = CaseController(data_folder)
            print("✅ 使用相容控制器")
            return controller
        except ImportError:
            print("⚠️ 控制器模組不可用，創建基本控制器")

            # 創建基本的控制器類別
            class BasicCaseController:
                def __init__(self, data_folder):
                    self.data_folder = data_folder
                    os.makedirs(data_folder, exist_ok=True)

                    # 嘗試使用Repository
                    try:
                        from repositories.case_repository import CaseRepository
                        self.case_repository = CaseRepository(os.path.join(data_folder, "cases.json"))
                    except ImportError:
                        self.case_repository = None

                def add_case(self, case_data, **kwargs):
                    if self.case_repository:
                        return self.case_repository.create_case(case_data)
                    return False

                def get_cases(self):
                    if self.case_repository:
                        return self.case_repository.get_all_cases()
                    return []

                def get_case_by_id(self, case_id):
                    if self.case_repository:
                        return self.case_repository.get_case_by_id(case_id)
                    return None

                def update_case(self, case_data, **kwargs):
                    if self.case_repository:
                        return self.case_repository.update_case(case_data)
                    return False

                def delete_case(self, case_id, **kwargs):
                    if self.case_repository:
                        return self.case_repository.delete_case(case_id)
                    return False

                def search_cases(self, keyword, **kwargs):
                    if self.case_repository:
                        return self.case_repository.search_cases(keyword)
                    return []

                def get_cases_by_client(self, client_name):
                    if self.case_repository:
                        return self.case_repository.get_cases_by_client(client_name)
                    return []

                def get_cases_by_type(self, case_type):
                    if self.case_repository:
                        return self.case_repository.get_cases_by_type(case_type)
                    return []

            return BasicCaseController(data_folder)

    except Exception as e:
        print(f"❌ 控制器創建失敗: {e}")
        return None


def run_gui_mode():
    """執行 GUI 模式（保持原有介面）"""
    try:
        print("\n🖥️ 啟動圖形介面模式...")

        # 初始化後端架構
        backend_info = initialize_backend_architecture()

        # 創建相容的控制器
        controller = create_compatible_controller(backend_info)

        if controller is None:
            print("❌ 無法初始化控制器")
            return False

        # 嘗試載入原有的主視窗
        try:
            from views.main_window import MainWindow

            # 創建主視窗實例
            main_window = MainWindow()

            # 如果主視窗支援控制器注入，則更新控制器
            if hasattr(main_window, 'case_controller'):
                main_window.case_controller = controller
                print("✅ 主視窗控制器已更新為新架構")
            elif hasattr(main_window, 'controller'):
                main_window.controller = controller
                print("✅ 主視窗控制器已更新")
            else:
                print("⚠️ 主視窗未支援控制器注入，使用預設設定")

            print("✅ 圖形介面初始化成功")
            print("🚀 啟動原有介面...")

            # 執行主視窗
            main_window.run()
            return True

        except ImportError as e:
            print(f"❌ 原有主視窗載入失敗: {e}")

            # 創建基本的GUI
            root = tk.Tk()
            root.title("案件管理系統")
            root.geometry("600x400")

            import tkinter.ttk as ttk

            frame = ttk.Frame(root, padding="20")
            frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

            ttk.Label(frame, text="案件管理系統", font=("Arial", 16, "bold")).grid(row=0, column=0, pady=10)
            ttk.Label(frame, text="主視窗暫時不可用，請使用基本功能").grid(row=1, column=0, pady=5)

            # 狀態顯示
            status_text = tk.Text(frame, height=8, width=50)
            status_text.grid(row=2, column=0, pady=10)

            cases = controller.get_cases() if controller else []
            status_info = f"""
系統狀態:
- 後端架構: {'已初始化' if backend_info['backend_initialized'] else '基本模式'}
- 控制器: {'可用' if controller else '不可用'}
- 案件數量: {len(cases)}

這是臨時介面，原有介面將在修復後恢復正常。
"""
            status_text.insert(tk.END, status_info)
            status_text.config(state=tk.DISABLED)

            ttk.Button(frame, text="關閉", command=root.quit).grid(row=3, column=0, pady=10)

            print("✅ 基本GUI界面啟動")
            root.mainloop()
            return True

    except Exception as e:
        print(f"❌ GUI模式啟動失敗: {e}")
        return False


def run_console_mode():
    """執行命令列模式"""
    try:
        print("\n💻 啟動命令列模式...")

        # 初始化後端架構
        backend_info = initialize_backend_architecture()

        # 創建相容的控制器
        controller = create_compatible_controller(backend_info)

        if controller is None:
            print("❌ 無法初始化控制器")
            return False

        # 載入或創建案件模型
        try:
            from models.case_model import CaseData
        except ImportError:
            print("⚠️ 案件模型不可用，使用基本模型")

            class CaseData:
                def __init__(self, case_id, client, case_type, **kwargs):
                    self.case_id = case_id
                    self.client = client
                    self.case_type = case_type
                    for key, value in kwargs.items():
                        setattr(self, key, value)

        def show_menu():
            print("\n" + "=" * 50)
            print("📋 案件管理系統 - 命令列模式")
            print("=" * 50)
            print("1. 查看所有案件")
            print("2. 新增案件")
            print("3. 搜尋案件")
            print("4. 系統狀態")
            print("0. 退出")
            print("=" * 50)

        def list_cases():
            cases = controller.get_cases()
            if not cases:
                print("📭 目前沒有案件資料")
                return

            print(f"\n📁 共有 {len(cases)} 筆案件:")
            print("-" * 60)
            for i, case in enumerate(cases, 1):
                client = getattr(case, 'client', '未知')
                case_type = getattr(case, 'case_type', '未知')
                case_id = getattr(case, 'case_id', '未知')
                print(f"{i:2d}. [{case_id}] {client} - {case_type}")

        def add_case():
            print("\n➕ 新增案件")
            print("-" * 30)

            try:
                case_id = input("案件ID (按 Enter 自動生成): ").strip()
                if not case_id:
                    case_id = f"CASE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                client = input("當事人姓名: ").strip()
                if not client:
                    print("❌ 當事人姓名不能為空")
                    return

                case_type = input("案件類型 (民事/刑事/行政): ").strip()
                if not case_type:
                    case_type = "一般案件"

                notes = input("備註 (可選): ").strip()

                new_case = CaseData(
                    case_id=case_id,
                    client=client,
                    case_type=case_type,
                    notes=notes if notes else None
                )

                if controller.add_case(new_case):
                    print(f"✅ 成功新增案件: {client}")
                else:
                    print("❌ 案件新增失敗")

            except KeyboardInterrupt:
                print("\n❌ 操作已取消")
            except Exception as e:
                print(f"❌ 新增案件時發生錯誤: {e}")

        def search_cases():
            print("\n🔍 搜尋案件")
            print("-" * 30)

            try:
                keyword = input("請輸入搜尋關鍵字: ").strip()
                if not keyword:
                    print("❌ 搜尋關鍵字不能為空")
                    return

                results = controller.search_cases(keyword)

                if not results:
                    print(f"🔍 沒有找到包含 '{keyword}' 的案件")
                    return

                print(f"\n🎯 找到 {len(results)} 筆相關案件:")
                print("-" * 60)
                for i, case in enumerate(results, 1):
                    client = getattr(case, 'client', '未知')
                    case_type = getattr(case, 'case_type', '未知')
                    case_id = getattr(case, 'case_id', '未知')
                    print(f"{i:2d}. [{case_id}] {client} - {case_type}")

            except KeyboardInterrupt:
                print("\n❌ 操作已取消")
            except Exception as e:
                print(f"❌ 搜尋時發生錯誤: {e}")

        def show_status():
            print("\n📊 系統狀態")
            print("-" * 30)
            print(f"後端架構: {'Repository架構' if backend_info['backend_initialized'] else '基本模式'}")
            print(f"資料夾: {backend_info['data_folder']}")
            cases = controller.get_cases()
            print(f"案件數量: {len(cases)}")

        # 主命令列循環
        while True:
            try:
                show_menu()
                choice = input("\n請選擇操作 (0-4): ").strip()

                if choice == '0':
                    print("\n👋 謝謝使用，再見！")
                    break
                elif choice == '1':
                    list_cases()
                elif choice == '2':
                    add_case()
                elif choice == '3':
                    search_cases()
                elif choice == '4':
                    show_status()
                else:
                    print("❌ 無效的選擇，請重新輸入")

                input("\n按 Enter 繼續...")

            except KeyboardInterrupt:
                print("\n\n👋 謝謝使用，再見！")
                break
            except Exception as e:
                print(f"❌ 發生錯誤: {e}")
                input("\n按 Enter 繼續...")

        return True

    except Exception as e:
        print(f"❌ 命令列模式啟動失敗: {e}")
        return False


def main():
    """主函數"""
    try:
        print("=" * 60)
        print("🚀 案件管理系統啟動中...")
        print("📝 保持原有介面，後端使用Repository架構")
        print("=" * 60)

        # 修正編碼和路徑
        fix_encoding()
        fix_import_path()

        # 檢查啟動參數
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            if mode in ['console', 'cmd', 'cli']:
                print("🎯 強制使用命令列模式")
                success = run_console_mode()
            elif mode in ['gui', 'window']:
                print("🎯 強制使用圖形介面模式")
                success = run_gui_mode()
            else:
                print(f"❌ 未知的啟動模式: {mode}")
                print("💡 可用模式: console, gui")
                return False
        else:
            # 自動選擇模式 - 優先GUI
            print("\n🎯 嘗試啟動圖形介面模式...")

            try:
                # 檢查是否有圖形環境
                root = tk.Tk()
                root.withdraw()
                root.destroy()

                print("✅ 檢測到圖形環境")
                success = run_gui_mode()

                if not success:
                    print("\n❌ GUI模式啟動失敗，切換到命令列模式")
                    success = run_console_mode()

            except:
                print("⚠️ 未檢測到圖形環境，使用命令列模式")
                success = run_console_mode()

        if success:
            print("\n✅ 程式正常結束")
        else:
            print("\n❌ 程式異常結束")

        return success

    except KeyboardInterrupt:
        print("\n\n👋 使用者中斷程式，再見！")
        return True
    except Exception as e:
        print(f"\n❌ 程式執行時發生嚴重錯誤: {e}")
        create_error_dialog(f"程式啟動失敗:\n{str(e)}", "系統錯誤")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 確保在正確的工作目錄中執行
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 執行主程式
    success = main()
    sys.exit(0 if success else 1)