import tkinter as tk
from tkinter import ttk, messagebox
from config.settings import AppConfig

class ConfirmDialog:
    """確認對話框 - 修正置頂層級問題"""

    def __init__(self, parent, title="確認", message="確定要執行此操作嗎？"):
        self.result = False
        self.message = message
        self.parent = parent
        self.drag_data = {"x": 0, "y": 0}

        # 建立視窗
        self.window = tk.Toplevel(parent)
        self._setup_window(title)
        self._create_dialog_content()

    def _setup_window(self, title):
        """設定視窗基本屬性 - 確保置頂顯示"""
        self.window.title(f"{AppConfig.WINDOW_TITLES['main']} - {title}")
        self.window.geometry("400x180")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.resizable(False, False)

        # 強制置頂設定
        if self.parent:
            self.window.transient(self.parent)
            # 立即設定置頂和模態，不延遲
            self.window.lift()
            self.window.attributes('-topmost', True)
            self.window.grab_set()
            self.window.focus_force()

        # 置中顯示
        self._center_window()

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 200
        y = (self.window.winfo_screenheight() // 2) - 100
        self.window.geometry(f"400x200+{x}+{y}")

    def _create_dialog_content(self):
        """建立對話框內容 - 確認對話框"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 標題列
        title_frame = tk.Frame(
            main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 標題標籤
        title_label = tk.Label(
            title_frame,
            text="重複階段確認",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        title_label.pack(expand=True)

        # 設定拖曳功能
        self._setup_drag(title_frame, title_label)

        # 內容區域
        content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 訊息標籤
        message_label = tk.Label(
            content_frame,
            text=self.message,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=350,
            justify='left'
        )
        message_label.pack(expand=True)

        # 按鈕區域
        button_frame = tk.Frame(content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=(20, 0))

        # 確定按鈕
        ok_btn = tk.Button(
            button_frame,
            text='確定',
            command=self._on_ok,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        ok_btn.pack(side='left', padx=10)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self._on_cancel,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        cancel_btn.pack(side='left', padx=10)

    def _setup_drag(self, title_frame, title_label):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        # 綁定拖曳事件
        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", on_drag)
        title_label.bind("<Button-1>", start_drag)
        title_label.bind("<B1-Motion>", on_drag)

    def _on_ok(self):
        """確定按鈕事件"""
        self.result = True
        self.window.attributes('-topmost', False)  # 關閉前移除置頂
        self.window.destroy()

    def _on_cancel(self):
        """取消按鈕事件"""
        self.result = False
        self.window.attributes('-topmost', False)  # 關閉前移除置頂
        self.window.destroy()

    @staticmethod
    def ask(parent, title="確認", message="確定要執行此操作嗎？"):
        """靜態方法：顯示確認對話框"""
        dialog = ConfirmDialog(parent, title, message)
        dialog.window.wait_window()
        return dialog.result


class MessageDialog:
    """訊息對話框"""

    def __init__(self, parent, title="訊息", message="", dialog_type="info"):
        self.message = message
        self.dialog_type = dialog_type
        self.parent = parent
        self.drag_data = {"x": 0, "y": 0}

        # 建立視窗
        self.window = tk.Toplevel(parent)
        self._setup_window(title)
        self._create_dialog_content()

    def _setup_window(self, title):
        """設定視窗基本屬性"""
        self.window.title(f"{AppConfig.WINDOW_TITLES['main']} - {title}")
        self.window.geometry("400x180")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.resizable(False, False)

        # 置頂設定
        if self.parent:
            self.window.transient(self.parent)
            # 延遲設定grab_set和置頂，避免與子控件衝突
            self.window.after(100, self._set_modal_dialog)

        # 置中顯示
        self._center_window()

    def _set_modal_dialog(self):
        """設定模態對話框"""
        try:
            if self.window.winfo_exists():
                self.window.grab_set()
                self.window.lift()
                self.window.focus_force()
                # 暫時置頂
                self.window.attributes('-topmost', True)
                self.window.after(200, lambda: self.window.attributes('-topmost', False))
        except:
            pass

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 200
        y = (self.window.winfo_screenheight() // 2) - 90
        self.window.geometry(f"400x180+{x}+{y}")

    def _create_dialog_content(self):
        """建立對話框內容 - 訊息對話框"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 標題列
        title_frame = tk.Frame(
            main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 標題標籤
        title_label = tk.Label(
            title_frame,
            text="系統訊息",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        title_label.pack(expand=True)

        # 設定拖曳功能
        self._setup_drag(title_frame, title_label)

        # 內容區域
        content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 訊息標籤
        message_label = tk.Label(
            content_frame,
            text=self.message,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=350,
            justify='left'
        )
        message_label.pack(expand=True)

        # 確定按鈕
        ok_btn = tk.Button(
            content_frame,
            text='確定',
            command=self._close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        ok_btn.pack(pady=(0, 10))

    def _setup_drag(self, title_frame, title_label):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        # 綁定拖曳事件
        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", on_drag)
        title_label.bind("<Button-1>", start_drag)
        title_label.bind("<B1-Motion>", on_drag)

    def _close(self):
        """關閉對話框"""
        self.window.destroy()

    @staticmethod
    def show(parent, title="訊息", message="", dialog_type="info"):
        """靜態方法：顯示訊息對話框"""
        dialog = MessageDialog(parent, title, message, dialog_type)
        dialog.window.wait_window()

class UnifiedMessageDialog:
    """統一風格的訊息對話框"""

    def __init__(self, parent, title="訊息", message="", dialog_type="info"):
        self.message = message
        self.dialog_type = dialog_type
        self.parent = parent
        self.drag_data = {"x": 0, "y": 0}

        # 建立視窗
        self.window = tk.Toplevel(parent)
        self._setup_window(title)
        self._create_dialog_content()

    def _setup_window(self, title):
        """設定視窗基本屬性"""
        self.window.title(f"{AppConfig.WINDOW_TITLES['main']} - {title}")
        self.window.geometry("400x250")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.resizable(False, False)

        # 置頂設定
        if self.parent:
            self.window.transient(self.parent)
            # 延遲設定grab_set和置頂，避免與子控件衝突
            self.window.after(100, self._set_modal_dialog)

        # 置中顯示
        self._center_window()

    def _set_modal_dialog(self):
        """設定模態對話框"""
        try:
            if self.window.winfo_exists():
                self.window.grab_set()
                self.window.lift()
                self.window.focus_force()
                # 暫時置頂
                self.window.attributes('-topmost', True)
                self.window.after(200, lambda: self.window.attributes('-topmost', False))
        except:
            pass

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 200
        y = (self.window.winfo_screenheight() // 2) - 125
        self.window.geometry(f"400x250+{x}+{y}")

    def _create_dialog_content(self):
        """建立對話框內容 - 統一訊息對話框"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 標題列
        title_frame = tk.Frame(
            main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 根據對話框類型設定標題
        title_text = {
            'success': '成功',
            'error': '錯誤',
            'warning': '警告',
            'info': '訊息'
        }.get(self.dialog_type, '訊息')

        # 標題標籤
        title_label = tk.Label(
            title_frame,
            text=title_text,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        title_label.pack(expand=True)

        # 設定拖曳功能
        self._setup_drag(title_frame, title_label)

        # 內容區域
        content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 圖示區域
        icon_frame = tk.Frame(content_frame, bg=AppConfig.COLORS['window_bg'])
        icon_frame.pack(pady=(0, 10))

        # 根據對話框類型設定圖示
        icon_text = {
            'success': '✓',
            'error': '✗',
            'warning': '⚠',
            'info': 'ℹ'
        }.get(self.dialog_type, 'ℹ')

        icon_color = {
            'success': '#4CAF50',
            'error': '#F44336',
            'warning': '#FF9800',
            'info': '#2196F3'
        }.get(self.dialog_type, '#2196F3')

        icon_label = tk.Label(
            icon_frame,
            text=icon_text,
            bg=AppConfig.COLORS['window_bg'],
            fg=icon_color,
            font=('Arial', 24, 'bold')
        )
        icon_label.pack()

        # 訊息標籤
        message_label = tk.Label(
            content_frame,
            text=self.message,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=350,
            justify='center'
        )
        message_label.pack(expand=True, pady=(0, 20))

        # 確定按鈕
        ok_btn = tk.Button(
            content_frame,
            text='確定',
            command=self._close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        ok_btn.pack(pady=(0, 10))

    def _setup_drag(self, title_frame, title_label):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        # 綁定拖曳事件
        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", on_drag)
        title_label.bind("<Button-1>", start_drag)
        title_label.bind("<B1-Motion>", on_drag)

    def _close(self):
        """關閉對話框"""
        self.window.destroy()

    @staticmethod
    def show(parent, title="訊息", message="", dialog_type="info"):
        """靜態方法：顯示統一訊息對話框"""
        dialog = UnifiedMessageDialog(parent, title, message, dialog_type)
        dialog.window.wait_window()

    @staticmethod
    def show_error(parent, message, title="錯誤"):
        """顯示錯誤對話框 - 修正版"""
        return UnifiedMessageDialog._show_message(parent, message, title, "error")

    @staticmethod
    def show_success(parent, message, title="成功"):
        """顯示成功對話框 - 修正版"""
        return UnifiedMessageDialog._show_message(parent, message, title, "success")

    @staticmethod
    def show_warning(parent, message, title="警告"):
        """顯示警告對話框 - 修正版"""
        return UnifiedMessageDialog._show_message(parent, message, title, "warning")

    @staticmethod
    def show_info(parent, message="訊息"):
        """顯示訊息"""
        UnifiedMessageDialog.show(parent, "訊息", message, "info")

    @staticmethod
    def _show_message(parent, message, title, msg_type):
        """🔥 修正：統一的訊息對話框處理"""
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("350x180")
        dialog.configure(bg=AppConfig.COLORS['window_bg'])
        dialog.resizable(False, False)
        dialog.overrideredirect(True)

        # 🔥 重要：確保置頂和模態
        dialog.attributes('-topmost', True)
        dialog.transient(parent)
        dialog.grab_set()

        # 置中顯示
        if parent:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 175
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 90
            dialog.geometry(f"350x180+{x}+{y}")

        # 標題列
        title_frame = tk.Frame(dialog, bg=AppConfig.COLORS['title_bg'], height=30)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text=title,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        title_label.pack(side='left', padx=10, pady=5)

        # 內容區域
        content_frame = tk.Frame(dialog, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 根據類型設定顏色
        colors = {
            "error": "red",
            "success": "green",
            "warning": "orange"
        }
        text_color = colors.get(msg_type, AppConfig.COLORS['text_color'])

        # 訊息內容
        msg_label = tk.Label(
            content_frame,
            text=message,
            bg=AppConfig.COLORS['window_bg'],
            fg=text_color,
            font=AppConfig.FONTS['text'],
            wraplength=300,
            justify='center'
        )
        msg_label.pack(expand=True)

        # 確定按鈕
        def close_dialog():
            dialog.grab_release()
            dialog.destroy()
            # 🔥 重要：恢復父視窗的置頂狀態
            if parent:
                parent.attributes('-topmost', True)
                parent.focus_force()

        ok_btn = tk.Button(
            content_frame,
            text='確定',
            command=close_dialog,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        ok_btn.pack(pady=(10, 0))

        # 綁定按鍵
        dialog.bind('<Return>', lambda e: close_dialog())
        dialog.bind('<Escape>', lambda e: close_dialog())

        # 設定焦點
        dialog.focus_force()
        ok_btn.focus_set()

        return dialog