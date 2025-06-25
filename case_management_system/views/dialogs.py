import tkinter as tk
from tkinter import ttk, messagebox
from config.settings import AppConfig

class ConfirmDialog:
    """確認對話框"""

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
            text="確認",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']  # 使用統一字體
        )
        title_label.pack(side='left', padx=10)

        # 關閉按鈕
        close_btn = tk.Button(
            title_frame,
            text="✕",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 12, 'bold'),
            bd=0,
            width=3,
            command=self._on_cancel
        )
        close_btn.pack(side='right', padx=10)

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
            font=AppConfig.FONTS['text'],  # 使用統一文字字體
            wraplength=350,
            justify='center'
        )
        message_label.pack(expand=True)

        # 按鈕區域
        button_frame = tk.Frame(content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=10)

        # 確定按鈕
        ok_btn = tk.Button(
            button_frame,
            text='確定',
            command=self._on_ok,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用按鈕字體大小
            width=8,
            height=1
        )
        ok_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self._on_cancel,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用按鈕字體大小
            width=8,
            height=1
        )
        cancel_btn.pack(side='left', padx=5)

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
        self.window.destroy()

    def _on_cancel(self):
        """取消按鈕事件"""
        self.result = False
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
        """建立對話框內容"""
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
            text="訊息",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']  # 使用統一字體
        )
        title_label.pack(side='left', padx=10)

        # 關閉按鈕
        close_btn = tk.Button(
            title_frame,
            text="✕",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 12, 'bold'),
            bd=0,
            width=3,
            command=self._close
        )
        close_btn.pack(side='right', padx=10)

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
            font=AppConfig.FONTS['text'],  # 使用統一字體
            wraplength=350,
            justify='center'
        )
        message_label.pack(expand=True)

        # 確定按鈕
        ok_btn = tk.Button(
            content_frame,
            text='確定',
            command=self._close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用統一字體
            width=10
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
        """建立對話框內容"""
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

        # 根據類型設定標題和顏色
        title_text, icon = self._get_dialog_style()

        # 圖示標籤
        icon_label = tk.Label(
            title_frame,
            text=icon,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 14, 'bold')
        )
        icon_label.pack(side='left', padx=(10, 5))

        # 標題標籤
        title_label = tk.Label(
            title_frame,
            text=title_text,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        title_label.pack(side='left', padx=5)

        # 關閉按鈕
        close_btn = tk.Button(
            title_frame,
            text="✕",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 12, 'bold'),
            bd=0,
            width=3,
            command=self._close
        )
        close_btn.pack(side='right', padx=10)

        # 設定拖曳功能
        self._setup_drag(title_frame, title_label, icon_label)

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
            justify='center'
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
            width=10
        )
        ok_btn.pack(pady=(0, 10))

    def _get_dialog_style(self):
        """根據對話框類型取得樣式"""
        styles = {
            'info': ('資訊', 'ℹ'),
            'success': ('成功', '✓'),
            'warning': ('警告', '⚠'),
            'error': ('錯誤', '✕'),
        }
        return styles.get(self.dialog_type, ('訊息', 'ℹ'))

    def _setup_drag(self, title_frame, title_label, icon_label):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        # 綁定拖曳事件
        for widget in [title_frame, title_label, icon_label]:
            widget.bind("<Button-1>", start_drag)
            widget.bind("<B1-Motion>", on_drag)

    def _close(self):
        """關閉對話框"""
        self.window.destroy()

    @staticmethod
    def show_info(parent, message, title="資訊"):
        """顯示資訊對話框"""
        dialog = UnifiedMessageDialog(parent, title, message, "info")
        dialog.window.wait_window()

    @staticmethod
    def show_success(parent, message, title="成功"):
        """顯示成功對話框"""
        dialog = UnifiedMessageDialog(parent, title, message, "success")
        dialog.window.wait_window()

    @staticmethod
    def show_warning(parent, message, title="警告"):
        """顯示警告對話框"""
        dialog = UnifiedMessageDialog(parent, title, message, "warning")
        dialog.window.wait_window()

    @staticmethod
    def show_error(parent, message, title="錯誤"):
        """顯示錯誤對話框"""
        dialog = UnifiedMessageDialog(parent, title, message, "error")
        dialog.window.wait_window()