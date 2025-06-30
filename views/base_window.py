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
        self._grab_enabled = True  # 新增：控制是否啟用 grab

        self._setup_window()
        self._setup_styles()
        self._create_layout()

        # 如果有父視窗，設定置頂
        if parent:
            self.window.transient(parent)
            # 🔥 修改：強制設定為置頂視窗，並立即設定模態
            self.window.attributes('-topmost', True)
            self.window.after(200, self._set_modal)
            # 🔥 新增：綁定焦點事件保持置頂
            self._setup_topmost_focus()

    def _setup_topmost_focus(self):
        """🔥 新增：設定保持置頂的焦點事件"""
        if self.parent:
            # 綁定焦點進入事件
            self.window.bind('<FocusIn>', self._on_focus_in)
            # 綁定視窗映射事件
            self.window.bind('<Map>', self._on_window_map)
            # 綁定滑鼠點擊事件
            self.window.bind('<Button-1>', self._on_window_click)

    def _on_focus_in(self, event=None):
        """🔥 新增：獲得焦點時確保置頂"""
        try:
            if self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
        except:
            pass

    def _on_window_map(self, event=None):
        """🔥 新增：視窗顯示時確保置頂"""
        try:
            if self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
        except:
            pass

    def _on_window_click(self, event=None):
        """🔥 新增：點擊視窗時確保置頂"""
        try:
            if self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
        except:
            pass


    def _set_modal(self):
        """設定模態對話框"""
        try:
            if self.window.winfo_exists() and self._grab_enabled:
                # 🔥 修改：確保在設定 grab 前視窗是置頂的
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
                self.window.grab_set()
        except:
            pass

    def disable_grab_temporarily(self, duration=1000):
        """暫時禁用 grab，用於特殊控件操作"""
        try:
            self.window.grab_release()
            self._grab_enabled = False
            # 在指定時間後重新啟用
            self.window.after(duration, self._enable_grab)
        except:
            pass

    def _enable_grab(self):
        """重新啟用 grab"""
        self._grab_enabled = True
        self._set_modal()
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
        """🔥 修改：改善關閉視窗的焦點處理"""
        try:
            # 如果是對話框（有父視窗），進行特殊處理
            if self.parent:
                # 取消置頂狀態和模態狀態
                try:
                    self.window.attributes('-topmost', False)
                    self.window.grab_release()
                except:
                    pass

                # 確保父視窗能正常接收焦點
                def restore_parent():
                    try:
                        if self.parent.winfo_exists():
                            self.parent.focus_force()
                            self.parent.lift()
                    except:
                        pass

                # 先銷毀視窗，再恢復父視窗焦點
                self.window.destroy()
                # 短暫延遲後恢復父視窗
                if hasattr(self.parent, 'after'):
                    self.parent.after(50, restore_parent)

            else:
                # 普通視窗直接銷毀
                self.window.destroy()

        except Exception as e:
            print(f"關閉視窗時發生錯誤: {e}")
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