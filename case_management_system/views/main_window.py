import tkinter as tk
from tkinter import filedialog, messagebox
from config.settings import AppConfig

class MainWindow:
    """主應用程式視窗 - 簡化版本避免繼承問題"""

    def __init__(self):
        self.case_overview = None
        self.selected_folder = None
        self.drag_data = {"x": 0, "y": 0}

        # 建立主視窗
        self.window = tk.Tk()
        self._setup_window()
        self._create_layout()

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title(AppConfig.DEFAULT_WINDOW['title'])
        self.window.geometry(f"{AppConfig.DEFAULT_WINDOW['width']}x{AppConfig.DEFAULT_WINDOW['height']}")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])

        # 移除系統標題欄
        self.window.overrideredirect(True)

        # 設定最小尺寸
        self.window.minsize(
            AppConfig.SIZES['min_window']['width'],
            AppConfig.SIZES['min_window']['height']
        )

        # 置中顯示
        self._center_window()

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        width = AppConfig.DEFAULT_WINDOW['width']
        height = AppConfig.DEFAULT_WINDOW['height']
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _create_layout(self):
        """建立視窗佈局"""
        # 主容器 - 移除內邊距
        self.main_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['window_bg']
        )
        self.main_frame.pack(fill='both', expand=True)  # 移除 padx=5, pady=5

        # 自定義標題列 - 移除下邊距
        self.title_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        self.title_frame.pack(fill='x')  # 移除 pady=(0, 5)
        self.title_frame.pack_propagate(False)

        # 標題標籤 - 移除展開
        self.title_label = tk.Label(
            self.title_frame,
            text=AppConfig.DEFAULT_WINDOW['title'],
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Microsoft JhengHei', 14, 'bold')
        )
        self.title_label.pack(side='left', padx=10)  # 改為固定左邊距，移除 expand=True

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
        self.close_btn.pack(side='right', padx=10)  # 改為固定右邊距

        # 設定拖曳功能
        self._setup_drag()

        # 內容區域
        self.content_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.content_frame.pack(fill='both', expand=True)

        # 建立主視窗內容
        self._create_main_content()

    def _setup_drag(self):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        # 綁定標題列拖曳事件
        self.title_frame.bind("<Button-1>", start_drag)
        self.title_frame.bind("<B1-Motion>", on_drag)
        self.title_label.bind("<Button-1>", start_drag)
        self.title_label.bind("<B1-Motion>", on_drag)

    def _create_main_content(self):
        """建立主視窗內容"""
        # 歡迎訊息
        welcome_label = tk.Label(
            self.content_frame,
            text="歡迎使用案件管理系統",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Microsoft JhengHei', 16, 'bold')
        )
        welcome_label.pack(expand=True)

        # 主功能按鈕區域
        button_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        button_frame.pack(expand=True)

        # 選擇資料夾按鈕
        self.folder_btn = tk.Button(
            button_frame,
            text='選擇資料夾位置',
            command=self._choose_folder,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=('Microsoft JhengHei', 10),
            width=15,
            height=2
        )
        self.folder_btn.pack(pady=10)

        # 資料夾路徑顯示
        self.folder_path_var = tk.StringVar(value="尚未選擇資料夾")
        self.folder_label = tk.Label(
            button_frame,
            textvariable=self.folder_path_var,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Microsoft JhengHei', 10),
            wraplength=400
        )
        self.folder_label.pack(pady=5)

        # 按鈕區域
        action_frame = tk.Frame(
            button_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        action_frame.pack(pady=20)

        # 確認按鈕
        confirm_btn = tk.Button(
            action_frame,
            text='確認',
            command=self._on_confirm,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=('Microsoft JhengHei', 10),
            width=10,
            height=2
        )
        confirm_btn.pack(side='left', padx=10)

        # 離開按鈕
        exit_btn = tk.Button(
            action_frame,
            text='離開',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=('Microsoft JhengHei', 10),
            width=10,
            height=2
        )
        exit_btn.pack(side='left', padx=10)

    def _choose_folder(self):
        """選擇資料夾"""
        folder_path = filedialog.askdirectory(title="選擇案件資料儲存位置")
        if folder_path:
            self.folder_path_var.set(f"已選擇：{folder_path}")
            self.selected_folder = folder_path

    def _on_confirm(self):
        """確認按鈕事件"""
        if hasattr(self, 'selected_folder') and self.selected_folder:
            self._show_case_overview()
        else:
            messagebox.showwarning("提醒", "請先選擇資料夾位置")

    def _show_case_overview(self):
        """顯示案件總覽"""
        if self.case_overview is None:
            # 動態導入避免循環導入
            from views.case_overview import CaseOverviewWindow
            self.case_overview = CaseOverviewWindow(self.window)

            # 測試資料
            from models.case_model import CaseData
            test_cases = [
                CaseData("C20250001", "刑事", "張三", "李律師", "王法務", "一審"),
                CaseData("C20250002", "民事", "李四", "陳律師", None, "二審"),
                CaseData("C20250003", "刑事", "王五", None, "林法務", "合議庭"),
            ]
            self.case_overview.update_case_data(test_cases)

        self.case_overview.show()

    def close(self):
        """關閉視窗"""
        self.window.destroy()

    def show(self):
        """顯示視窗"""
        self.window.deiconify()

    def hide(self):
        """隱藏視窗"""
        self.window.withdraw()

    def run(self):
        """啟動應用程式"""
        self.window.mainloop()
