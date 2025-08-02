#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件管理系統 - 主程式入口（編碼修正版本）
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
import locale

def fix_encoding():
    """修正編碼問題"""
    try:
        # 設定系統預設編碼
        if sys.platform.startswith('win'):
            # Windows 系統
            locale.setlocale(locale.LC_ALL, 'Chinese_Taiwan.utf8')
        else:
            # Linux/Mac 系統
            locale.setlocale(locale.LC_ALL, 'zh_TW.UTF-8')

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
            from views.base_window import BaseWindow
            from views.dialogs import UnifiedMessageDialog

            print("✅ 核心模組載入成功")
            return True

        except ImportError as e:
            print(f"⚠️ 警告：部分模組載入失敗 - {e}")
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

def main():
    """主程式入口點 - 編碼修正版本"""
    print("=" * 50)
    print("📋 案件管理系統 v2.0")
    print("🏢 專業Python工程團隊開發")
    print("=" * 50)

    try:
        # 步驟 1: 修正編碼問題
        print("\n🔧 步驟 1: 修正編碼設定")
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

        # 步驟 3: 載入並啟動主應用程式
        print("\n🚀 步驟 3: 載入主應用程式")
        from views.main_window import MainWindow

        app = MainWindow()
        print("✅ 主應用程式初始化完成")

        app.run()
        return True

    except Exception as e:
        error_msg = f"程式啟動失敗:\n{str(e)}"
        print(f"❌ 程式啟動失敗: {e}")
        create_error_dialog(error_msg, "啟動失敗")
        return False

if __name__ == "__main__":
    # 確保在正確的工作目錄中執行
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 執行主程式
    success = main()
    sys.exit(0 if success else 1)