import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict
from datetime import datetime

try:
    from tkcalendar import DateEntry
except ImportError:
    print("警告：tkcalendar 套件未安裝，請執行：pip install tkcalendar")
    # 提供替代的日期輸入方式
    DateEntry = None

# 🔥 修正導入路徑
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow

class ProgressHistoryDialog(BaseWindow):
    """進度歷史管理對話框"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 on_update: Optional[Callable] = None):
        """
        初始化進度歷史對話框

        Args:
            parent: 父視窗
            case_data: 案件資料
            on_update: 更新回調函數
        """
        self.case_data = case_data
        self.on_update = on_update
        self.progress_history = case_data.progress_history.copy() if case_data else {}

        title = f"進度歷史管理 - {case_data.client if case_data else '未知案件'}"
        super().__init__(title=title, width=700, height=500, resizable=True, parent=parent)

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()

        # 建立對話框內容
        self._create_dialog_content()

    def _create_dialog_content(self):
        """建立對話框內容"""
        # 案件資訊區域
        self._create_case_info_section()

        # 進度歷史列表
        self._create_history_list_section()

        # 新增進度區域
        self._create_add_progress_section()

        # 按鈕區域
        self._create_dialog_buttons()

    def _create_case_info_section(self):
        """建立案件資訊區域"""
        info_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        info_frame.pack(fill='x', padx=20, pady=(20, 10))

        # 案件基本資訊
        if self.case_data:
            info_text = f"案件編號：{self.case_data.case_id} | 當事人：{self.case_data.client} | 案件類型：{self.case_data.case_type}"
            tk.Label(
                info_frame,
                text=info_text,
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['button']
            ).pack(anchor='w')

            current_progress = f"目前進度：{self.case_data.progress}"
            if self.case_data.progress_date:
                current_progress += f" ({self.case_data.progress_date})"

            tk.Label(
                info_frame,
                text=current_progress,
                bg=AppConfig.COLORS['window_bg'],
                fg='#4CAF50',
                font=AppConfig.FONTS['text']
            ).pack(anchor='w', pady=(5, 0))

    def _create_history_list_section(self):
        """建立進度歷史列表區域"""
        # 標題
        title_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        title_frame.pack(fill='x', padx=20, pady=(10, 5))

        tk.Label(
            title_frame,
            text="進度歷史記錄",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        ).pack(side='left')

        # 刪除按鈕
        self.delete_btn = tk.Button(
            title_frame,
            text='刪除選中',
            command=self._delete_selected_history,
            bg='#F44336',
            fg='white',
            font=AppConfig.FONTS['text'],
            width=10
        )
        self.delete_btn.pack(side='right')

        # 列表區域
        list_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=5)

        # 建立Treeview
        columns = ('progress', 'date')
        self.history_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            height=8
        )

        # 設定欄位
        self.history_tree.heading('progress', text='進度階段')
        self.history_tree.heading('date', text='日期')
        self.history_tree.column('progress', width=200, anchor='center')
        self.history_tree.column('date', width=150, anchor='center')

        # 滾動軸
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        # 佈局
        self.history_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 載入歷史資料
        self._refresh_history_list()

    def _create_add_progress_section(self):
        """建立新增進度區域"""
        add_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        add_frame.pack(fill='x', padx=20, pady=10)

        # 標題
        tk.Label(
            add_frame,
            text="新增進度記錄",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['title']
        ).pack(anchor='w', pady=(0, 10))

        # 輸入區域
        input_frame = tk.Frame(add_frame, bg=AppConfig.COLORS['window_bg'])
        input_frame.pack(fill='x')

        # 進度選擇
        tk.Label(
            input_frame,
            text="進度：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)

        case_type = self.case_data.case_type if self.case_data else ''
        progress_options = AppConfig.get_progress_options(case_type)

        self.progress_var = tk.StringVar()
        self.progress_combo = ttk.Combobox(
            input_frame,
            textvariable=self.progress_var,
            values=progress_options,
            state='readonly',
            width=20
        )
        self.progress_combo.grid(row=0, column=1, sticky='w', pady=5)

        # 日期選擇
        tk.Label(
            input_frame,
            text="日期：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=0, column=2, sticky='w', padx=(20, 10), pady=5)

        if DateEntry is not None:
            self.date_entry = DateEntry(
                input_frame,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                locale='zh_TW'
            )
        else:
            # 回退方案：使用普通輸入框
            self.date_entry = tk.Entry(
                input_frame,
                width=15,
                bg='white',
                fg='black',
                font=AppConfig.FONTS['text']
            )
            # 設定預設值為今天
            self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        self.date_entry.grid(row=0, column=3, sticky='w', pady=5)

        # 新增按鈕
        add_btn = tk.Button(
            input_frame,
            text='新增',
            command=self._add_progress_record,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['text'],
            width=8
        )
        add_btn.grid(row=0, column=4, sticky='w', padx=(20, 0), pady=5)

    def _create_dialog_buttons(self):
        """建立對話框按鈕"""
        button_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=20)

        # 儲存按鈕
        save_btn = tk.Button(
            button_frame,
            text='儲存',
            command=self._save_changes,
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

    def _refresh_history_list(self):
        """重新整理歷史列表"""
        # 清空現有項目
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # 按日期排序顯示
        if self.progress_history:
            sorted_history = sorted(
                self.progress_history.items(),
                key=lambda x: x[1],  # 按日期排序
                reverse=True  # 最新的在前
            )

            for progress, date in sorted_history:
                self.history_tree.insert('', 'end', values=(progress, date))

    def _add_progress_record(self):
        """新增進度記錄"""
        progress = self.progress_var.get()

        # 取得日期（支援回退方案）
        if DateEntry is not None and hasattr(self.date_entry, 'get_date'):
            date = self.date_entry.get_date().strftime('%Y-%m-%d')
        else:
            date_str = self.date_entry.get().strip()
            try:
                # 驗證日期格式
                datetime.strptime(date_str, '%Y-%m-%d')
                date = date_str
            except ValueError:
                messagebox.showerror("錯誤", "日期格式錯誤，請使用 YYYY-MM-DD 格式")
                return

        if not progress:
            messagebox.showwarning("提醒", "請選擇進度階段")
            return

        # 檢查是否已存在
        if progress in self.progress_history:
            if not messagebox.askyesno("確認", f"進度「{progress}」已存在，是否要更新日期？"):
                return

        # 新增或更新記錄
        self.progress_history[progress] = date
        self._refresh_history_list()

        # 清空輸入
        self.progress_var.set('')
        if DateEntry is not None and hasattr(self.date_entry, 'set_date'):
            self.date_entry.set_date(datetime.now().date())
        else:
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        messagebox.showinfo("成功", f"已新增進度記錄：{progress} ({date})")

    def _delete_selected_history(self):
        """刪除選中的歷史記錄"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("提醒", "請選擇要刪除的記錄")
            return

        item = selection[0]
        values = self.history_tree.item(item, 'values')
        progress = values[0]

        if messagebox.askyesno("確認", f"確定要刪除進度記錄「{progress}」嗎？"):
            if progress in self.progress_history:
                del self.progress_history[progress]
                self._refresh_history_list()
                messagebox.showinfo("成功", f"已刪除進度記錄：{progress}")

    def _save_changes(self):
        """儲存變更"""
        if self.case_data and self.on_update:
            # 更新案件資料
            self.case_data.progress_history = self.progress_history.copy()
            self.case_data.updated_date = datetime.now()

            # 呼叫更新回調
            try:
                success = self.on_update(self.case_data)
                if success:
                    messagebox.showinfo("成功", "進度歷史已更新")
                    self.close()
                else:
                    messagebox.showerror("錯誤", "更新失敗")
            except Exception as e:
                messagebox.showerror("錯誤", f"更新時發生錯誤：{str(e)}")
        else:
            self.close()

    @staticmethod
    def show_dialog(parent, case_data: CaseData, on_update: Callable):
        """顯示進度歷史管理對話框"""
        dialog = ProgressHistoryDialog(parent, case_data, on_update)
        dialog.window.wait_window()