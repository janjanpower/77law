import tkinter as tk
from tkinter import ttk
from config.settings import AppConfig

class BaseWindow:
    """基礎視窗類別 - 提供統一的視窗樣式和功能"""

    def __init__(self, title="視窗", width=800, height=600, resizable=True, parent=None):
        """
        初始化基礎視窗

        Args:
            title: 視窗標題
            width: 視窗寬度
            height: 視窗高度
            resizable: 是否可調整大小
            parent: 父視窗
        """
        self.parent = parent
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.title = title
        self.width = width
        self.height = height
        self.resizable = resizable

        self._setup_window()
        self._setup_styles()
        self._create_layout()

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title(self.title)
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])

        # 移除系統標題欄
        self.window.overrideredirect(True)

        if self.resizable:
            self.window.minsize(
                AppConfig.SIZES['min_window']['width'],
                AppConfig.SIZES['min_window']['height']
            )
        else:
            self.window.resizable(False, False)

        # 置中顯示
        self._center_window()

        # 添加視窗拖曳功能
        self._setup_window_drag()

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.width // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.height // 2)
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _setup_window_drag(self):
        """設定視窗拖曳功能"""
        self.drag_data = {"x": 0, "y": 0}

        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        # 等待標題框架建立後再綁定
        self.window.after(100, lambda: self._bind_drag_events(start_drag, on_drag))

    def _bind_drag_events(self, start_drag, on_drag):
        """綁定拖曳事件到標題框架"""
        if hasattr(self, 'title_frame') and hasattr(self, 'title_label'):
            self.title_frame.bind("<Button-1>", start_drag)
            self.title_frame.bind("<B1-Motion>", on_drag)
            self.title_label.bind("<Button-1>", start_drag)
            self.title_label.bind("<B1-Motion>", on_drag)

    def _setup_styles(self):
        """設定 ttk 樣式"""
        self.style = ttk.Style()

        # 按鈕樣式
        self.style.configure(
            'Custom.TButton',
            background=AppConfig.COLORS['button_bg'],
            foreground=AppConfig.COLORS['button_fg'],
            borderwidth=1,
            focuscolor='none'
        )

        self.style.map(
            'Custom.TButton',
            background=[('active', AppConfig.COLORS['button_hover'])]
        )

        # 對話框按鈕樣式
        self.style.configure(
            'Dialog.TButton',
            background=AppConfig.COLORS['button_bg'],
            foreground=AppConfig.COLORS['button_fg'],
            width=10
        )

        # 功能按鈕樣式
        self.style.configure(
            'Function.TButton',
            background=AppConfig.COLORS['button_bg'],
            foreground=AppConfig.COLORS['button_fg'],
            width=15
        )

    def _create_layout(self):
        """建立基礎佈局"""
        # 主容器
        self.main_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['window_bg']
        )
        self.main_frame.pack(fill='both', expand=True)

        # 標題列
        self.title_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        self.title_frame.pack(fill='x')
        self.title_frame.pack_propagate(False)

        # 標題標籤 - 使用統一字體
        self.title_label = tk.Label(
            self.title_frame,
            text=self.title,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']  # 使用統一字體設定
        )
        self.title_label.pack(side='left', padx=10)

        # 關閉按鈕
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
        self.close_btn.pack(side='right', padx=10)

        # 內容區域
        self.content_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.content_frame.pack(fill='both', expand=True)

    def create_button(self, parent, text, command, style='Custom.TButton'):
        """
        建立標準化按鈕

        Args:
            parent: 父容器
            text: 按鈕文字
            command: 點擊事件
            style: 按鈕樣式

        Returns:
            ttk.Button: 建立的按鈕
        """
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style=style
        )

    def create_dialog_buttons(self, parent, ok_command=None, cancel_command=None):
        """
        建立對話框標準按鈕（確定、取消）

        Args:
            parent: 父容器
            ok_command: 確定按鈕事件
            cancel_command: 取消按鈕事件

        Returns:
            tuple: (確定按鈕, 取消按鈕)
        """
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=10)

        # 確定按鈕
        ok_btn = tk.Button(
            button_frame,
            text='確定',
            command=ok_command or self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用統一字體
            width=10
        )
        ok_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=cancel_command or self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用統一字體
            width=10
        )
        cancel_btn.pack(side='left', padx=5)

        return ok_btn, cancel_btn

    def close(self):
        """關閉視窗"""
        self.window.destroy()

    def show(self):
        """顯示視窗"""
        self.window.deiconify()

    def hide(self):
        """隱藏視窗"""
        self.window.withdraw()