# views/case_transfer_dialog.py
"""
更新的結案轉移對話框 - 統一使用增強版BaseWindow
移除重複的置頂處理代碼
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
from typing import Optional, Callable
from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import EnhancedBaseWindow
from views.dialogs import UnifiedMessageDialog

class CaseTransferDialog(EnhancedBaseWindow):
    """結案轉移對話框 - 使用增強版BaseWindow"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 case_controller=None, on_transfer_complete: Optional[Callable] = None):
        """
        初始化結案轉移對話框

        Args:
            parent: 父視窗
            case_data: 選中的案件資料
            case_controller: 案件控制器
            on_transfer_complete: 轉移完成回調函數
        """
        self.case_data = case_data
        self.case_controller = case_controller
        self.on_transfer_complete = on_transfer_complete
        self.transfer_folder = None
        self.transfer_settings = self._load_transfer_settings()

        # 🔥 簡化：使用增強版BaseWindow，自動處理置頂
        super().__init__(
            title="結案轉移",
            width=500,
            height=450,
            resizable=False,
            parent=parent,
            auto_topmost=True  # 自動維持置頂
        )

    def _load_transfer_settings(self):
        """載入轉移設定"""
        try:
            import json
            settings_file = os.path.join(os.path.dirname(__file__), "transfer_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"載入轉移設定失敗: {e}")

        return {'default_transfer_folder': None}

    def _save_transfer_settings(self):
        """儲存轉移設定"""
        try:
            import json
            settings_file = os.path.join(os.path.dirname(__file__), "transfer_settings.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.transfer_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存轉移設定失敗: {e}")

    def _create_layout(self):
        """覆寫：建立對話框佈局"""
        super()._create_layout()
        self._create_transfer_content()

    def _create_transfer_content(self):
        """建立轉移對話框內容"""
        if not self.case_data:
            tk.Label(
                self.content_frame,
                text="錯誤：未選擇案件",
                bg=AppConfig.COLORS['window_bg'],
                fg='red',
                font=AppConfig.FONTS['text']
            ).pack(pady=20)
            return

        # 案件資訊
        info_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        info_frame.pack(fill='x', pady=(0, 20))

        case_display_name = AppConfig.format_case_display_name(self.case_data)
        tk.Label(
            info_frame,
            text=f"準備結案轉移案件：{case_display_name}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button'],
            wraplength=450
        ).pack(anchor='w')

        # 警告訊息
        warning_frame = tk.Frame(self.content_frame, bg='#FFE6E6', relief='solid', borderwidth=1)
        warning_frame.pack(fill='x', pady=(0, 20), padx=5)

        warning_text = """⚠️ 重要提醒：

• 結案轉移將會把案件資料夾移動到指定的歸檔位置
• 案件記錄將從系統中移除，但資料夾會保留
• 此操作無法復原，請確認案件確實已結案
• 建議先備份重要資料"""

        tk.Label(
            warning_frame,
            text=warning_text,
            bg='#FFE6E6',
            fg='#D32F2F',
            font=AppConfig.FONTS['text'],
            justify='left',
            wraplength=450
        ).pack(padx=10, pady=10)

        # 轉移目標選擇
        target_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        target_frame.pack(fill='x', pady=(0, 20))

        tk.Label(
            target_frame,
            text="選擇歸檔資料夾：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(0, 10))

        folder_select_frame = tk.Frame(target_frame, bg=AppConfig.COLORS['window_bg'])
        folder_select_frame.pack(fill='x')

        # 預設資料夾路徑
        default_folder = self.transfer_settings.get('default_transfer_folder', '請選擇歸檔資料夾...')
        self.folder_path_var = tk.StringVar(value=default_folder)

        self.folder_path_label = tk.Label(
            folder_select_frame,
            textvariable=self.folder_path_var,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text'],
            relief='sunken',
            borderwidth=1,
            anchor='w'
        )
        self.folder_path_label.pack(side='left', fill='x', expand=True, padx=(0, 10))

        browse_btn = tk.Button(
            folder_select_frame,
            text='瀏覽',
            command=self._select_transfer_folder,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        browse_btn.pack(side='right')

        # 選項設定
        options_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        options_frame.pack(fill='x', pady=(0, 20))

        # 保留原始結構選項
        self.keep_structure_var = tk.BooleanVar(value=True)
        keep_structure_cb = tk.Checkbox(
            options_frame,
            text="保留原始資料夾結構",
            variable=self.keep_structure_var,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        )
        keep_structure_cb.pack(anchor='w', pady=2)

        # 自動設為預設資料夾選項
        self.set_as_default_var = tk.BooleanVar(value=False)
        set_default_cb = tk.Checkbox(
            options_frame,
            text="將此資料夾設為預設歸檔位置",
            variable=self.set_as_default_var,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        )
        set_default_cb.pack(anchor='w', pady=2)

        # 按鈕區域
        button_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=(30, 0))

        # 確認轉移按鈕
        transfer_btn = tk.Button(
            button_frame,
            text='確認結案轉移',
            command=self._confirm_transfer,
            bg='#FF5722',
            fg='white',
            font=AppConfig.FONTS['button'],
            width=15,
            height=2
        )
        transfer_btn.pack(side='left', padx=10)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=2
        )
        cancel_btn.pack(side='left', padx=10)

    def _select_transfer_folder(self):
        """選擇轉移目標資料夾"""
        folder_path = filedialog.askdirectory(
            title="選擇案件歸檔資料夾",
            initialdir=self.transfer_settings.get('default_transfer_folder', os.path.expanduser('~')),
            parent=self.window
        )

        if folder_path:
            self.transfer_folder = folder_path
            self.folder_path_var.set(f"歸檔位置：{folder_path}")

            # 🔥 使用統一的置頂確保
            self.ensure_topmost()

    def _confirm_transfer(self):
        """確認轉移"""
        if not self.transfer_folder:
            UnifiedMessageDialog.show_error(self.window, "請先選擇歸檔資料夾")
            return

        if not os.path.exists(self.transfer_folder):
            UnifiedMessageDialog.show_error(self.window, "選擇的歸檔資料夾不存在")
            return

        # 最終確認
        from views.dialogs import ConfirmDialog

        confirm_msg = (
            f"確定要將案件「{AppConfig.format_case_display_name(self.case_data)}」結案轉移嗎？\n\n"
            f"案件資料夾將移動到：\n{self.transfer_folder}\n\n"
            f"此操作無法復原，請確認案件確實已結案！"
        )

        if not ConfirmDialog.ask(self.window, "確認結案轉移", confirm_msg):
            return

        try:
            # 執行轉移
            success = self.case_controller.transfer_case_to_archive(
                self.case_data.case_id,
                self.transfer_folder,
                keep_structure=self.keep_structure_var.get()
            )

            if success:
                # 更新預設設定
                if self.set_as_default_var.get():
                    self.transfer_settings['default_transfer_folder'] = self.transfer_folder
                    self._save_transfer_settings()

                UnifiedMessageDialog.show_success(
                    self.window,
                    f"案件「{AppConfig.format_case_display_name(self.case_data)}」已成功結案轉移"
                )

                # 呼叫完成回調
                if self.on_transfer_complete:
                    self.on_transfer_complete()

                self.close()
            else:
                UnifiedMessageDialog.show_error(self.window, "結案轉移失敗，請檢查目標資料夾權限")

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"結案轉移過程發生錯誤：{str(e)}")


# 🔥 新增：統一的對話框工廠函數
def create_import_dialog(parent, case_controller, on_complete=None):
    """創建匯入對話框"""
    return ImportDataDialog(parent, case_controller, on_complete)

def create_upload_dialog(parent, case_data, folder_manager, on_complete=None):
    """創建上傳對話框"""
    return UploadFileDialog(parent, case_data, folder_manager, on_complete)

def create_transfer_dialog(parent, case_data, case_controller, on_complete=None):
    """創建轉移對話框"""
    return CaseTransferDialog(parent, case_data, case_controller, on_complete)