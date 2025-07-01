# views/case_form.py

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow
from views.dialogs import UnifiedMessageDialog

class CaseFormDialog(BaseWindow):
    """案件表單對話框 - 最簡化版本"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 on_save: Optional[Callable] = None, mode='add'):
        """初始化案件表單對話框"""
        self.case_data = case_data
        self.on_save = on_save
        self.mode = mode
        self.result_data = None
        self.form_vars = {}

        # 初始化表單變數
        self._init_form_data()

        # 設定標題
        title = AppConfig.WINDOW_TITLES['add_case'] if mode == 'add' else AppConfig.WINDOW_TITLES['edit_case']

        # 直接調用父類初始化，不做任何額外操作
        super().__init__(title=title, width=400, height=650, resizable=False, parent=parent)

    def _init_form_data(self):
        """初始化表單資料"""
        # 基本欄位
        self.form_vars['case_type'] = tk.StringVar(value=self.case_data.case_type if self.case_data else '')
        self.form_vars['client'] = tk.StringVar(value=self.case_data.client if self.case_data else '')
        self.form_vars['lawyer'] = tk.StringVar(value=self.case_data.lawyer if self.case_data else '')
        self.form_vars['legal_affairs'] = tk.StringVar(value=self.case_data.legal_affairs if self.case_data else '')

        # 詳細資訊欄位
        self.form_vars['case_reason'] = tk.StringVar(value=getattr(self.case_data, 'case_reason', '') if self.case_data else '')
        self.form_vars['case_number'] = tk.StringVar(value=getattr(self.case_data, 'case_number', '') if self.case_data else '')
        self.form_vars['opposing_party'] = tk.StringVar(value=getattr(self.case_data, 'opposing_party', '') if self.case_data else '')
        self.form_vars['court'] = tk.StringVar(value=getattr(self.case_data, 'court', '') if self.case_data else '')
        self.form_vars['division'] = tk.StringVar(value=getattr(self.case_data, 'division', '') if self.case_data else '')

    def _create_layout(self):
        """建立表單佈局"""
        super()._create_layout()
        self._create_form_content()

    def _create_form_content(self):
        """建立表單內容"""
        # 主要內容框架
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)

        # 基本資訊區塊
        self._create_basic_info_section(main_frame)

        # 詳細資訊區塊
        self._create_detail_info_section(main_frame)

        # 按鈕區域
        self._create_form_buttons(main_frame)

    def _create_basic_info_section(self, parent):
        """建立基本資訊區塊"""
        # 標題
        tk.Label(
            parent,
            text="基本資訊",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        ).pack(anchor='w', pady=(0, 10))

        # 表單框架
        form_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        form_frame.pack(fill='x', pady=(0, 20))

        # 案件類型
        self._create_field(form_frame, "案件類型", 'case_type', 0, field_type='combobox',
                          values=AppConfig.CASE_TYPES, required=True)

        # 當事人
        self._create_field(form_frame, "當事人", 'client', 1, required=True)

        # 委任律師
        self._create_field(form_frame, "委任律師", 'lawyer', 2)

        # 法務
        self._create_field(form_frame, "法務", 'legal_affairs', 3)

    def _create_detail_info_section(self, parent):
        """建立詳細資訊區塊"""
        # 標題
        tk.Label(
            parent,
            text="詳細資訊",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        ).pack(anchor='w', pady=(0, 10))

        # 表單框架
        form_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        form_frame.pack(fill='x', pady=(0, 20))

        # 案由
        self._create_field(form_frame, "案由", 'case_reason', 0)
        # 案號
        self._create_field(form_frame, "案號", 'case_number', 1)
        # 對造
        self._create_field(form_frame, "對造", 'opposing_party', 2)
        # 負責法院
        self._create_field(form_frame, "負責法院", 'court', 3)
        # 負責股別
        self._create_field(form_frame, "負責股別", 'division', 4)

    def _create_field(self, parent, label_text, var_name, row, field_type='entry',
                     values=None, required=False):
        """建立表單欄位"""
        # 標籤
        tk.Label(
            parent,
            text=f"{label_text}{'*' if required else ''}:",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            width=12,
            anchor='w'
        ).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=8)

        # 輸入控件
        if field_type == 'combobox':
            widget = ttk.Combobox(
                parent,
                textvariable=self.form_vars[var_name],
                values=values or [],
                state='readonly',
                width=15,
                font=AppConfig.FONTS['text']
            )

            # 設定預設值
            if values and len(values) > 0:
                current_value = self.form_vars[var_name].get()
                if current_value not in values and required:
                    self.form_vars[var_name].set(values[0])

        else:
            widget = tk.Entry(
                parent,
                textvariable=self.form_vars[var_name],
                font=AppConfig.FONTS['text'],
                width=15
            )

        widget.grid(row=row, column=1, sticky='w', pady=8)

    def _create_form_buttons(self, parent):
        """建立表單按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=20)

        # 儲存按鈕
        tk.Button(
            button_frame,
            text='儲存',
            command=self._on_save,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10
        ).pack(side='left', padx=5)

        # 取消按鈕
        tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10
        ).pack(side='left', padx=5)

    def _validate_form(self) -> bool:
        """驗證表單資料"""
        # 檢查必填欄位
        if not self.form_vars['case_type'].get().strip():
            UnifiedMessageDialog.show_warning(self.window, "請選擇案件類型！")
            return False

        if not self.form_vars['client'].get().strip():
            UnifiedMessageDialog.show_warning(self.window, "請輸入當事人姓名！")
            return False

        # 檢查案件類型是否有效
        case_type = self.form_vars['case_type'].get().strip()
        if case_type not in AppConfig.CASE_TYPES:
            UnifiedMessageDialog.show_warning(self.window, f"無效的案件類型：{case_type}")
            return False

        return True

    def _on_save(self):
        """儲存案件資料"""
        try:
            if not self._validate_form():
                return

            # 建立案件資料物件
            case_data = CaseData(
                case_id=self.case_data.case_id if self.case_data else '',
                case_type=self.form_vars['case_type'].get().strip(),
                client=self.form_vars['client'].get().strip(),
                lawyer=self.form_vars['lawyer'].get().strip() or None,
                legal_affairs=self.form_vars['legal_affairs'].get().strip() or None,
                progress='待處理',
                case_reason=self.form_vars['case_reason'].get().strip() or None,
                case_number=self.form_vars['case_number'].get().strip() or None,
                opposing_party=self.form_vars['opposing_party'].get().strip() or None,
                court=self.form_vars['court'].get().strip() or None,
                division=self.form_vars['division'].get().strip() or None,
                progress_date=None
            )

            # 處理編輯模式的舊資料
            if self.mode == 'edit' and self.case_data:
                case_data.progress = self.case_data.progress
                case_data.progress_date = self.case_data.progress_date
                case_data.progress_stages = getattr(self.case_data, 'progress_stages', {}).copy()
                case_data.created_date = self.case_data.created_date

            self.result_data = case_data

            # 呼叫儲存回調
            if self.on_save:
                try:
                    success = self.on_save(case_data, self.mode)
                    if success:
                        self.close()
                except Exception as e:
                    UnifiedMessageDialog.show_error(self.window, f"儲存失敗：{str(e)}")
            else:
                self.close()

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"處理失敗：{str(e)}")

    @staticmethod
    def show_add_dialog(parent, on_save: Callable) -> Optional[CaseData]:
        """顯示新增案件對話框"""
        dialog = CaseFormDialog(parent, mode='add', on_save=on_save)
        dialog.window.wait_window()
        return dialog.result_data

    @staticmethod
    def show_edit_dialog(parent, case_data: CaseData, on_save: Callable) -> Optional[CaseData]:
        """顯示編輯案件對話框"""
        dialog = CaseFormDialog(parent, case_data=case_data, mode='edit', on_save=on_save)
        dialog.window.wait_window()
        return dialog.result_data