import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow

class CaseFormDialog(BaseWindow):
    """案件表單對話框 - 用於新增和編輯案件"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 on_save: Optional[Callable] = None, mode='add'):
        """
        初始化案件表單對話框

        Args:
            parent: 父視窗
            case_data: 案件資料（編輯模式時提供）
            on_save: 儲存回調函數
            mode: 模式 ('add' 或 'edit')
        """
        self.case_data = case_data
        self.on_save = on_save
        self.mode = mode
        self.result_data = None

        # 🔥 關鍵修正：先初始化表單變數，再調用父類別初始化
        self.form_vars = {}
        self._init_form_data()

        title = AppConfig.WINDOW_TITLES['add_case'] if mode == 'add' else AppConfig.WINDOW_TITLES['edit_case']
        super().__init__(title=title, width=600, height=700, resizable=False, parent=parent)

    def _init_form_data(self):
        """初始化表單資料"""
        # 基本欄位
        self.form_vars['case_type'] = tk.StringVar(value=self.case_data.case_type if self.case_data else '')
        self.form_vars['client'] = tk.StringVar(value=self.case_data.client if self.case_data else '')
        self.form_vars['lawyer'] = tk.StringVar(value=self.case_data.lawyer if self.case_data else '')
        self.form_vars['legal_affairs'] = tk.StringVar(value=self.case_data.legal_affairs if self.case_data else '')
        self.form_vars['progress'] = tk.StringVar(value=self.case_data.progress if self.case_data else '待處理')

        # 詳細資訊欄位
        self.form_vars['case_reason'] = tk.StringVar(value=getattr(self.case_data, 'case_reason', '') if self.case_data else '')
        self.form_vars['case_number'] = tk.StringVar(value=getattr(self.case_data, 'case_number', '') if self.case_data else '')
        self.form_vars['opposing_party'] = tk.StringVar(value=getattr(self.case_data, 'opposing_party', '') if self.case_data else '')
        self.form_vars['court'] = tk.StringVar(value=getattr(self.case_data, 'court', '') if self.case_data else '')
        self.form_vars['division'] = tk.StringVar(value=getattr(self.case_data, 'division', '') if self.case_data else '')

    def _create_layout(self):
        """建立表單佈局"""
        super()._create_layout()

        # 建立表單內容
        self._create_form_content()

    def _create_form_content(self):
        """建立表單內容"""
        # 滾動區域
        canvas = tk.Canvas(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=AppConfig.COLORS['window_bg'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 表單內容
        form_frame = tk.Frame(scrollable_frame, bg=AppConfig.COLORS['window_bg'])
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 基本資訊區塊
        self._create_basic_info_section(form_frame)

        # 詳細資訊區塊
        self._create_detail_info_section(form_frame)

        # 按鈕區域
        self._create_form_buttons(form_frame)

    def _create_basic_info_section(self, parent):
        """建立基本資訊區塊"""
        # 基本資訊標題
        basic_title = tk.Label(
            parent,
            text="基本資訊",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        )
        basic_title.pack(anchor='w', pady=(0, 10))

        # 基本資訊表單
        basic_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        basic_frame.pack(fill='x', pady=(0, 20))

        # 案件類型
        self._create_field(basic_frame, "案件類型", 'case_type', 0, field_type='combobox',
                          values=AppConfig.CASE_TYPES, required=True)

        # 當事人
        self._create_field(basic_frame, "當事人", 'client', 1, required=True)

        # 委任律師
        self._create_field(basic_frame, "委任律師", 'lawyer', 2)

        # 法務
        self._create_field(basic_frame, "法務", 'legal_affairs', 3)

        # 進度追蹤
        self._create_field(basic_frame, "進度追蹤", 'progress', 4, field_type='combobox',
                          values=AppConfig.PROGRESS_OPTIONS)

    def _create_detail_info_section(self, parent):
        """建立詳細資訊區塊"""
        # 詳細資訊標題
        detail_title = tk.Label(
            parent,
            text="詳細資訊",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        )
        detail_title.pack(anchor='w', pady=(0, 10))

        # 詳細資訊表單
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
        label.grid(row=row, column=0, sticky='w', padx=(0, 10), pady=5)

        # 輸入控件
        if field_type == 'combobox':
            widget = ttk.Combobox(
                parent,
                textvariable=self.form_vars[var_name],
                values=values or [],
                state='readonly' if values else 'normal',
                width=30
            )
        else:
            widget = tk.Entry(
                parent,
                textvariable=self.form_vars[var_name],
                bg='white',
                fg='black',
                font=AppConfig.FONTS['text'],
                width=32
            )

        widget.grid(row=row, column=1, sticky='ew', pady=5)

        # 設定欄位權重
        parent.grid_columnconfigure(1, weight=1)

    def _create_form_buttons(self, parent):
        """建立表單按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=20)

        # 確定按鈕
        save_btn = tk.Button(
            button_frame,
            text='儲存',
            command=self._on_save,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10
        )
        save_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10
        )
        cancel_btn.pack(side='left', padx=5)

    def _validate_form(self) -> bool:
        """驗證表單資料"""
        # 檢查必填欄位
        if not self.form_vars['case_type'].get().strip():
            messagebox.showerror("錯誤", "請選擇案件類型")
            return False

        if not self.form_vars['client'].get().strip():
            messagebox.showerror("錯誤", "請輸入當事人")
            return False

        return True

    def _on_save(self):
        """儲存按鈕事件"""
        if not self._validate_form():
            return

        try:
            # 建立案件資料
            case_data = CaseData(
                case_id=self.case_data.case_id if self.case_data else '',
                case_type=self.form_vars['case_type'].get().strip(),
                client=self.form_vars['client'].get().strip(),
                lawyer=self.form_vars['lawyer'].get().strip() or None,
                legal_affairs=self.form_vars['legal_affairs'].get().strip() or None,
                progress=self.form_vars['progress'].get(),
                case_reason=self.form_vars['case_reason'].get().strip() or None,
                case_number=self.form_vars['case_number'].get().strip() or None,
                opposing_party=self.form_vars['opposing_party'].get().strip() or None,
                court=self.form_vars['court'].get().strip() or None,
                division=self.form_vars['division'].get().strip() or None
            )

            # 保留原有的建立時間（編輯模式）
            if self.case_data:
                case_data.created_date = self.case_data.created_date

            self.result_data = case_data

            # 🔥 修正：呼叫儲存回調並檢查結果
            if self.on_save:
                try:
                    success = self.on_save(case_data, self.mode)
                    if success:
                        print(f"案件儲存成功，關閉對話框")
                        self.close()
                    else:
                        print(f"案件儲存失敗，保持對話框開啟")
                        # 不關閉對話框，讓使用者可以重試
                except Exception as callback_error:
                    print(f"儲存回調函數發生錯誤: {callback_error}")
                    messagebox.showerror("錯誤", f"儲存過程發生錯誤：{str(callback_error)}")
            else:
                # 沒有回調函數時直接關閉
                self.close()

        except Exception as e:
            print(f"建立案件資料時發生錯誤: {e}")
            messagebox.showerror("錯誤", f"資料處理失敗：{str(e)}")
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