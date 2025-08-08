# views/case_form.py - 修正版本
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow

# 🔥 統一安全導入
try:
    from views.dialogs import UnifiedMessageDialog
    DIALOGS_AVAILABLE = True
except ImportError as e:
    print(f"警告：無法導入對話框模組 - {e}")
    import tkinter.messagebox as messagebox
    DIALOGS_AVAILABLE = False

    class UnifiedMessageDialog:
        @staticmethod
        def show_success(parent, message, title="成功"):
            if parent and hasattr(parent, 'winfo_exists'):
                messagebox.showinfo(title, message, parent=parent)
            else:
                messagebox.showinfo(title, message)

        @staticmethod
        def show_error(parent, message, title="錯誤"):
            if parent and hasattr(parent, 'winfo_exists'):
                messagebox.showerror(title, message, parent=parent)
            else:
                messagebox.showerror(title, message)


class CaseFormDialog(BaseWindow):
    """案件表單對話框 - 修正版本"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 on_save: Optional[Callable] = None, mode='add'):
        self.case_data = case_data
        self.on_save = on_save
        self.mode = mode
        self.result_data = None
        self.parent_window = parent  # 🔥 保存父視窗引用

        # 先初始化表單變數
        self.form_vars = {}
        self._init_form_data()

        title = AppConfig.WINDOW_TITLES['add_case'] if mode == 'add' else AppConfig.WINDOW_TITLES['edit_case']
        super().__init__(title=title, width=400, height=700, resizable=False, parent=parent)

        if parent:
            self.window.lift()
            self.window.attributes('-topmost', True)
            self.window.focus_force()
            self.window.after(100, self._ensure_topmost)

    def _ensure_topmost(self):
        """確保視窗保持置頂"""
        try:
            if self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
        except tk.TclError:
            pass

    def _init_form_data(self):
        """初始化表單資料"""
        # 基本欄位
        self.form_vars['case_type'] = tk.StringVar(value=self.case_data.case_type if self.case_data else '')
        self.form_vars['client'] = tk.StringVar(value=self.case_data.client if self.case_data else '')
        self.form_vars['lawyer'] = tk.StringVar(value=self.case_data.lawyer if self.case_data else '')
        self.form_vars['legal_affairs'] = tk.StringVar(value=self.case_data.legal_affairs if self.case_data else '')

        # 詳細資訊欄位
        self.form_vars['case_reason'] = tk.StringVar(value=getattr(self.case_data, 'case_reason', '') or '' if self.case_data else '')
        self.form_vars['case_number'] = tk.StringVar(value=getattr(self.case_data, 'case_number', '') or '' if self.case_data else '')
        self.form_vars['opposing_party'] = tk.StringVar(value=getattr(self.case_data, 'opposing_party', '') or '' if self.case_data else '')
        self.form_vars['court'] = tk.StringVar(value=getattr(self.case_data, 'court', '') or '' if self.case_data else '')
        self.form_vars['division'] = tk.StringVar(value=getattr(self.case_data, 'division', '') or '' if self.case_data else '')

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._create_form_content()

    def _create_form_content(self):
        """建立表單內容"""
        # 主滾動區域
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 基本資訊區塊
        self._create_basic_info_section(main_frame)

        # 詳細資訊區塊
        self._create_detail_info_section(main_frame)

        # 按鈕區域
        self._create_buttons(main_frame)

    def _create_basic_info_section(self, parent):
        """建立基本資訊區塊"""
        basic_title = tk.Label(
            parent,
            text="基本資訊",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        )
        basic_title.pack(anchor='w', pady=(0, 10))

        basic_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        basic_frame.pack(fill='x', pady=(0, 20))

        # 案件類型
        self._create_field(basic_frame, "案件類型", 'case_type', 0,
                          field_type='combobox',
                          values=list(AppConfig.CASE_TYPE_FOLDERS.keys()),
                          required=True)

        # 當事人
        self._create_field(basic_frame, "當事人", 'client', 1, required=True)

        # 委任律師
        self._create_field(basic_frame, "委任律師", 'lawyer', 2)

        # 法務
        self._create_field(basic_frame, "法務", 'legal_affairs', 3)

    def _create_detail_info_section(self, parent):
        """建立詳細資訊區塊"""
        detail_title = tk.Label(
            parent,
            text="詳細資訊",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        )
        detail_title.pack(anchor='w', pady=(0, 10))

        detail_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        detail_frame.pack(fill='x', pady=(0, 20))

        # 案由
        self._create_field(detail_frame, "案由", 'case_reason', 0)

        # 案號
        self._create_field(detail_frame, "案號", 'case_number', 1)

        # 對造
        self._create_field(detail_frame, "對造", 'opposing_party', 2)

        # 負責法院
        self._create_field(detail_frame, "負責法院", 'court', 3)

        # 負責股別
        self._create_field(detail_frame, "負責股別", 'division', 4)

    def _create_field(self, parent, label_text, var_name, row, field_type='entry',
                     values=None, required=False):
        """建立表單欄位"""
        # 標籤
        label = tk.Label(
            parent,
            text=f"{label_text}{'*' if required else ''}:",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            width=12,
            anchor='w'
        )
        label.grid(row=row, column=0, sticky='w', padx=(0, 10), pady=8)

        # 輸入控件
        if field_type == 'combobox':
            widget = ttk.Combobox(
                parent,
                textvariable=self.form_vars[var_name],
                values=values or [],
                state='readonly' if values else 'normal',
                width=15,
                font=AppConfig.FONTS['text']
            )
        else:
            widget = tk.Entry(
                parent,
                textvariable=self.form_vars[var_name],
                width=18,
                font=AppConfig.FONTS['text'],
                bg='white',
                relief='solid',
                borderwidth=1
            )

        widget.grid(row=row, column=1, sticky='ew', padx=5, pady=8)
        parent.grid_columnconfigure(1, weight=1)

    def _create_buttons(self, parent):
        """建立按鈕區域"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(fill='x', pady=(20, 0))

        # 儲存按鈕
        save_btn = tk.Button(
            button_frame,
            text='儲存',
            command=self._on_save,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=2
        )
        save_btn.pack(side='left', padx=(0, 10))

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg='#757575',
            fg='white',
            font=AppConfig.FONTS['button'],
            width=10,
            height=2
        )
        cancel_btn.pack(side='left')

    def _validate_form(self) -> tuple[bool, str]:
        """驗證表單資料"""
        # 檢查必填欄位
        case_type = self.form_vars['case_type'].get().strip()
        if not case_type:
            return False, "請選擇案件類型"

        client = self.form_vars['client'].get().strip()
        if not client:
            return False, "請輸入當事人姓名"

        # 檢查案件類型是否有效
        if case_type not in AppConfig.CASE_TYPE_FOLDERS:
            return False, f"無效的案件類型：{case_type}"

        return True, ""

    def _on_save(self):
        """🔥 修正版：儲存按鈕處理"""
        try:
            # 驗證表單
            is_valid, error_message = self._validate_form()
            if not is_valid:
                UnifiedMessageDialog.show_error(self.window, error_message)
                return

            # 🔥 關鍵修正：根據模式決定 case_id
            if self.mode == 'edit' and self.case_data:
                # 編輯模式：使用現有的 case_id
                case_id = self.case_data.case_id
            else:
                # 新增模式：這裡先設定為 None，讓 controller 自動生成
                case_id = None

            # 建立案件資料對象
            case_data = CaseData(
                case_id=case_id,
                case_type=self.form_vars['case_type'].get().strip(),
                client=self.form_vars['client'].get().strip(),
                lawyer=self.form_vars['lawyer'].get().strip() or None,
                legal_affairs=self.form_vars['legal_affairs'].get().strip() or None,
                case_reason=self.form_vars['case_reason'].get().strip() or None,
                case_number=self.form_vars['case_number'].get().strip() or None,
                opposing_party=self.form_vars['opposing_party'].get().strip() or None,
                court=self.form_vars['court'].get().strip() or None,
                division=self.form_vars['division'].get().strip() or None,
                progress_date=None
            )

            # 處理編輯模式的特殊邏輯
            if self.mode == 'edit' and self.case_data:
                case_data.progress = self.case_data.progress
                case_data.progress_date = self.case_data.progress_date
                case_data.progress_stages = self.case_data.progress_stages.copy()
                case_data.created_date = self.case_data.created_date

            self.result_data = case_data

            # 🔥 修正：執行儲存回調，只傳入兩個參數
            if self.on_save:
                try:
                    success = self.on_save(case_data, self.mode)
                    if success:
                        print(f"案件儲存成功，關閉對話框")
                        self.close()
                    else:
                        print(f"案件儲存失敗，保持對話框開啟")
                        UnifiedMessageDialog.show_error(self.window, "儲存失敗，請檢查資料或聯繫系統管理員")

                except Exception as callback_error:
                    print(f"儲存回調函數發生錯誤: {callback_error}")
                    UnifiedMessageDialog.show_error(self.window, f"儲存過程發生錯誤：{str(callback_error)}")
            else:
                self.close()

        except Exception as e:
            print(f"建立案件資料時發生錯誤: {e}")
            error_details = f"資料處理失敗：{str(e)}"
            if "tk" in str(e):
                error_details = "視窗對話框錯誤，請重新嘗試"
            UnifiedMessageDialog.show_error(self.window, error_details)

    @staticmethod
    def show_add_dialog(parent, on_save: Callable) -> Optional[CaseData]:
        """顯示新增案件對話框"""
        try:
            dialog = CaseFormDialog(parent, mode='add', on_save=on_save)
            dialog.window.wait_window()
            return dialog.result_data
        except Exception as e:
            print(f"顯示新增對話框失敗: {e}")
            return None

    @staticmethod
    def show_edit_dialog(parent, case_data: CaseData, on_save: Callable) -> Optional[CaseData]:
        """顯示編輯案件對話框"""
        try:
            dialog = CaseFormDialog(parent, case_data=case_data, mode='edit', on_save=on_save)
            dialog.window.wait_window()
            return dialog.result_data
        except Exception as e:
            print(f"顯示編輯對話框失敗: {e}")
            return None