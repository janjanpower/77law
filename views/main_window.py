#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import tkinter as tk
from tkinter import filedialog

from config.settings import AppConfig
from views.dialogs import UnifiedMessageDialog


class MainWindow:
    """主應用程式視窗"""

    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.case_overview = None
        self.selected_folder = None
        self.drag_data = {"x": 0, "y": 0}
        self.app_settings = self._load_app_settings()

        # 建立主視窗
        self.window = tk.Tk()
        self._setup_window()
        self._create_layout()

        # 🔥 新增：設定通知管理器的主視窗參考
        if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
            if hasattr(self.date_reminder_widget, 'notification_manager'):
                self.date_reminder_widget.notification_manager.set_main_window_reference(self.window)

    def _show_bell_popup(self, urgent_count: int):
        """
        🔥 修正版：顯示鈴鐺彈出提示 - 只相對主視窗置頂

        Args:
            urgent_count: 緊急案件數量
        """
        try:
            # 清除舊的彈出視窗
            if self.bell_popup_window:
                try:
                    self.bell_popup_window.destroy()
                except:
                    pass
                self.bell_popup_window = None

            # 建立彈出提示視窗
            self.bell_popup_window = tk.Toplevel(self.parent_window)
            self.bell_popup_window.overrideredirect(True)  # 無邊框
            self.bell_popup_window.configure(bg='red')

            # ========================================
            # 🔥 核心修改：只相對父視窗置頂
            # ========================================
            # 設定為父視窗的子視窗，這樣就只會在父視窗之上
            self.bell_popup_window.transient(self.parent_window)

            # ❌ 移除全域置頂
            # self.bell_popup_window.attributes('-topmost', True)  # 移除此行

            # 使用lift()相對於父視窗提升
            self.bell_popup_window.lift(self.parent_window)

            # 建立內容標籤
            bell_label = tk.Label(
                self.bell_popup_window,
                text=f"🔔 {urgent_count}",
                bg='red',
                fg='white',
                font=('Arial', 12, 'bold'),
                padx=8,
                pady=4
            )
            bell_label.pack()

            # 計算位置（相對於跑馬燈右側）
            self._position_bell_popup()

            # 顯示視窗
            self.bell_popup_window.deiconify()

            # 設定自動隱藏
            if self.bell_popup_job:
                self.parent_window.after_cancel(self.bell_popup_job)

            self.bell_popup_job = self.parent_window.after(3000, self._hide_bell_popup)

            print(f"✅ 鈴鐺彈出已顯示: {urgent_count}個緊急案件")

        except Exception as e:
            print(f"❌ 顯示鈴鐺彈出失敗: {e}")

    def _position_bell_popup(self):
        """
        🔥 修改：定位鈴鐺彈出視窗
        """
        try:
            # 更新視窗以取得實際尺寸
            self.bell_popup_window.update_idletasks()
            self.parent_window.update_idletasks()

            # 取得跑馬燈容器的位置
            marquee_x = self.marquee_container.winfo_rootx()
            marquee_y = self.marquee_container.winfo_rooty()
            marquee_width = self.marquee_container.winfo_width()
            marquee_height = self.marquee_container.winfo_height()

            # 取得彈出視窗尺寸
            popup_width = self.bell_popup_window.winfo_reqwidth()
            popup_height = self.bell_popup_window.winfo_reqheight()

            # 計算位置（跑馬燈右側）
            x = marquee_x + marquee_width + 5
            y = marquee_y + (marquee_height - popup_height) // 2

            # 確保不超出螢幕邊界
            screen_width = self.bell_popup_window.winfo_screenwidth()
            if x + popup_width > screen_width:
                x = marquee_x - popup_width - 5  # 改為左側顯示

            self.bell_popup_window.geometry(f"+{x}+{y}")

        except Exception as e:
            print(f"⚠️ 鈴鐺彈出定位失敗: {e}")

    def _load_app_settings(self):
        """載入應用程式設定"""
        # 取得主程式檔案所在目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        settings_file = os.path.join(script_dir, AppConfig.DATA_CONFIG['settings_file'])
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
        # 取得主程式檔案所在目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        settings_file = os.path.join(script_dir, AppConfig.DATA_CONFIG['settings_file'])
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
            font=AppConfig.FONTS['button'],  # 使用統一字體設定
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
        """選擇母資料夾 - 🔥 修正：檔案對話框置頂處理"""
        try:
            # 🔥 新增：暫時取消主視窗置頂，讓檔案對話框正常顯示
            original_topmost = False
            if hasattr(self.window, 'attributes'):
                try:
                    original_topmost = self.window.attributes('-topmost')
                    self.window.attributes('-topmost', False)
                except:
                    pass

            folder_path = filedialog.askdirectory(
                title="父資料夾位置",
                parent=self.window,  # 🔥 確保指定父視窗
                initialdir=self.app_settings.get('data_folder', os.path.expanduser('~'))
            )

            # 🔥 新增：檔案對話框關閉後立即恢復置頂
            self.window.after(100, lambda: self._restore_topmost_after_folder_dialog(original_topmost))

            if folder_path:
                # 建立必要的子資料夾結構
                self._create_data_structure(folder_path)

                self.folder_path_var.set(f"目前位置：{folder_path}")
                self.selected_folder = folder_path

                # 儲存設定
                self.app_settings['data_folder'] = folder_path
                self._save_app_settings()

                # 🔥 修正：使用正確的靜態方法顯示成功對話框
                UnifiedMessageDialog.show_success(
                    self.window,
                    f"已設定母資料夾：\n{folder_path}\n\n系統將在此資料夾內建立必要的子資料夾結構。"
                )

        except Exception as e:
            print(f"選擇母資料夾時發生錯誤: {e}")
            UnifiedMessageDialog.show_error(self.window, f"選擇資料夾時發生錯誤：{str(e)}")

    def _restore_topmost_after_folder_dialog(self, original_topmost):
        """🔥 新增：檔案對話框關閉後恢復置頂狀態"""
        try:
            if self.window and self.window.winfo_exists():
                # 恢復原本的置頂狀態（對於主視窗通常不需要置頂）
                if hasattr(self.window, 'attributes'):
                    self.window.attributes('-topmost', original_topmost)
                self.window.lift()
                self.window.focus_force()
                print("主視窗已恢復焦點")
        except Exception as e:
            print(f"恢復主視窗焦點失敗: {e}")

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
            # 使用 after 方法延遲執行，確保視窗切換順序正確
            self.window.after(50, self._show_case_overview)
        else:
            UnifiedMessageDialog.show_warning(self.window, "請先選擇母資料夾位置")

    def _show_case_overview(self):
        """顯示案件總覽"""
        if self.case_overview is None:
            # 🔥 修正：動態導入避免循環導入
            try:
                from views.case_overview import CaseOverviewWindow
                from controllers.case_controller import CaseController

                # 建立控制器，使用選定的資料夾
                data_file = os.path.join(self.selected_folder, AppConfig.DATA_CONFIG['case_data_file'])
                case_controller = CaseController(data_file)

                # 建立總覽視窗
                self.case_overview = CaseOverviewWindow(self.window, case_controller)

                # 綁定總覽視窗關閉事件
                self.case_overview.window.protocol("WM_DELETE_WINDOW", self._on_overview_close)

            except ImportError as e:
                print(f"無法載入案件總覽視窗: {e}")
                UnifiedMessageDialog.show_error(self.window, f"載入失敗：{str(e)}")
                return

        # 先顯示總覽視窗
        self.case_overview.show()
        # 再隱藏主視窗
        self.window.after(100, self.hide)

    def _on_overview_close(self):
        """總覽視窗關閉事件"""
        if self.case_overview:
            self.case_overview.window.destroy()
            self.case_overview = None
        # 重新顯示主視窗
        self.show()

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