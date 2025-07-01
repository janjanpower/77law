# views/simple_progress_edit_dialog.py
"""
簡單進度編輯對話框 - 整合置頂日期控件解決方案
移除重複代碼，統一日期控件處理
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from datetime import datetime

from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow
from utils.topmost_date_entry import TopmostDateEntryManager

class SimpleProgressEditDialog(BaseWindow):
    """簡單進度編輯對話框"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 stage_name: str = None, stage_date: str = None,
                 on_save: Optional[Callable] = None, mode='edit'):
        """
        初始化進度編輯對話框

        Args:
            parent: 父視窗
            case_data: 案件資料
            stage_name: 要編輯的階段名稱
            stage_date: 要編輯的階段日期
            on_save: 儲存回調函數
            mode: 模式 ('edit' 或 'add')
        """
        self.case_data = case_data
        self.stage_name = stage_name
        self.stage_date = stage_date
        self.on_save = on_save
        self.mode = mode
        self.result = None
        self.date_entry = None  # 統一的日期控件引用

        title_text = "新增進度階段" if mode == 'add' else f"編輯進度階段 - {stage_name}"

        # 完全覆寫父類的視窗設定，避免閃爍
        self.parent = parent
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.title = title_text
        self.width = 400
        self.height = 500
        self.resizable = False

        # 立即隱藏視窗，在所有設定完成前不顯示
        self.window.withdraw()

        # 設定基本屬性
        self.window.title(title_text)
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.resizable(False, False)
        self.window.overrideredirect(True)

        # 設定大小和位置
        self._center_window()

        # 建立佈局
        self._setup_styles()
        self._create_layout()

        if parent:
            # 所有設定完成後才顯示並設定模態
            self.window.after(10, self._show_and_setup_modal)

    def _center_window(self):
        """視窗置中"""
        x = (self.window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.window.winfo_screenheight() // 2) - (500 // 2)
        self.window.geometry(f"400x500+{x}+{y}")

    def _setup_styles(self):
        """設定樣式"""
        self.style = ttk.Style()
        self.style.configure(
            'Custom.TButton',
            background=AppConfig.COLORS['button_bg'],
            foreground=AppConfig.COLORS['button_fg']
        )

    def _show_and_setup_modal(self):
        """顯示視窗並設定模態狀態"""
        try:
            self.window.deiconify()
            self.window.transient(self.parent)
            self.window.grab_set()
            self.window.attributes('-topmost', True)
            self.window.lift()
            self.window.focus_force()

            # 🔥 新增：確保所有日曆控件置頂
            TopmostDateEntryManager.ensure_all_calendars_topmost(self.window)

        except tk.TclError:
            pass

    def _create_layout(self):
        """建立對話框佈局"""
        # 標題列
        self.title_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['title_bg'],
            height=40
        )
        self.title_frame.pack(fill='x')
        self.title_frame.pack_propagate(False)

        self.title_label = tk.Label(
            self.title_frame,
            text=self.title,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        self.title_label.pack(side='left', padx=10, pady=10)

        self.close_btn = tk.Button(
            self.title_frame,
            text="✕",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 12, 'bold'),
            bd=0,
            width=3,
            command=self.close
        )
        self.close_btn.pack(side='right', padx=5, pady=5)

        # 內容區域
        self.content_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        self.content_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self._create_edit_content()

    def _create_edit_content(self):
        """建立編輯內容"""
        # 表單容器
        form_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        form_frame.pack(fill='both', expand=True, pady=10)

        # 案件資訊（如果有）
        if self.case_data:
            info_frame = tk.Frame(form_frame, bg=AppConfig.COLORS['window_bg'])
            info_frame.pack(fill='x', pady=(0, 10))

            case_display_name = AppConfig.format_case_display_name(self.case_data)
            case_type = self.case_data.case_type

            info_text = f"案件：{case_display_name} ({case_type})"
            tk.Label(
                info_frame,
                text=info_text,
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['text']
            ).pack(anchor='w')

        # 編輯區域
        edit_frame = tk.Frame(form_frame, bg=AppConfig.COLORS['window_bg'])
        edit_frame.pack(fill='x', pady=10)

        # 階段名稱
        tk.Label(
            edit_frame,
            text="進度階段：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=0, column=0, sticky='w', padx=(0, 10), pady=10)

        if self.mode == 'add':
            # 新增模式：可選擇階段
            case_type = self.case_data.case_type if self.case_data else ''
            progress_options = AppConfig.get_progress_options(case_type)

            self.stage_var = tk.StringVar(value=self.stage_name or '')
            self.stage_combo = ttk.Combobox(
                edit_frame,
                textvariable=self.stage_var,
                values=progress_options,
                state='normal',
                width=25,
                font=AppConfig.FONTS['text']
            )
            self.stage_combo.grid(row=0, column=1, sticky='w', pady=10)
        else:
            # 編輯模式：顯示階段名稱
            self.stage_var = tk.StringVar(value=self.stage_name or '')
            stage_label = tk.Label(
                edit_frame,
                textvariable=self.stage_var,
                bg=AppConfig.COLORS['window_bg'],
                fg='#4CAF50',
                font=AppConfig.FONTS['button']
            )
            stage_label.grid(row=0, column=1, sticky='w', pady=10)

        # 🔥 修改：使用統一的置頂日期控件
        tk.Label(
            edit_frame,
            text="執行日期：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=1, column=0, sticky='w', padx=(0, 10), pady=10)

        # 使用統一的置頂日期控件管理器
        self.date_entry = TopmostDateEntryManager.create_date_entry(
            edit_frame,
            parent_window=self.window,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            font=AppConfig.FONTS['text']
        )

        # 設定初始日期
        if self.stage_date:
            try:
                date_obj = datetime.strptime(self.stage_date, '%Y-%m-%d')
                self.date_entry.set_date(date_obj.date())
            except:
                pass

        self.date_entry.grid(row=1, column=1, sticky='w', pady=10)

        # 時間輸入
        tk.Label(
            edit_frame,
            text="執行時間：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=2, column=0, sticky='w', padx=(0, 10), pady=10)

        self.time_entry = tk.Entry(
            edit_frame,
            width=15,
            font=AppConfig.FONTS['text']
        )
        self.time_entry.grid(row=2, column=1, sticky='w', pady=10)

        # 提示標籤
        time_hint = tk.Label(
            edit_frame,
            text="(格式: HH:MM，如 14:30)",
            bg=AppConfig.COLORS['window_bg'],
            fg='#666666',
            font=('Arial', 8)
        )
        time_hint.grid(row=2, column=2, sticky='w', padx=(5, 0), pady=10)

        # 備註輸入
        tk.Label(
            edit_frame,
            text="備註：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=3, column=0, sticky='nw', padx=(0, 10), pady=10)

        self.note_text = tk.Text(
            edit_frame,
            width=25,
            height=4,
            font=AppConfig.FONTS['text'],
            wrap='word'
        )
        self.note_text.grid(row=3, column=1, sticky='w', pady=10)

        # 按鈕區域
        button_frame = tk.Frame(form_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=20)

        save_btn = tk.Button(
            button_frame,
            text='儲存',
            command=self._on_save,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        save_btn.pack(side='left', padx=10)

        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        cancel_btn.pack(side='left', padx=10)

    def _show_duplicate_stage_confirmation(self, stage_name: str) -> bool:
        """顯示重複階段確認對話框 - 🔥 優化置頂處理"""
        from views.dialogs import ConfirmDialog

        # 暫時釋放當前對話框的grab和置頂
        try:
            self.window.grab_release()
            self.window.attributes('-topmost', False)
        except:
            pass

        # 建立確認對話框
        confirm_result = ConfirmDialog.ask(
            self.window,
            "重複階段確認",
            f"階段「{stage_name}」已存在，是否要更新日期和備註？"
        )

        # 🔥 改進：恢復對話框控制權和置頂狀態
        self.window.after(100, self._restore_dialog_control)

        return confirm_result

    def _restore_dialog_control(self):
        """🔥 改進：恢復對話框控制權，確保日曆也置頂"""
        try:
            if self.window.winfo_exists():
                self.window.lift()
                self.window.grab_set()
                self.window.attributes('-topmost', True)
                self.window.focus_force()

                # 確保所有日曆控件也置頂
                TopmostDateEntryManager.ensure_all_calendars_topmost(self.window)
        except:
            pass

    def _on_save(self):
        """儲存進度階段"""
        try:
            stage_name = self.stage_var.get().strip()
            if not stage_name:
                messagebox.showerror("錯誤", "請輸入階段名稱")
                return

            # 🔥 改進：統一的日期獲取方式
            stage_date = ""
            if self.date_entry:
                try:
                    # 優先使用get_date方法
                    if hasattr(self.date_entry, 'get_date') and self.date_entry.get_date():
                        stage_date = self.date_entry.get_date().strftime('%Y-%m-%d')
                    else:
                        # 降級使用get方法
                        stage_date = self.date_entry.get()
                except:
                    stage_date = self.date_entry.get() if self.date_entry else ""

            if not stage_date:
                messagebox.showerror("錯誤", "請選擇執行日期")
                return

            # 驗證日期格式
            if stage_date:
                try:
                    datetime.strptime(stage_date, '%Y-%m-%d')
                except ValueError:
                    messagebox.showerror("錯誤", "日期格式不正確，請使用 YYYY-MM-DD 格式")
                    return

            # 取得時間和備註
            stage_time = self.time_entry.get().strip()
            stage_note = self.note_text.get(1.0, tk.END).strip()

            # 準備結果
            self.result = {
                'stage_name': stage_name,
                'stage_date': stage_date,
                'stage_time': stage_time,
                'stage_note': stage_note
            }

            # 呼叫回調函數
            if self.on_save:
                success = self.on_save(self.result)
                if success:
                    self.close()
                # 如果保存失敗，不關閉對話框，讓用戶修正
            else:
                self.close()

        except Exception as e:
            messagebox.showerror("錯誤", f"儲存失敗：{str(e)}")

    def close(self):
        """關閉對話框"""
        try:
            # 清理日期控件
            if self.date_entry:
                self.date_entry.destroy()

            if self.window:
                self.window.grab_release()
                self.window.destroy()
        except:
            pass

    @staticmethod
    def show_edit_dialog(parent, case_data, stage_name, stage_date, on_save_callback):
        """靜態方法：顯示編輯對話框"""
        dialog = SimpleProgressEditDialog(
            parent=parent,
            case_data=case_data,
            stage_name=stage_name,
            stage_date=stage_date,
            on_save=on_save_callback,
            mode='edit'
        )
        return dialog

    @staticmethod
    def show_add_dialog(parent, case_data, on_save_callback):
        """靜態方法：顯示新增對話框"""
        dialog = SimpleProgressEditDialog(
            parent=parent,
            case_data=case_data,
            on_save=on_save_callback,
            mode='add'
        )
        return dialog