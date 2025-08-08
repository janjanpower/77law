# utils/import_manager.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib
from .date_reminder import DateReminderManager
"""統一導入管理器"""

import sys
from typing import Optional, Any


class SafeImportManager:
    """安全導入管理器"""

    _cache = {}

    @classmethod
    def safe_import(cls, module_name: str, fallback_class: Any = None) -> Any:
        """安全導入模組，失敗時返回備用類別"""
        if module_name in cls._cache:
            return cls._cache[module_name]

        try:
            module = importlib.import_module(module_name)
            cls._cache[module_name] = module
            return module
        except ImportError as e:
            print(f"警告：無法導入 {module_name} - {e}")
            if fallback_class:
                cls._cache[module_name] = fallback_class
                return fallback_class
            return None

    @classmethod
    def get_dialog_classes(cls):
        """取得對話框類別（統一處理）"""
        dialogs_module = cls.safe_import('views.dialogs')

        if dialogs_module:
            return {
                'UnifiedMessageDialog': getattr(dialogs_module, 'UnifiedMessageDialog', None),
                'UnifiedConfirmDialog': getattr(dialogs_module, 'UnifiedConfirmDialog', None)
            }
        else:
            # 返回備用實作
            import tkinter.messagebox as messagebox

            class FallbackMessageDialog:
                @staticmethod
                def show_success(parent, message, title="成功"):
                    messagebox.showinfo(title, message)

                @staticmethod
                def show_error(parent, message, title="錯誤"):
                    messagebox.showerror(title, message)

            class FallbackConfirmDialog:
                def __init__(self, parent, title="確認", message="", confirm_text="確定", cancel_text="取消"):
                    self.result = messagebox.askyesno(title, message)
                    self.window = None

            return {
                'UnifiedMessageDialog': FallbackMessageDialog,
                'UnifiedConfirmDialog': FallbackConfirmDialog
            }