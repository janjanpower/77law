import tkinter as tk
from tkinter import ttk, messagebox
from views.base_window import BaseWindow

class ConfirmDialog(BaseWindow):
    """確認對話框"""

    def __init__(self, parent, title="確認", message="確定要執行此操作嗎？"):
        self.result = False
        self.message = message

        super().__init__(
            title=title,
            width=400,
            height=200,
            resizable=False,
            parent=parent
        )

        self._create_dialog_content()

    def _create_dialog_content(self):
        """建立對話框內容"""
        # 訊息標籤
        message_label = tk.Label(
            self.content_frame,
            text=self.message,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Arial', 12),
            wraplength=350
        )
        message_label.pack(expand=True, pady=20)

        # 按鈕
        self.create_dialog_buttons(
            self.content_frame,
            self._on_ok,
            self._on_cancel
        )

    def _on_ok(self):
        """確定按鈕事件"""
        self.result = True
        self.close()

    def _on_cancel(self):
        """取消按鈕事件"""
        self.result = False
        self.close()

    @staticmethod
    def ask(parent, title="確認", message="確定要執行此操作嗎？"):
        """靜態方法：顯示確認對話框"""
        dialog = ConfirmDialog(parent, title, message)
        dialog.window.wait_window()
        return dialog.result


class MessageDialog(BaseWindow):
    """訊息對話框"""

    def __init__(self, parent, title="訊息", message="", dialog_type="info"):
        self.message = message
        self.dialog_type = dialog_type

        super().__init__(
            title=title,
            width=400,
            height=180,
            resizable=False,
            parent=parent
        )

        self._create_dialog_content()

    def _create_dialog_content(self):
        """建立對話框內容"""
        # 圖示和訊息區域
        content_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        content_frame.pack(expand=True, fill='both', padx=20, pady=20)

        # 訊息標籤
        message_label = tk.Label(
            content_frame,
            text=self.message,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Microsoft JhengHei', 12),
            wraplength=350,
            justify='center'
        )
        message_label.pack(expand=True)

        # 確定按鈕
        ok_btn = self.create_button(
            self.content_frame,
            '確定',
            self.close,
            'Dialog.TButton'
        )
        ok_btn.pack(pady=(0, 10))

    @staticmethod
    def show(parent, title="訊息", message="", dialog_type="info"):
        """靜態方法：顯示訊息對話框"""
        dialog = MessageDialog(parent, title, message, dialog_type)
        dialog.window.wait_window()
