"""視圖模組"""
from .base_window import BaseWindow
from .main_window import MainWindow
from .case_form import CaseFormDialog
from .dialogs import ConfirmDialog, MessageDialog, UnifiedMessageDialog
from .simple_progress_edit_dialog import SimpleProgressEditDialog
from .upload_file_dialog import UploadFileDialog
from .import_data_dialog import ImportDataDialog
from .case_transfer_dialog import CaseTransferDialog  # 🔥 新增

# 🔥 修正：將可能產生循環導入的模組移到後面，並使用延遲導入
def get_case_overview_window():
    """延遲導入 CaseOverviewWindow"""
    from .case_overview import CaseOverviewWindow
    return CaseOverviewWindow

def get_date_reminder_widget():
    """延遲導入 DateReminderWidget"""
    from .date_reminder_widget import DateReminderWidget
    return DateReminderWidget

__all__ = [
    'BaseWindow',
    'MainWindow',
    'CaseFormDialog',
    'ConfirmDialog',
    'MessageDialog',
    'UnifiedMessageDialog',
    'SimpleProgressEditDialog',
    'UploadFileDialog',
    'ImportDataDialog',
    'CaseTransferDialog',  # 🔥 新增
    'get_case_overview_window',
    'get_date_reminder_widget'
]