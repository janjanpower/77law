"""視圖模組"""
from .base_window import BaseWindow
from .main_window import MainWindow
from .case_overview import CaseOverviewWindow
from .case_form import CaseFormDialog
from .dialogs import ConfirmDialog, MessageDialog
from .progress_history_dialog import ProgressHistoryDialog  # 🔥 新增

__all__ = [
    'BaseWindow',
    'MainWindow',
    'CaseOverviewWindow',
    'CaseFormDialog',
    'ConfirmDialog',
    'MessageDialog',
    'ProgressHistoryDialog'  # 🔥 新增
]