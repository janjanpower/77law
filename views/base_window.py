# views/base_window.py

import tkinter as tk
from tkinter import ttk
from config.settings import AppConfig

class BaseWindow:
    """基礎視窗類別 - 提供統一的視窗樣式和功能"""

    def __init__(self, title="視窗", width=800, height=600, resizable=True, parent=None):
        """
        初始化基礎視窗
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

        # 🔥 關鍵修正：根據視窗類型決定是否使用模態
        if parent:
            self.window.transient(parent)
            # 🔥 不立即設定模態，等視窗完全顯示後再設定
            self.window.after(200, self._delayed_modal_setup)

    def _delayed_modal_setup(self):
        """🔥 延遲設定模態，避免閃爍"""
        try:
            if self.window.winfo_exists():
                # 🔥 關鍵：先確保視窗完全顯示
                self.window.update_idletasks()
                # 🔥 再設定模態
                self.window.grab_set()
                # 🔥 最後才設定焦點，避免重複重繪
                self.window.focus_set()  # 使用focus_set代替focus_force
        except:
            pass

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title(self.title)
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.resizable(self.resizable, self.resizable)

        # 🔥 關鍵修正：只有對話框才隱藏標題列
        if self.parent:
            # 🔥 檢查父視窗類型，決定是否隱藏標題列
            parent_class_name = self.parent.__class__.__name__
            if parent_class_name == 'CaseOverviewWindow':
                # 🔥 如果父視窗是CaseOverviewWindow，保留標題列避免衝突
                self.window.overrideredirect(False)
            else:
                # 🔥 其他情況才隱藏標題列
                self.window.overrideredirect(True)
        else:
            # 主視窗保留系統標題列
            self.window.overrideredirect(False)

        self._center_window()
        self._setup_window_drag()

    def _center_window(self):
        """視窗置中"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.width // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.height // 2)
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _setup_window_drag(self):
        """設定視窗拖曳功能"""
        # 🔥 只有無邊框視窗才需要拖曳功能
        if self.window.overrideredirect():
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
            width=AppConfig.SIZES['function_button']['width'],
            relief='raised'
        )

        # ComboBox樣式
        self.style.configure(
            'Custom.TCombobox',
            fieldbackground='white',
            background=AppConfig.COLORS['button_bg'],
            foreground='black',
            arrowcolor=AppConfig.COLORS['button_bg']
        )

    def _create_layout(self):
        """建立基本佈局"""
        # 🔥 根據是否有標題列決定是否建立自訂標題
        if self.window.overrideredirect():
            # 無邊框視窗：建立自訂標題列
            self._create_title_bar()

        # 內容區域
        self.content_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['window_bg']
        )
        self.content_frame.pack(fill='both', expand=True)

    def _create_title_bar(self):
        """建立標題列（只在無邊框視窗時使用）"""
        self.title_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        self.title_frame.pack(fill='x')
        self.title_frame.pack_propagate(False)

        # 標題文字
        self.title_label = tk.Label(
            self.title_frame,
            text=self.title,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        self.title_label.pack(side='left', padx=10, pady=2)

        # 關閉按鈕
        close_btn = tk.Button(
            self.title_frame,
            text='✕',
            command=self.close,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title'],
            bd=0,
            width=3,
            height=1
        )
        close_btn.pack(side='right', padx=5, pady=2)

    def create_label(self, parent, text, font_key='text', **kwargs):
        """建立標籤"""
        default_config = {
            'bg': AppConfig.COLORS['window_bg'],
            'fg': AppConfig.COLORS['text_color'],
            'font': AppConfig.FONTS[font_key]
        }
        default_config.update(kwargs)

        return tk.Label(parent, text=text, **default_config)

    def create_button(self, parent, text, command=None, style='Custom.TButton', **kwargs):
        """建立按鈕"""
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style=style,
            **kwargs
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
            font=AppConfig.FONTS['button'],
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
            font=AppConfig.FONTS['button'],
            width=10
        )
        cancel_btn.pack(side='left', padx=5)

        return ok_btn, cancel_btn

    def close(self):
        """關閉視窗"""
        try:
            if self.parent:
                # 🔥 溫和地釋放grab
                try:
                    self.window.grab_release()
                except:
                    pass
                # 🔥 溫和地返回焦點
                try:
                    self.parent.focus_set()
                except:
                    pass

            self.window.destroy()
        except:
            try:
                self.window.destroy()
            except:
                pass

    def show(self):
        """顯示視窗"""
        self.window.deiconify()

    def hide(self):
        """隱藏視窗"""
        self.window.withdraw()