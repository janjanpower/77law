# views/cloud_setup_dialog.py
"""
雲端設定對話框 - 一鍵設定雲端同步
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable
from config.settings import AppConfig
from utils.cloud_sync import CloudSync
from views.base_window import BaseWindow
from views.dialogs import UnifiedMessageDialog

class CloudSetupDialog(BaseWindow):
    """雲端設定對話框"""

    def __init__(self, parent=None, on_setup_complete: Optional[Callable] = None):
        self.on_setup_complete = on_setup_complete
        self.cloud_sync = CloudSync()
        self.detected_services = {}

        title = "雲端同步設定"
        super().__init__(title=title, width=500, height=400, resizable=False, parent=parent)

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._detect_services()
        self._create_setup_content()

    def _detect_services(self):
        """偵測雲端服務"""
        self.detected_services = self.cloud_sync.detect_cloud_services()

    def _create_setup_content(self):
        """建立設定內容"""
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 標題
        title_label = tk.Label(
            main_frame,
            text="🌤️ 一鍵雲端同步設定",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Microsoft JhengHei', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # 說明
        info_label = tk.Label(
            main_frame,
            text="讓您的案件資料在多台電腦間自動同步\n完全免費，設定超簡單！",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            justify='center'
        )
        info_label.pack(pady=(0, 20))

        if not self.detected_services:
            self._create_no_service_content(main_frame)
        else:
            self._create_service_selection(main_frame)

    def _create_no_service_content(self, parent):
        """沒有偵測到雲端服務時的內容"""
        no_service_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        no_service_frame.pack(fill='both', expand=True)

        warning_label = tk.Label(
            no_service_frame,
            text="❌ 未偵測到已安裝的雲端服務",
            bg=AppConfig.COLORS['window_bg'],
            fg='red',
            font=AppConfig.FONTS['button']
        )
        warning_label.pack(pady=20)

        info_text = """
請先安裝以下任一雲端服務：

💾 OneDrive (5GB免費)
💿 Google Drive (15GB免費)
💽 Dropbox (2GB免費)

安裝完成後重新開啟此對話框
        """

        info_label = tk.Label(
            no_service_frame,
            text=info_text,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            justify='left'
        )
        info_label.pack(pady=20)

        # 關閉按鈕
        close_btn = tk.Button(
            no_service_frame,
            text='知道了',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12
        )
        close_btn.pack(pady=20)

    def _create_service_selection(self, parent):
        """建立雲端服務選擇"""
        selection_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        selection_frame.pack(fill='both', expand=True)

        success_label = tk.Label(
            selection_frame,
            text="✅ 偵測到可用的雲端服務",
            bg=AppConfig.COLORS['window_bg'],
            fg='green',
            font=AppConfig.FONTS['button']
        )
        success_label.pack(pady=(0, 20))

        # 服務選擇
        self.selected_service = tk.StringVar()

        for provider_id, service_info in self.detected_services.items():
            service_frame = tk.Frame(selection_frame, bg=AppConfig.COLORS['window_bg'])
            service_frame.pack(fill='x', pady=5)

            radio = tk.Radiobutton(
                service_frame,
                text=f"📁 {service_info['name']} - {service_info['path']}",
                variable=self.selected_service,
                value=provider_id,
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['text'],
                selectcolor=AppConfig.COLORS['window_bg']
            )
            radio.pack(anchor='w')

            # 預設選擇第一個
            if not self.selected_service.get():
                self.selected_service.set(provider_id)

        # 按鈕區域
        button_frame = tk.Frame(selection_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=30)

        # 設定按鈕
        setup_btn = tk.Button(
            button_frame,
            text='🚀 開始設定',
            command=self._setup_cloud_sync,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12,
            height=2
        )
        setup_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='稍後設定',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12,
            height=2
        )
        cancel_btn.pack(side='left', padx=5)

    def _setup_cloud_sync(self):
        """設定雲端同步"""
        if not self.selected_service.get():
            UnifiedMessageDialog.show_warning(self.window, "請選擇一個雲端服務")
            return

        provider_id = self.selected_service.get()
        service_name = self.detected_services[provider_id]['name']

        try:
            # 執行設定
            success = self.cloud_sync.setup_cloud_sync(provider_id)

            if success:
                UnifiedMessageDialog.show_success(
                    self.window,
                    f"🎉 {service_name} 同步已設定完成！\n\n"
                    f"您的案件資料現在會自動同步到雲端\n"
                    f"在其他電腦上安裝相同程式即可存取相同資料"
                )

                # 執行回調
                if self.on_setup_complete:
                    self.on_setup_complete(provider_id, service_name)

                self.close()
            else:
                UnifiedMessageDialog.show_error(self.window, "雲端同步設定失敗，請重試")

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"設定過程中發生錯誤：{str(e)}")

    @staticmethod
    def show_setup_dialog(parent, on_setup_complete: Optional[Callable] = None):
        """顯示雲端設定對話框"""
        dialog = CloudSetupDialog(parent, on_setup_complete)
        dialog.window.wait_window()