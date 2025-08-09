#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""視圖模組"""
from .base_window import BaseWindow
from .main_window import MainWindow
from .case_form import CaseFormDialog

# 🔥 安全導入對話框類別
try:
    from .dialogs import ConfirmDialog, MessageDialog, UnifiedMessageDialog, UnifiedConfirmDialog
except ImportError as e:
    print(f"警告：無法導入對話框模組 - {e}")
    # 提供備用實作
    import tkinter.messagebox as messagebox

    class ConfirmDialog:
        @staticmethod
        def ask(parent, title="確認", message="確定要執行此操作嗎？"):
            return messagebox.askyesno(title, message)

    class MessageDialog:
        @staticmethod
        def show(parent, title="訊息", message="", dialog_type="info"):
            if dialog_type == "error":
                messagebox.showerror(title, message)
            elif dialog_type == "warning":
                messagebox.showwarning(title, message)
            else:
                messagebox.showinfo(title, message)

    class UnifiedMessageDialog:
        @staticmethod
        def show_success(parent, message, title="成功"):
            messagebox.showinfo(title, message)

        @staticmethod
        def show_error(parent, message, title="錯誤"):
            messagebox.showerror(title, message)

        @staticmethod
        def show_warning(parent, message, title="警告"):
            messagebox.showwarning(title, message)

        @staticmethod
        def show_info(parent, message, title="資訊"):
            messagebox.showinfo(title, message)

    class UnifiedConfirmDialog:
        @staticmethod
        def ask_stage_update(parent, stage_name):
            return messagebox.askyesno(
                "確認更新",
                f"階段「{stage_name}」已存在，是否要更新日期和備註？"
            )

from .simple_progress_edit_dialog import SimpleProgressEditDialog
from .upload_file_dialog import UploadFileDialog
from .import_data_dialog import ImportDataDialog
from .case_transfer_dialog import CaseTransferDialog

__all__ = [
    'BaseWindow',
    'MainWindow',
    'CaseFormDialog',
    'ConfirmDialog',
    'MessageDialog',
    'UnifiedMessageDialog',
    'UnifiedConfirmDialog',
    'SimpleProgressEditDialog',
    'UploadFileDialog',
    'ImportDataDialog',
    'CaseTransferDialog',
    'get_case_overview_window',
    'get_date_reminder_widget'
]