import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
from config.settings import AppConfig

class MainWindow:
    """主應用程式視窗"""

    def __init__(self):
        self.case_overview = None
        self.selected_folder = None
        self.drag_data = {"x": 0, "y": 0}
        self.app_settings = self._load_app_settings()

        # 建立主視窗
        self.window = tk.Tk()
        self._setup_window()
        self._create_layout()

    def _load_app_settings(self):
        """載入應用程式設定"""
        settings_file = AppConfig.DATA_CONFIG['settings_file']
        default_settings = {
            'data_folder': None,
            'last_opened': None
        }

        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"載入設定失敗: {e}")

        return default_settings

    def _save_app_settings(self):
        """儲存應用程式設定"""
        settings_file = AppConfig.DATA_CONFIG['settings_file']
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存設定失敗: {e}")

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title(AppConfig.WINDOW_TITLES['main'])  # 使用統一標題
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
        # 主容器
        self.main_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['window_bg']
        )
        self.main_frame.pack(fill='both', expand=True)

        # 自定義標題列
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
            text=AppConfig.WINDOW_TITLES['main'],
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
            font=AppConfig.FONTS['welcome']  # 使用統一字體設定
        )
        welcome_label.pack(expand=True,pady=(10,0))

        # 主功能按鈕區域
        button_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        button_frame.pack(expand=True)

        # 選擇資料夾按鈕
        self.folder_btn = tk.Button(
            button_frame,
            text='選擇主要資料夾',  # 更明確的說明
            command=self._choose_data_folder,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用統一字體設定
            width=18,
            height=2
        )
        self.folder_btn.pack(pady=(0,30))

        # 資料夾路徑顯示
        initial_path = self.app_settings.get('data_folder', '尚未選擇母資料夾')
        if initial_path and initial_path != '尚未選擇母資料夾':
            self.selected_folder = initial_path

        self.folder_path_var = tk.StringVar(value=f"目前位置：{initial_path}" if initial_path != '尚未選擇母資料夾' else initial_path)
        self.folder_label = tk.Label(
            button_frame,
            textvariable=self.folder_path_var,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],  # 使用統一字體設定
            wraplength=350
        )
        self.folder_label.pack(pady=5)

        # 按鈕區域
        action_frame = tk.Frame(
            button_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        action_frame.pack(pady=(0,25))

        # 確認按鈕
        confirm_btn = tk.Button(
            action_frame,
            text='進入系統',
            command=self._on_confirm,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用統一字體設定
            width=10,
            height=2
        )
        confirm_btn.pack(side='left', padx=10,pady=(10,0))

        # 離開按鈕
        exit_btn = tk.Button(
            action_frame,
            text='離開',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用統一字體設定
            width=10,
            height=2
        )
        exit_btn.pack(side='left', padx=10,pady=(10,0))

    def _choose_data_folder(self):
        """選擇母資料夾"""
        folder_path = filedialog.askdirectory(
            title="父資料夾位置",
            initialdir=self.app_settings.get('data_folder', os.path.expanduser('~'))
        )

        if folder_path:
            # 建立必要的子資料夾結構
            self._create_data_structure(folder_path)

            self.folder_path_var.set(f"目前位置：{folder_path}")
            self.selected_folder = folder_path

            # 儲存設定
            self.app_settings['data_folder'] = folder_path
            self._save_app_settings()

            messagebox.showinfo("成功", f"已設定母資料夾：\n{folder_path}\n\n系統將在此資料夾內建立必要的子資料夾結構。")

    def _create_data_structure(self, base_path):
        """建立資料夾結構"""
        try:
            # 只建立刑事和民事資料夾
            folders_to_create = list(AppConfig.CASE_TYPE_FOLDERS.values())

            for folder in folders_to_create:
                folder_path = os.path.join(base_path, folder)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"建立資料夾：{folder_path}")

        except Exception as e:
            print(f"建立資料夾結構失敗：{e}")

    def _on_confirm(self):
        """確認按鈕事件"""
        if hasattr(self, 'selected_folder') and self.selected_folder:
            self._show_case_overview()
        else:
            messagebox.showwarning("提醒", "請先選擇母資料夾位置")

    def _show_case_overview(self):
        """顯示案件總覽"""
        if self.case_overview is None:
            # 動態導入避免循環導入
            from views.case_overview import CaseOverviewWindow
            from controllers.case_controller import CaseController

            # 建立控制器，使用選定的資料夾
            data_file = os.path.join(self.selected_folder, AppConfig.DATA_CONFIG['case_data_file'])
            case_controller = CaseController(data_file)

            # 建立總覽視窗
            self.case_overview = CaseOverviewWindow(self.window, case_controller)

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