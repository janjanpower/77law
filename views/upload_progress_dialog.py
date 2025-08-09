# -*- coding: utf-8 -*-
"""
views/upload_progress_dialog.py
上傳進度對話框 - 顯示案件資料上傳到資料庫的進度
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable, List
from datetime import datetime

try:
    from views.base_window import BaseWindow
    from config.settings import AppConfig
    from views.dialogs import UnifiedMessageDialog
except ImportError as e:
    print(f"⚠️ 導入模組失敗: {e}")
    # 提供備用實現
    class BaseWindow:
        def __init__(self, title="視窗", width=400, height=300, resizable=True, parent=None):
            self.window = tk.Toplevel(parent) if parent else tk.Tk()
            self.window.title(title)
            self.window.geometry(f"{width}x{height}")
            self.parent = parent

        def close(self):
            if self.window:
                self.window.destroy()

    class AppConfig:
        COLORS = {
            'window_bg': '#f0f0f0',
            'button_bg': '#4a90e2',
            'button_fg': 'white',
            'text_color': '#333333',
            'success_color': '#27ae60',
            'error_color': '#e74c3c'
        }
        FONTS = {
            'default': ('Microsoft JhengHei UI', 10),
            'title': ('Microsoft JhengHei UI', 12, 'bold')
        }

    class UnifiedMessageDialog:
        @staticmethod
        def show_success(parent, message):
            tk.messagebox.showinfo("成功", message, parent=parent)
        @staticmethod
        def show_error(parent, message):
            tk.messagebox.showerror("錯誤", message, parent=parent)
        @staticmethod
        def show_warning(parent, message):
            tk.messagebox.showwarning("警告", message, parent=parent)


class UploadProgressDialog(BaseWindow):
    """上傳進度對話框"""

    def __init__(self, parent, total_cases: int, on_cancel: Callable = None):
        """
        初始化上傳進度對話框

        Args:
            parent: 父視窗
            total_cases: 總案件數
            on_cancel: 取消回調函數
        """
        super().__init__(
            title="上傳案件資料到資料庫",
            width=1500,
            height=500,
            resizable=False,
            parent=parent
        )

        self.total_cases = total_cases
        self.on_cancel = on_cancel
        self.is_completed = False
        self.upload_cancelled = False

        # UI 元件
        self.progress_var = tk.IntVar()
        self.status_var = tk.StringVar()
        self.detail_var = tk.StringVar()
        self.progress_bar = None
        self.status_label = None
        self.detail_label = None
        self.stats_frame = None
        self.cancel_btn = None
        self.close_btn = None
        self.log_text = None

        # 統計數據
        self.uploaded_count = 0
        self.failed_count = 0
        self.start_time = datetime.now()

        self._create_ui()
        self._center_window()

        # 設定關閉事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _create_ui(self):
        """建立UI界面"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=15)

        # 標題
        title_label = tk.Label(
            main_frame,
            text="正在上傳案件資料到雲端資料庫",
            font=AppConfig.FONTS['title'],
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color']
        )
        title_label.pack(pady=(0, 15))

        # 進度條區域
        progress_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        progress_frame.pack(fill='x', pady=(0, 10))

        # 進度條
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=300
        )
        self.progress_bar.pack(pady=(0, 5))

        # 狀態文字
        self.status_label = tk.Label(
            progress_frame,
            textvariable=self.status_var,
            font=AppConfig.FONTS['default'],
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color']
        )
        self.status_label.pack()

        # 詳細資訊
        self.detail_label = tk.Label(
            progress_frame,
            textvariable=self.detail_var,
            font=('Microsoft JhengHei UI', 9),
            bg=AppConfig.COLORS['window_bg'],
            fg='#666666'
        )
        self.detail_label.pack(pady=(5, 0))

        # 統計區域
        self._create_stats_area(main_frame)

        # 日誌區域
        self._create_log_area(main_frame)

        # 按鈕區域
        self._create_buttons(main_frame)

        # 初始化狀態
        self.update_progress(0, f"準備上傳 {self.total_cases} 筆案件資料...")

    def _create_stats_area(self, parent):
        """建立統計資訊區域"""
        self.stats_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        self.stats_frame.pack(fill='x', pady=(10, 10))

        # 統計資訊標籤
        stats_info = [
            ("總計:", str(self.total_cases), AppConfig.COLORS['text_color']),
            ("成功:", "0", AppConfig.COLORS['success_color']),
            ("失敗:", "0", AppConfig.COLORS['error_color']),
            ("進度:", "0%", AppConfig.COLORS['text_color'])
        ]

        self.stats_labels = {}
        for i, (label, value, color) in enumerate(stats_info):
            # 標籤
            tk.Label(
                self.stats_frame,
                text=label,
                font=AppConfig.FONTS['default'],
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color']
            ).grid(row=0, column=i*2, sticky='e', padx=(0, 5))

            # 值
            value_label = tk.Label(
                self.stats_frame,
                text=value,
                font=('Microsoft JhengHei UI', 10, 'bold'),
                bg=AppConfig.COLORS['window_bg'],
                fg=color
            )
            value_label.grid(row=0, column=i*2+1, sticky='w', padx=(0, 20))

            # 儲存標籤以便更新
            key = label.replace(':', '').lower()
            self.stats_labels[key] = value_label

        # 設定列權重
        for i in range(8):
            self.stats_frame.columnconfigure(i, weight=1)

    def _create_log_area(self, parent):
        """建立日誌區域"""
        log_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        log_frame.pack(fill='both', expand=True, pady=(5, 10))

        # 日誌標題
        log_title = tk.Label(
            log_frame,
            text="上傳日誌:",
            font=AppConfig.FONTS['default'],
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color']
        )
        log_title.pack(anchor='w')

        # 日誌文本區域和滾動條
        log_container = tk.Frame(log_frame)
        log_container.pack(fill='both', expand=True, pady=(5, 0))

        self.log_text = tk.Text(
            log_container,
            height=6,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='white',
            fg='black',
            state='disabled'
        )

        scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _create_buttons(self, parent):
        """建立按鈕區域"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(fill='x', pady=(10, 0))

        # 取消按鈕
        self.cancel_btn = tk.Button(
            button_frame,
            text="取消上傳",
            command=self._on_cancel,
            font=AppConfig.FONTS['default'],
            bg='#e74c3c',
            fg='white',
            width=12
        )
        self.cancel_btn.pack(side='left')

        # 關閉按鈕（初始隱藏）
        self.close_btn = tk.Button(
            button_frame,
            text="關閉",
            command=self._on_close,
            font=AppConfig.FONTS['default'],
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            width=12
        )
        # 初始不顯示

    def _center_window(self):
        """將視窗置中"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def update_progress(self, progress: int, status: str, detail: str = ""):
        """
        更新進度

        Args:
            progress: 進度百分比 (0-100)
            status: 狀態訊息
            detail: 詳細資訊
        """
        try:
            self.progress_var.set(progress)
            self.status_var.set(status)
            if detail:
                self.detail_var.set(detail)

            # 更新統計
            if hasattr(self, 'stats_labels'):
                self.stats_labels['進度'].config(text=f"{progress}%")

            # 自動滾動到底部
            if self.log_text:
                self.log_text.see('end')

            # 強制更新界面
            self.window.update()

        except Exception as e:
            print(f"更新進度失敗: {e}")

    def update_stats(self, uploaded: int, failed: int):
        """
        更新統計數據

        Args:
            uploaded: 已上傳數量
            failed: 失敗數量
        """
        try:
            self.uploaded_count = uploaded
            self.failed_count = failed

            if hasattr(self, 'stats_labels'):
                self.stats_labels['成功'].config(text=str(uploaded))
                self.stats_labels['失敗'].config(text=str(failed))

        except Exception as e:
            print(f"更新統計失敗: {e}")

    def add_log(self, message: str, log_type: str = "info"):
        """
        添加日誌訊息

        Args:
            message: 日誌訊息
            log_type: 日誌類型 ("info", "success", "error", "warning")
        """
        try:
            if not self.log_text:
                return

            self.log_text.config(state='normal')

            # 時間戳
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 根據類型設定顏色
            colors = {
                "info": "black",
                "success": "green",
                "error": "red",
                "warning": "orange"
            }
            color = colors.get(log_type, "black")

            # 添加訊息
            full_message = f"[{timestamp}] {message}\n"
            self.log_text.insert('end', full_message)

            # 設定顏色（如果支援）
            try:
                start_index = self.log_text.index('end-2c linestart')
                end_index = self.log_text.index('end-1c')
                self.log_text.tag_add(log_type, start_index, end_index)
                self.log_text.tag_config(log_type, foreground=color)
            except:
                pass  # 如果顏色設定失敗，忽略

            self.log_text.config(state='disabled')
            self.log_text.see('end')

        except Exception as e:
            print(f"添加日誌失敗: {e}")

    def on_upload_complete(self, success: bool, summary: Dict[str, Any]):
        """
        上傳完成處理

        Args:
            success: 是否成功
            summary: 結果摘要
        """
        try:
            self.is_completed = True

            # 更新進度和狀態
            self.update_progress(100, summary.get('message', '上傳完成'))

            # 更新統計
            uploaded = summary.get('uploaded_count', 0)
            failed = summary.get('failed_count', 0)
            self.update_stats(uploaded, failed)

            # 計算用時
            elapsed = datetime.now() - self.start_time
            elapsed_str = str(elapsed).split('.')[0]  # 移除微秒

            # 添加完成日誌
            if success:
                self.add_log(f"✅ 上傳完成！用時: {elapsed_str}", "success")
                self.add_log(f"📊 統計: 成功 {uploaded} 筆，失敗 {failed} 筆", "info")
            else:
                self.add_log(f"❌ 上傳完成但有錯誤！用時: {elapsed_str}", "error")
                self.add_log(f"📊 統計: 成功 {uploaded} 筆，失敗 {failed} 筆", "info")

                # 顯示錯誤
                errors = summary.get('errors', [])
                for error in errors[:5]:  # 只顯示前5個錯誤
                    self.add_log(f"  • {error}", "error")

            # 切換按鈕
            self.cancel_btn.pack_forget()
            self.close_btn.pack(side='left')

            # 顯示完成對話框
            if success:
                UnifiedMessageDialog.show_success(
                    self.window,
                    f"案件資料上傳完成！\n\n成功: {uploaded} 筆\n失敗: {failed} 筆\n用時: {elapsed_str}"
                )
            else:
                UnifiedMessageDialog.show_error(
                    self.window,
                    f"案件資料上傳完成但有錯誤！\n\n成功: {uploaded} 筆\n失敗: {failed} 筆\n用時: {elapsed_str}\n\n請查看日誌了解詳細錯誤。"
                )

        except Exception as e:
            print(f"處理上傳完成事件失敗: {e}")
            self.add_log(f"❌ 處理完成事件失敗: {e}", "error")

    def _on_cancel(self):
        """取消按鈕事件"""
        if not self.is_completed and not self.upload_cancelled:
            self.upload_cancelled = True
            self.add_log("⚠️ 用戶請求取消上傳...", "warning")

            if self.on_cancel:
                self.on_cancel()

            self.cancel_btn.config(text="取消中...", state='disabled')

    def _on_close(self):
        """關閉按鈕事件"""
        self.close()

    def _on_window_close(self):
        """視窗關閉事件"""
        if not self.is_completed:
            # 如果上傳未完成，先詢問用戶
            import tkinter.messagebox as msgbox
            if msgbox.askyesno("確認關閉", "上傳仍在進行中，確定要關閉視窗嗎？", parent=self.window):
                self._on_cancel()
                self.close()
        else:
            self.close()

    @staticmethod
    def show_upload_dialog(parent, total_cases: int, on_cancel: Callable = None):
        """
        顯示上傳進度對話框

        Args:
            parent: 父視窗
            total_cases: 總案件數
            on_cancel: 取消回調函數

        Returns:
            UploadProgressDialog: 對話框實例
        """
        dialog = UploadProgressDialog(parent, total_cases, on_cancel)
        dialog.window.grab_set()  # 設為模態
        return dialog