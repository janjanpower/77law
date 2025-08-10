#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
controllers/login_controller.py (增強版)
法律案件管理系統 - 登入視窗控制層
整合 auth_controller_layer 的功能，保持現有架構和樣式
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import requests

# 導入現有配置和基礎視窗邏輯
from config.settings import AppConfig
from views.base_window import BaseWindow
from views.login_logic import LoginLogic
from views.dialog_base import CustomDialog, open_modal_dialog

# 安全導入對話框
try:
    from views.dialogs import UnifiedMessageDialog
    DIALOGS_AVAILABLE = True
except ImportError:
    import tkinter.messagebox as messagebox
    DIALOGS_AVAILABLE = False

    class UnifiedMessageDialog:
        @staticmethod
        def show_success(parent, message, title="成功"):
            messagebox.showinfo(title, message)
        @staticmethod
        def show_error(parent, message, title="錯誤"):
            messagebox.showerror(title, message)
        @staticmethod
        def show_warning(parent, message, title="警告"):
            messagebox.showwarning(title, message)


class LoginController(BaseWindow):
    """登入視窗控制層 - 增強版，保持現有架構"""

    def __init__(self, api_base_url: str = "https://law-controller.herokuapp.com",
                 on_login_success: Optional[Callable] = None):
        """
        初始化登入控制器

        Args:
            api_base_url: API 基礎 URL
            on_login_success: 登入成功回調函數
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.on_login_success = on_login_success

        # 初始化增強版邏輯層
        self.logic = LoginLogic(self.api_base_url)

        # 登入狀態
        self.is_logged_in = False
        self.user_data = None

        # UI 變數
        self.username_var = None
        self.password_var = None
        self.remember_var = None  # 🔥 新增：記住密碼選項
        self.status_label = None
        self.progress_bar = None

        # 拖曳資料
        self.drag_data = {"x": 0, "y": 0}

        # 🔥 新增：登入嘗試計數
        self.login_attempts = 0
        self.max_attempts = 3

        # 套用BaseWindow邏輯，設定登入視窗專用參數
        super().__init__(
            title="登入系統",
            width=320,  # 🔥 稍微增寬以容納新功能
            height=400,  # 🔥 稍微增高
            resizable=False,
            parent=None
        )

        # 載入儲存的登入資訊
        self._load_saved_credentials()

    def _create_layout(self):
        """建立視窗佈局 - 增強版"""
        # 主容器
        self.main_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['window_bg']
        )
        self.main_frame.pack(fill='both', expand=True)

        # 自訂標題列
        self.title_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        self.title_frame.pack(fill='x')
        self.title_frame.pack_propagate(False)

        # 標題標籤
        self.title_label = tk.Label(
            self.title_frame,
            text="登入系統",  # 🔥 增加圖示
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        self.title_label.pack(side='left', padx=(5,5))

        # 🔥 新增：連線狀態指示器
        self.connection_indicator = tk.Label(
            self.title_frame,
            text="●",
            bg=AppConfig.COLORS['title_bg'],
            fg="#ff6b6b",  # 預設紅色（未連線）
            font=('Arial', 15)
        )
        self.connection_indicator.pack(side='left')

        # 關閉按鈕
        self.close_btn = tk.Button(
            self.title_frame,
            text="✕",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 12, 'bold'),
            bd=0,
            width=3,
            command=self._handle_exit
        )
        self.close_btn.pack(side='right', padx=10)

        # 設定拖曳功能
        self._setup_drag()

        # 內容區域
        self.content_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.content_frame.pack(fill='both', expand=True, padx=20, pady=15)

        # 建立登入表單內容
        self._create_login_content()

        # 🔥 新增：啟動時檢查連線狀態
        self._check_connection_status()

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

    def _create_login_content(self):
        """建立登入表單內容 - 增強版"""
        # 系統標題
        system_title = tk.Label(
            self.content_frame,
            text="法律案件管理系統",
            font=('Microsoft JhengHei', 12, 'bold'),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color']
        )
        system_title.pack(pady=(10, 5))

        # 🔥 新增：版本資訊
        version_label = tk.Label(
            self.content_frame,
            text="v1.0 Editor : JanLee",
            font=('Microsoft JhengHei', 8),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS.get('secondary_text', '#7f8c8d')
        )
        version_label.pack(pady=(0, 15))

        # 帳號輸入區
        account_label = tk.Label(
            self.content_frame,
            text="事務所帳號",
            font=AppConfig.FONTS['text'],
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            width=17
        )
        account_label.pack(anchor='w', pady=(0, 5))

        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(
            self.content_frame,
            textvariable=self.username_var,
            font=AppConfig.FONTS['text'],
            bg='white',
            fg='black',
            relief='sunken',
            width=25,
            bd=1
        )
        self.username_entry.pack(anchor='center', pady=(0, 15))

        # 密碼輸入區
        password_label = tk.Label(
            self.content_frame,
            text="密碼",
            font=AppConfig.FONTS['text'],
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            width=12
        )
        password_label.pack(anchor='w', pady=(0, 5))

        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(
            self.content_frame,
            textvariable=self.password_var,
            font=AppConfig.FONTS['text'],
            bg='white',
            fg='black',
            show='*',
            relief='sunken',
            width=25,
            bd=1
        )
        self.password_entry.pack(anchor='center', pady=(0, 10))

        # 🔥 新增：記住密碼選項
        options_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        options_frame.pack(fill='x', pady=(0, 15))

        self.remember_var = tk.BooleanVar()
        remember_check = tk.Checkbutton(
            options_frame,
            text="記住帳號密碼",
            variable=self.remember_var,
            font=('Microsoft JhengHei', 9),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            activebackground=AppConfig.COLORS['window_bg'],
            selectcolor='white',
            width=18
        )
        remember_check.pack(anchor='w')

        # 🔥 新增：忘記密碼按鈕
        forgot_btn = tk.Button(
            options_frame,
            text="忘記密碼？",
            font=('Microsoft JhengHei', 9),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS.get('link_color', '#3498db'),
            bd=0,
            cursor='hand2',
            command=self._handle_forgot_password,
            width=15
        )
        forgot_btn.pack(side='right')

        # 按鈕區域
        button_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=(5, 0))

        # 置中的按鈕容器
        center_button_frame = tk.Frame(button_frame, bg=AppConfig.COLORS['window_bg'])
        center_button_frame.pack(expand=True)

        # 登入按鈕
        self.login_btn = tk.Button(
            center_button_frame,
            text="登入",
            font=AppConfig.FONTS['button'],
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            width=8,
            height=1,
            command=self._handle_login,
            relief='raised',
            bd=2
        )
        self.login_btn.pack(side='left', padx=(0, 20))

        # 退出按鈕
        self.exit_btn = tk.Button(
            center_button_frame,
            text="退出",
            font=AppConfig.FONTS['button'],
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            width=8,
            height=1,
            command=self._handle_exit,
            relief='raised',
            bd=2
        )
        self.exit_btn.pack(side='left',padx=(20,0))

        # 整個內容區設為填滿，避免高度不足蓋掉按鈕
        self.content_frame.pack_propagate(False)

        footer = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        # 關鍵：固定在底部
        footer.pack(side='bottom', fill='x', pady=(12, 8))

        register_btn = tk.Button(
            footer,
            text="註冊用戶",
            font=('Microsoft JhengHei', 9),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS.get('link_color', '#3498db'),
            bd=0,
            cursor='hand2',
            command=self._open_register_dialog,
            width=12
        )
        # 關鍵：置中
        register_btn.pack(anchor='center')

        # 狀態顯示區域
        self.status_label = tk.Label(
            self.content_frame,
            text="",
            font=('Microsoft JhengHei', 10),
            bg=AppConfig.COLORS['window_bg'],
            wraplength=160
        )

        # 進度條
        self.progress_bar = ttk.Progressbar(
            self.content_frame,
            mode='indeterminate'
        )

        # 🔥 新增：快捷資訊區域
        self._create_info_area()


        # 設定事件綁定
        self._setup_key_bindings()

    def _create_info_area(self):
        """建立資訊顯示區域"""
        info_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        info_frame.pack(fill='x', pady=(10, 0))

        # 🔥 新增：上次登入資訊
        self.last_login_label = tk.Label(
            info_frame,
            text="",
            font=('Microsoft JhengHei', 8),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS.get('info_color', '#7f8c8d')
        )
        self.last_login_label.pack(anchor='w')

    def _create_register_footer(self):
        """建立底部置中的『註冊用戶』連結，樣式與『忘記密碼？』一致"""
        footer = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        footer.pack(fill='x', pady=(12, 6))

        register_btn = tk.Button(
            footer,
            text="註冊用戶",
            font=('Microsoft JhengHei', 9),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS.get('link_color', '#3498db'),
            bd=0,
            cursor='hand2',
            command=self._open_register_dialog,
            width=12
        )
        register_btn.pack(anchor='center')

    def _setup_key_bindings(self):
        """設定鍵盤事件綁定"""
        # Enter鍵登入
        self.window.bind('<Return>', lambda event: self._handle_login())

        # Escape鍵退出
        self.window.bind('<Escape>', lambda event: self._handle_exit())

        # Tab鍵切換焦點
        self.username_entry.bind('<Tab>', lambda e: self.password_entry.focus())

        # F5刷新連線狀態
        self.window.bind('<F5>', lambda event: self._check_connection_status())

        # 設定初始焦點
        if self.username_var.get():
            self.password_entry.focus_set()
        else:
            self.username_entry.focus_set()

    # ==================== 🔥 新增：增強功能 ====================



    def _check_connection_status(self):
        """檢查連線狀態並更新指示器"""
        def check_in_thread():
            connected, message = self.logic.check_api_connection()
            self.window.after(0, lambda: self._update_connection_indicator(connected, message))

        threading.Thread(target=check_in_thread, daemon=True).start()

    def _update_connection_indicator(self, connected: bool, message: str):
        """更新連線狀態指示器"""
        if connected:
            self.connection_indicator.config(fg="#2ecc71")  # 綠色
            tooltip_text = f"連線正常: {message}"
        else:
            self.connection_indicator.config(fg="#e74c3c")  # 紅色
            tooltip_text = f"連線失敗: {message}"

        # 設定工具提示（簡化版）
        def on_enter(event):
            self._show_status(tooltip_text, "info")

        def on_leave(event):
            self._clear_status_message()

        self.connection_indicator.bind("<Enter>", on_enter)
        self.connection_indicator.bind("<Leave>", on_leave)

    def _handle_forgot_password(self):
        """處理忘記密碼"""
        message = """忘記密碼解決方案：

1. 聯繫您的系統管理員
2. 發送郵件至: support@lawfirm.com
3. 電話諮詢: (02) 1234-5678

請提供您的事務所名稱和帳號資訊。"""

        if DIALOGS_AVAILABLE:
            UnifiedMessageDialog.show_info(self.window, message, "忘記密碼")
        else:
            messagebox.showinfo("忘記密碼", message)



    # ==================== 事件處理方法 ====================

    def _handle_login(self):
        """處理登入按鈕點擊 - 增強版"""
        client_id = self.username_var.get().strip()
        password = self.password_var.get().strip()

        # 🔥 增強：檢查登入嘗試次數
        if self.login_attempts >= self.max_attempts:
            self._show_error_message(f"登入嘗試次數過多，請稍後再試")
            return

        # 輸入驗證
        if not self._validate_login_input(client_id, password):
            return

        # 增加嘗試次數
        self.login_attempts += 1

        # 顯示載入狀態
        self._show_loading_state("正在驗證帳號密碼...")

        # 在背景執行緒中執行登入
        threading.Thread(
            target=self._perform_login,
            args=(client_id, password),
            daemon=True
        ).start()

    def _handle_exit(self):
        """處理退出按鈕點擊"""
        if messagebox.askokcancel("確認退出", "確定要退出登入系統嗎？"):
            self.close()

    # ==================== 輸入驗證方法 ====================

    def _validate_login_input(self, client_id: str, password: str) -> bool:
        """驗證登入輸入 - 增強版"""
        if not client_id:
            self._show_error_message("請輸入事務所帳號")
            self.username_entry.focus_set()
            return False

        if not password:
            self._show_error_message("請輸入密碼")
            self.password_entry.focus_set()
            return False

        if len(client_id) < 3:
            self._show_error_message("帳號長度至少需要3個字元")
            self.username_entry.focus_set()
            return False

        # 🔥 新增：密碼長度檢查
        if len(password) < 3:
            self._show_error_message("密碼長度至少需要3個字元")
            self.password_entry.focus_set()
            return False

        return True

    # ==================== 登入處理方法 ====================

    def _perform_login(self, client_id: str, password: str):
        """執行登入流程 - 增強版"""
        try:
            # 呼叫邏輯層進行登入驗證
            login_result = self.logic.authenticate_user(client_id, password)

            # 在主執行緒中處理結果
            self.window.after(0, lambda: self._handle_login_result(login_result, client_id, password))

        except Exception as e:
            # 在主執行緒中顯示錯誤
            self.window.after(0, lambda: self._handle_login_error(str(e)))

    def _handle_login_result(self, result: Dict[str, Any], client_id: str, password: str):
        """處理登入結果 - 增強版"""
        self._hide_loading_state()

        if result.get('success', False):
            # 重置登入嘗試次數
            self.login_attempts = 0

            self.user_data = result.get('user_data', {})
            self.is_logged_in = True

            # 顯示成功訊息
            client_name = self.user_data.get('client_name', self.user_data.get('username', client_id))
            self._show_success_message(f"登入成功！歡迎 {client_name}")

            # 🔥 增強：儲存登入資訊（根據用戶選擇）
            remember = self.remember_var.get()
            if remember:
                self.logic.save_user_credentials(client_id, password, True)
                print("✅ 帳號密碼已儲存")

            # 呼叫成功回調
            if self.on_login_success:
                self.on_login_success(self.user_data)

            # 延遲關閉視窗
            self.window.after(1500, self.close)

        else:
            error_message = result.get('message', '登入失敗，請檢查帳號密碼')
            self._show_error_message(error_message)

            # 🔥 增強：智能焦點設定
            if "密碼" in error_message:
                self.password_var.set("")
                self.password_entry.focus_set()
            elif "帳號" in error_message:
                self.username_entry.focus_set()

            # 🔥 增強：顯示剩餘嘗試次數
            remaining = self.max_attempts - self.login_attempts
            if remaining > 0:
                self.window.after(2000, lambda: self._show_status(f"剩餘嘗試次數: {remaining}", "warning"))

    def _handle_login_error(self, error_message: str):
        """處理登入錯誤"""
        self._hide_loading_state()
        self._show_error_message(f"登入過程發生錯誤：{error_message}")

    # ==================== UI 狀態控制方法 ====================

    def _show_loading_state(self, message: str):
        """顯示載入狀態"""
        self.status_label.config(
            text=message,
            fg=AppConfig.COLORS.get('info_color', '#3498db')
        )
        self.status_label.pack(pady=(10, 5))

        self.progress_bar.pack(fill='x', pady=(0, 10))
        self.progress_bar.start()

        # 禁用輸入控件
        self._set_controls_enabled(False)

    def _hide_loading_state(self):
        """隱藏載入狀態"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

        # 啟用輸入控件
        self._set_controls_enabled(True)

    def _show_success_message(self, message: str):
        """顯示成功訊息"""
        self.status_label.config(
            text=message,
            fg=AppConfig.COLORS.get('success_color', '#27ae60')
        )
        self.status_label.pack(pady=(10, 5))

    def _show_error_message(self, message: str):
        """顯示錯誤訊息"""
        self.status_label.config(
            text=message,
            fg=AppConfig.COLORS.get('error_color', '#e74c3c')
        )
        self.status_label.pack(pady=(10, 5))

        # 清除狀態顯示
        self.window.after(5000, self._clear_status_message)

    def _show_status(self, message: str, status_type: str = "info"):
        """顯示狀態訊息"""
        color_map = {
            "success": AppConfig.COLORS.get('success_color', '#27ae60'),
            "error": AppConfig.COLORS.get('error_color', '#e74c3c'),
            "warning": AppConfig.COLORS.get('warning_color', '#f39c12'),
            "info": AppConfig.COLORS.get('info_color', '#3498db')
        }

        self.status_label.config(
            text=message,
            fg=color_map.get(status_type, '#7f8c8d')
        )
        self.status_label.pack(pady=(10, 5))

    def _clear_status_message(self):
        """清除狀態訊息"""
        if self.status_label:
            self.status_label.pack_forget()

    def _set_controls_enabled(self, enabled: bool):
        """設定控件啟用/禁用狀態"""
        state = 'normal' if enabled else 'disabled'

        controls = [
            self.username_entry, self.password_entry,
            self.login_btn, self.exit_btn,
        ]

        for control in controls:
            if hasattr(control, 'config'):
                control.config(state=state)

    # ==================== 資料載入方法 ====================

    def _load_saved_credentials(self):
        """載入儲存的登入資訊 - 增強版"""
        try:
            client_id, _ = self.logic.load_saved_credentials()
            if client_id and hasattr(self, 'username_var'):
                self.username_var.set(client_id)
                # 如果有儲存的帳號，預設勾選記住密碼
                if hasattr(self, 'remember_var'):
                    self.remember_var.set(True)
                print(f"✅ 已載入儲存的帳號: {client_id}")
        except Exception as e:
            print(f"⚠️ 載入儲存登入資訊失敗: {e}")

    # ==================== 視窗管理方法 ====================

    def close(self):
        """關閉視窗 - 增強版"""
        try:
            # 清理資源
            if hasattr(self, 'progress_bar'):
                self.progress_bar.stop()

            # 🔥 新增：儲存視窗狀態
            try:
                window_state = {
                    'geometry': self.window.geometry(),
                    'last_closed': datetime.now().isoformat()
                }
                config = self.logic._load_config()
                config['window_state'] = window_state
                self.logic._save_config(config)
            except Exception as e:
                print(f"⚠️ 儲存視窗狀態失敗: {e}")

            # 呼叫父類的關閉方法
            super().close()

        except Exception as e:
            print(f"❌ 關閉登入視窗時發生錯誤: {e}")

    def show(self):
        """顯示登入視窗並啟動事件循環 - 增強版"""
        try:
            # 🔥 新增：載入視窗狀態
            try:
                config = self.logic._load_config()
                window_state = config.get('window_state', {})
                if window_state.get('geometry'):
                    self.window.geometry(window_state['geometry'])
            except Exception as e:
                print(f"⚠️ 載入視窗狀態失敗: {e}")

            # 套用BaseWindow的顯示邏輯
            if self.window:
                self.window.deiconify()
                self.window.lift()
                self.window.focus_force()

                # 確保置頂
                if hasattr(self, 'ensure_topmost'):
                    self.ensure_topmost()

                # 🔥 新增：顯示歡迎訊息
                self._show_status("請輸入您的帳號密碼", "info")

                # 啟動主事件循環
                self.window.mainloop()

        except Exception as e:
            print(f"❌ 顯示登入視窗失敗: {e}")

    # ==================== 公共方法 ====================

    def get_user_data(self) -> Optional[Dict[str, Any]]:
        """取得登入用戶資料"""
        return self.user_data if self.is_logged_in else None

    def is_admin_user(self) -> bool:
        """檢查是否為管理員用戶"""
        return self.user_data.get("is_admin", False) if self.user_data else False

    def get_system_info(self) -> Dict[str, Any]:
        """取得系統資訊"""
        try:
            return {
                'login_attempts': self.login_attempts,
                'max_attempts': self.max_attempts,
                'is_logged_in': self.is_logged_in,
                'api_url': self.api_base_url,
                'logic_info': self.logic.get_system_info()
            }
        except Exception as e:
            return {'error': str(e)}


# ==================== 整合現有系統的管理類別 ====================

    def _open_register_dialog(self):
        result, dlg = open_modal_dialog(self.window, RegisterDialog, self.api_base_url, borderless=True)
        if result and result.get("success"):
            sc = result.get("secret_code") or ""
            try:
                if DIALOGS_AVAILABLE:
                    UnifiedMessageDialog.show_success(self.window, f"註冊成功！\n\n您的律師登陸號：{sc}", "註冊完成")
                else:
                    messagebox.showinfo("註冊完成", f"註冊成功！\n\n您的律師登陸號：{sc}")
            except Exception:
                messagebox.showinfo("註冊完成", f"註冊成功！\n\n您的律師登陸號：{sc}")

            if result.get("client_id"):
                self.username_var.set(result["client_id"])
            if result.get("password"):
                self.password_var.set(result["password"])
                self.password_entry.focus_set()


class RegisterDialog(CustomDialog):
        def __init__(self, parent, api_base_url: str, borderless: bool = True):
            self.api_base_url = api_base_url.rstrip('/')
            self.result = None
            super().__init__(parent, title="註冊用戶", size=(340, 280), borderless=borderless, modal=True)

        def build_body(self, parent):
            import tkinter as tk
            from tkinter import messagebox

            from config.settings import AppConfig  # 與你的檔案一致的匯入

            tk.Label(parent, text="事務所名稱", font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                    bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'),
                    fg=AppConfig.COLORS.get('text_color', '#2c3e50')).grid(row=0, column=0, sticky='w', pady=(0,4))
            self.var_name = tk.StringVar()
            self.entry_name = tk.Entry(parent, textvariable=self.var_name,
                                    font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)), width=26)
            self.entry_name.grid(row=1, column=0, sticky='we', pady=(0,8))

            tk.Label(parent, text="帳號（client_id）", font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                    bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'),
                    fg=AppConfig.COLORS.get('text_color', '#2c3e50')).grid(row=2, column=0, sticky='w', pady=(0,4))
            self.var_id = tk.StringVar()
            self.entry_id = tk.Entry(parent, textvariable=self.var_id,
                                    font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)), width=26)
            self.entry_id.grid(row=3, column=0, sticky='we', pady=(0,8))

            tk.Label(parent, text="密碼", font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                    bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'),
                    fg=AppConfig.COLORS.get('text_color', '#2c3e50')).grid(row=4, column=0, sticky='w', pady=(0,4))
            self.var_pwd = tk.StringVar()
            self.entry_pwd = tk.Entry(parent, textvariable=self.var_pwd,
                                    font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                                    show='*', width=26)
            self.entry_pwd.grid(row=5, column=0, sticky='we', pady=(0,8))

            parent.grid_columnconfigure(0, weight=1)

            btns = tk.Frame(parent, bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'))
            btns.grid(row=6, column=0, pady=(6, 0))
            tk.Button(btns, text="送出註冊",
                    font=AppConfig.FONTS.get('button', ('Microsoft JhengHei', 10, 'bold')),
                    bg=AppConfig.COLORS.get('button_bg', '#3498db'),
                    fg=AppConfig.COLORS.get('button_fg', '#ffffff'),
                    width=10, command=self._submit).pack(side='left', padx=10)
            tk.Button(btns, text="取消",
                    font=AppConfig.FONTS.get('button', ('Microsoft JhengHei', 10, 'bold')),
                    bg=AppConfig.COLORS.get('button_bg', '#3498db'),
                    fg=AppConfig.COLORS.get('button_fg', '#ffffff'),
                    width=10, command=self.close).pack(side='left', padx=10)

            # 指定第一個聚焦欄位
            self.first_focus = lambda: (self.entry_name.focus_set(), self.entry_name.icursor('end'))

            # 快捷鍵
            self.top.bind('<Return>', lambda e: self._submit())
            self.top.bind('<Escape>', lambda e: self.close())

        def _submit(self):
            import requests, tkinter as tk
            from tkinter import messagebox
            name = self.var_name.get().strip()
            cid  = self.var_id.get().strip()
            pwd  = self.var_pwd.get().strip()
            if not name:
                messagebox.showwarning("提示", "請輸入事務所名稱"); return
            if len(cid) < 3:
                messagebox.showwarning("提示", "帳號長度至少 3 個字元"); return
            if len(pwd) < 6:
                messagebox.showwarning("提示", "密碼長度至少 6 個字元"); return

            url = f"{self.api_base_url}/register"
            try:
                resp = requests.post(url, json={"client_name": name, "client_id": cid, "password": pwd}, timeout=15)
                if resp.status_code == 201:
                    data = resp.json()
                    self.result = {"success": True, "client_id": data.get("client_id"),
                                "secret_code": data.get("secret_code"), "password": pwd}
                    self.close()
                else:
                    try: msg = resp.json().get("detail") or resp.text
                    except Exception: msg = resp.text
                    messagebox.showwarning("提示", f"註冊失敗：{msg}")
            except Exception as e:
                messagebox.showwarning("提示", f"連線失敗：{e}")

class LoginManager:
    """登入管理器 - 增強版"""

    def __init__(self, main_window, api_base_url: str = "https://law-controller.herokuapp.com"):
        self.main_window = main_window
        self.api_base_url = api_base_url
        self.current_user = None
        self.is_logged_in = False

    def show_login_window(self) -> bool:
        """顯示登入視窗並等待結果"""
        login_controller = LoginController(
            api_base_url=self.api_base_url,
            on_login_success=self._on_login_success
        )

        # 套用BaseWindow的等待機制
        if hasattr(self.main_window, 'wait_window'):
            self.main_window.wait_window(login_controller.window)
        else:
            login_controller.show()

        return self.is_logged_in

    def _on_login_success(self, user_data: Dict[str, Any]):
        """登入成功處理"""
        self.current_user = user_data
        self.is_logged_in = True

        # 更新主視窗狀態
        if hasattr(self.main_window, '_on_user_login'):
            self.main_window._on_user_login(user_data)

    def logout(self):
        """登出"""
        self.current_user = None
        self.is_logged_in = False

        # 更新主視窗狀態
        if hasattr(self.main_window, '_on_user_logout'):
            self.main_window._on_user_logout()

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """取得當前登入用戶"""
        return self.current_user if self.is_logged_in else None

    def is_admin(self) -> bool:
        """檢查是否為管理員"""
        return self.current_user.get("is_admin", False) if self.current_user else False

    def get_client_id(self) -> Optional[str]:
        """取得客戶ID"""
        return self.current_user.get("client_id") if self.current_user else None

    def get_client_name(self) -> Optional[str]:
        """取得客戶名稱"""
        return self.current_user.get("client_name") if self.current_user else None
