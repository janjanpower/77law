#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
from config.settings import AppConfig
from utils.window_manager import (
    WindowManager, WindowPriority, register_window,
    unregister_window, set_modal, bring_to_front
)
import uuid

class ConfirmDialog:
    """確認對話框 - 修正版本"""

    def __init__(self, parent, title="確認", message="確定要執行此操作嗎？",
                 confirm_text="確定", cancel_text="取消"):
        self.result = False
        self.message = message
        self.confirm_text = confirm_text  # 🔥 新增：儲存確認按鈕文字
        self.cancel_text = cancel_text    # 🔥 新增：儲存取消按鈕文字
        self.parent = parent
        self.drag_data = {"x": 0, "y": 0}

        # 建立視窗
        self.window = tk.Toplevel(parent)
        self._setup_window(title)
        self._create_dialog_content()  # 🔥 修正：不需要傳入參數，使用實例變數

    def _setup_window(self, title):
        """設定視窗基本屬性"""
        self.window.title(f"{AppConfig.WINDOW_TITLES.get('main', '案件管理系統')} - {title}")
        self.window.geometry("400x180")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.resizable(False, False)

        # 置頂設定
        if self.parent:
            self.window.transient(self.parent)
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
                self.window.attributes('-topmost', True)
                self.window.after(200, lambda: self.window.attributes('-topmost', False))
        except tk.TclError:
            pass

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 200
        y = (self.window.winfo_screenheight() // 2) - 100
        self.window.geometry(f"400x180+{x}+{y}")

    def _create_dialog_content(self):
        """建立對話框內容 - 修正版本"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 標題列
        title_frame = tk.Frame(
            main_frame,
            bg=AppConfig.COLORS.get('title_bg', '#2c3e50'),
            height=30
        )
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 標題標籤
        title_label = tk.Label(
            title_frame,
            text="確認",
            bg=AppConfig.COLORS.get('title_bg', '#2c3e50'),
            fg=AppConfig.COLORS.get('title_fg', 'white'),
            font=AppConfig.FONTS.get('title', ('Arial', 10, 'bold'))
        )
        title_label.pack(side='left', padx=10, pady=5)

        # 關閉按鈕
        close_btn = tk.Button(
            title_frame,
            text="✕",
            command=self._on_cancel,
            bg=AppConfig.COLORS.get('title_bg', '#2c3e50'),
            fg=AppConfig.COLORS.get('title_fg', 'white'),
            font=('Arial', 10),
            bd=0,
            width=3,
            height=1
        )
        close_btn.pack(side='right', padx=5, pady=5)

        # 設定拖曳功能
        self._setup_drag(title_frame, title_label)

        # 內容區域
        content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)

        # 訊息標籤
        message_label = tk.Label(
            content_frame,
            text=self.message,  # 🔥 修正：使用實例變數
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS.get('text', ('Arial', 9)),
            wraplength=350,
            justify='center'
        )
        message_label.pack(expand=True, pady=10)

        # 按鈕區域
        button_frame = tk.Frame(content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=(10, 0))

        # 確定按鈕
        ok_btn = tk.Button(
            button_frame,
            text=self.confirm_text,  # 🔥 修正：使用實例變數
            command=self._on_ok,
            bg=AppConfig.COLORS.get('button_bg', '#007ACC'),
            fg=AppConfig.COLORS.get('button_fg', 'white'),
            font=AppConfig.FONTS.get('button', ('Arial', 9)),
            width=10
        )
        ok_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text=self.cancel_text,  # 🔥 修正：使用實例變數
            command=self._on_cancel,
            bg='#757575',
            fg='white',
            font=AppConfig.FONTS.get('button', ('Arial', 9)),
            width=10
        )
        cancel_btn.pack(side='left', padx=5)

        # 設定預設焦點和快捷鍵
        ok_btn.focus_set()
        self.window.bind('<Return>', lambda e: self._on_ok())
        self.window.bind('<Escape>', lambda e: self._on_cancel())

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
    def ask(parent, title="確認", message="確定要執行此操作嗎？",
            confirm_text="確定", cancel_text="取消"):
        """靜態方法：顯示確認對話框 - 修正版本"""
        try:
            dialog = ConfirmDialog(parent, title, message, confirm_text, cancel_text)
            dialog.window.wait_window()
            return dialog.result
        except Exception as e:
            print(f"顯示確認對話框失敗: {e}")
            # 回退至標準對話框
            import tkinter.messagebox as messagebox
            return messagebox.askyesno(title, message)

class UnifiedConfirmDialog:
    """統一樣式的確認對話框 - 簡化版本"""

    def __init__(self, parent, title="確認", message="", confirm_text="是", cancel_text="否"):
        self.result = None
        self.parent = parent
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.drag_data = {"x": 0, "y": 0}

        # 建立視窗
        self.window = tk.Toplevel(parent)
        self.window.withdraw()  # 先隱藏

        self._setup_window(title)
        self._create_dialog_content()

        # 延遲顯示確保正確設定置頂
        self.window.after(10, self._show_dialog_safely)

    def _setup_window(self, title):
        """設定視窗基本屬性"""
        self.window.title(f"{AppConfig.WINDOW_TITLES['main']} - {title}")
        self.window.geometry("450x200")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.resizable(False, False)

        if self.parent:
            self.window.transient(self.parent)

        # 置中顯示
        self._center_window()
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 225
        y = (self.window.winfo_screenheight() // 2) - 100
        self.window.geometry(f"450x200+{x}+{y}")

    def _show_dialog_safely(self):
        """安全顯示對話框並確保置頂"""
        try:
            if self.window.winfo_exists():
                self.window.deiconify()
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.grab_set()
                self.window.focus_force()
        except tk.TclError as e:
            print(f"顯示確認對話框失敗: {e}")

    def _create_dialog_content(self):
        """建立對話框內容"""
        # 主框架
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 標題列
        title_frame = tk.Frame(main_frame, bg=AppConfig.COLORS.get('title_bg', '#2c3e50'), height=30)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 標題
        title_label = tk.Label(title_frame, text="確認", bg=AppConfig.COLORS.get('title_bg', '#2c3e50'),
                              fg=AppConfig.COLORS.get('title_fg', 'white'), font=AppConfig.FONTS.get('title', ('Arial', 10, 'bold')))
        title_label.pack(side='left', padx=10, pady=5)

        # 內容區域
        content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)

        # 訊息
        message_label = tk.Label(content_frame, text=self.message, bg=AppConfig.COLORS['window_bg'],
                                fg=AppConfig.COLORS['text_color'], font=AppConfig.FONTS['text'],
                                wraplength=350, justify='center')
        message_label.pack(expand=True, pady=(10, 0))

        # 按鈕區域
        button_frame = tk.Frame(content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=(15, 0))

        # 確定按鈕
        confirm_btn = tk.Button(button_frame, text=self.confirm_text, command=self._on_confirm,
                               bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg'],
                               font=AppConfig.FONTS['button'], width=10, height=1)
        confirm_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(button_frame, text=self.cancel_text, command=self._on_cancel,
                              bg='#757575', fg='white', font=AppConfig.FONTS['button'],
                              width=10, height=1)
        cancel_btn.pack(side='left', padx=5)

        # 設定焦點和快捷鍵
        confirm_btn.focus_set()
        self.window.bind('<Return>', lambda e: self._on_confirm())
        self.window.bind('<Escape>', lambda e: self._on_cancel())

    def _on_confirm(self):
        """確認按鈕事件"""
        self.result = True
        self._close_dialog_safely()

    def _on_cancel(self):
        """取消按鈕事件"""
        self.result = False
        self._close_dialog_safely()

    def _close_dialog_safely(self):
        """安全關閉對話框"""
        try:
            if self.window.winfo_exists():
                self.window.grab_release()
                if self.parent and self.parent.winfo_exists():
                    self.parent.focus_force()
                    self.parent.lift()
                self.window.destroy()
        except tk.TclError:
            pass

    def close(self):
        """關閉對話框 - 相容性方法"""
        self._close_dialog_safely()

    @staticmethod
    def ask(parent, title="確認", message="確定要執行此操作嗎？", confirm_text="確定", cancel_text="取消"):
        """靜態方法：顯示確認對話框"""
        dialog = UnifiedConfirmDialog(parent, title, message, confirm_text, cancel_text)
        dialog.window.wait_window()
        return dialog.result

    @staticmethod
    def ask_stage_update(parent, stage_name):
        """專門處理階段更新確認的靜態方法"""
        message = f"階段「{stage_name}」已存在，是否要更新日期和備註？"
        dialog = UnifiedConfirmDialog(parent, "確認更新", message, "是", "否")
        dialog.window.wait_window()
        return dialog.result

    @staticmethod
    def ask_file_overwrite(parent, filename):
        """檔案覆蓋確認"""
        message = f"檔案「{filename}」已存在，是否要覆蓋？"
        dialog = UnifiedConfirmDialog(parent, "檔案覆蓋確認", message, "覆蓋", "跳過")
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
        # 取得對話框樣式
        title_text, icon = self._get_dialog_style()

        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 標題列
        title_frame = tk.Frame(
            main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=30
        )
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 標題圖示
        icon_label = tk.Label(
            title_frame,
            text=icon,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 14)
        )
        icon_label.pack(side='left', padx=10, pady=5)

        # 標題標籤
        title_label = tk.Label(
            title_frame,
            text=title_text,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        title_label.pack(side='left', pady=5)

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
        close_btn.pack(side='right', padx=5)

        # 設定拖曳功能
        self._setup_drag(title_frame, title_label, icon_label)

        # 內容區域
        content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)

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
    def show(parent, title="訊息", message="", dialog_type="info"):
        """靜態方法：顯示訊息對話框"""
        dialog = MessageDialog(parent, title, message, dialog_type)
        dialog.window.wait_window()


class UnifiedMessageDialog:
    """統一樣式的訊息對話框（含陰影、動態尺寸）"""

    def __init__(self, parent, title="訊息", message="", dialog_type="info"):
        import tkinter.font as tkfont

        self.parent = parent
        self.message = message or ""
        self.dialog_type = dialog_type
        self.result = None

        # 預估寬度：依文字長度決定 (最小320，最大560)
        base_font = tkfont.Font(family=AppConfig.FONTS.get('text', ('Arial', 10))[0],
                                size=AppConfig.FONTS.get('text', ('Arial', 10))[1])
        text_px = base_font.measure(self.message) if self.message else 320
        width = min(560, max(320, 40 + text_px // 1))  # 預估，但後續會再 fit
        height = 180

        # 陰影層（在主窗右下 6px）
        self.shadow = tk.Toplevel(parent)
        try:
            self.shadow.overrideredirect(True)
        except Exception:
            pass
        self.shadow.geometry(f"{width}x{height}+0+0")
        self.shadow.configure(bg="#000000")
        try:
            self.shadow.attributes("-alpha", 0.25)
        except Exception:
            pass

        # 主對話框
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        try:
            self.window.overrideredirect(True)
        except Exception:
            pass
        self.window.configure(bg=AppConfig.COLORS['window_bg'])

        # 位置（置中）
        self._place_center(width, height)
        self._place_shadow()

        # 標題列
        title_bar = tk.Frame(self.window, bg=AppConfig.COLORS.get('title_bg', '#2c3e50'), height=32)
        title_bar.pack(fill='x')
        self._enable_drag(title_bar)

        icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(self.dialog_type, "ℹ️")
        tk.Label(title_bar, text=icon, bg=title_bar['bg'],
                 fg=AppConfig.COLORS.get('title_fg', 'white'),
                 font=('Arial', 12, 'bold')).pack(side='left', padx=10)
        tk.Label(title_bar, text=title, bg=title_bar['bg'],
                 fg=AppConfig.COLORS.get('title_fg', 'white'),
                 font=AppConfig.FONTS.get('title', ('Arial', 10, 'bold'))).pack(side='left')

        # 內容
        body = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        body.pack(fill='both', expand=True, padx=16, pady=12)

        msg = tk.Label(
            body, text=self.message, bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS.get('text', ('Arial', 10)), justify='left', wraplength=width - 48
        )
        msg.pack(fill='both', expand=True)

        btn = tk.Button(
            body, text="確定", command=self._close,
            bg=AppConfig.COLORS.get('button_bg', '#007ACC'),
            fg=AppConfig.COLORS.get('button_fg', 'white'),
            font=AppConfig.FONTS.get('button', ('Arial', 9)), width=10
        )
        btn.pack(pady=(8, 2))

        self.window.deiconify()
        self.window.lift(parent)
        try:
            self.window.grab_set()
        except Exception:
            pass
        self.window.after(10, self._fit_to_text, msg)

        # 關閉行為
        self.window.bind('<Escape>', lambda e: self._close())

    def _place_center(self, w, h):
        self.window.update_idletasks()
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

    def _place_shadow(self):
        # 陰影位置：主窗右下 6px
        try:
            self.window.update_idletasks()
            x = self.window.winfo_x() + 6
            y = self.window.winfo_y() + 6
            w = self.window.winfo_width()
            h = self.window.winfo_height()
            self.shadow.geometry(f"{w}x{h}+{x}+{y}")
            self.shadow.lift()
            self.window.lift()
        except Exception:
            pass

    def _fit_to_text(self, msg_label):
        # 依內容重新計算尺寸與 wraplength
        msg_label.update_idletasks()
        req_w = min(560, max(320, msg_label.winfo_reqwidth() + 48))
        req_h = max(160, msg_label.winfo_reqheight() + 120)
        self._place_center(req_w, req_h)
        try:
            msg_label.config(wraplength=req_w - 48)
        except Exception:
            pass
        self._place_shadow()

    def _enable_drag(self, widget):
        drag = {"x": 0, "y": 0}
        widget.bind("<Button-1>", lambda e: drag.update(x=e.x, y=e.y))
        def on_drag(e):
            nx = self.window.winfo_x() + (e.x - drag["x"])
            ny = self.window.winfo_y() + (e.y - drag["y"])
            self.window.geometry(f"+{nx}+{ny}")
            self._place_shadow()
        widget.bind("<B1-Motion>", on_drag)

    def _close(self):
        try:
            self.window.grab_release()
        except Exception:
            pass
        try:
            self.window.destroy()
        finally:
            try: self.shadow.destroy()
            except Exception: pass


    def _setup_window(self, title):
        """設定視窗基本屬性"""
        self.window.title(f"{AppConfig.WINDOW_TITLES['main']} - {title}")
        self.window.geometry("400x200")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.resizable(False, False)

        # 設定 transient
        if self.parent:
            self.window.transient(self.parent)

        # 置中顯示
        self._center_window()

        # 綁定關閉事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_confirm)

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 200
        y = (self.window.winfo_screenheight() // 2) - 100
        self.window.geometry(f"400x200+{x}+{y}")

    def _show_dialog_safely(self):
        """安全顯示對話框並確保置頂"""
        try:
            if self.window.winfo_exists():
                # 顯示視窗
                self.window.deiconify()

                # 強制置頂設定
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.grab_set()  # 設定模態
                self.window.focus_force()

                print(f"訊息對話框已顯示並置頂: {self.dialog_type}")

        except tk.TclError as e:
            print(f"顯示訊息對話框失敗: {e}")

    def _create_dialog_content(self):
        """建立對話框內容"""
        # 主框架
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 自定義標題列
        title_frame = tk.Frame(
            main_frame,
            bg=AppConfig.COLORS.get('title_bg', '#2c3e50'),
            height=30
        )
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # 取得對話框樣式
        title_text, icon_text = self._get_dialog_style()

        # 標題圖示
        icon_label = tk.Label(
            title_frame,
            text=icon_text,
            bg=AppConfig.COLORS.get('title_bg', '#2c3e50'),
            fg=AppConfig.COLORS.get('title_fg', 'white'),
            font=('Arial', 12)
        )
        icon_label.pack(side='left', padx=10, pady=5)

        # 標題文字
        title_label = tk.Label(
            title_frame,
            text=title_text,
            bg=AppConfig.COLORS.get('title_bg', '#2c3e50'),
            fg=AppConfig.COLORS.get('title_fg', 'white'),
            font=AppConfig.FONTS.get('title', ('Arial', 10, 'bold'))
        )
        title_label.pack(side='left', pady=5)

        # 設定拖曳功能
        self._setup_drag(title_frame, title_label, icon_label)

        # 內容區域
        content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)

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
        message_label.pack(expand=True, pady=(10, 0))

        # 🔥 關鍵修正：確保按鈕區域正確建立
        button_frame = tk.Frame(content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=(15, 0))

        # 🔥 關鍵修正：確定按鈕
        confirm_btn = tk.Button(
            button_frame,
            text="確定",
            command=self._on_confirm,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        confirm_btn.pack()

        # 設定焦點和快捷鍵
        confirm_btn.focus_set()
        self.window.bind('<Return>', lambda e: self._on_confirm())
        self.window.bind('<Escape>', lambda e: self._on_confirm())

        print(f"訊息對話框UI組件已建立完成，包含確定按鈕")

    def _get_dialog_style(self):
        """根據對話框類型取得樣式"""
        styles = {
            'info': ('資訊', 'ℹ️'),
            'success': ('成功', '✅'),
            'warning': ('警告', '⚠️'),
            'error': ('錯誤', '❌'),
        }
        return styles.get(self.dialog_type, ('訊息', 'ℹ️'))

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

    def _on_confirm(self):
        """確認按鈕事件"""
        self._close_dialog_safely()

    def _close_dialog_safely(self):
        """安全關閉對話框"""
        try:
            if self.window.winfo_exists():
                # 釋放模態
                self.window.grab_release()

                # 如果有父視窗，恢復其焦點
                if self.parent and self.parent.winfo_exists():
                    self.parent.focus_force()
                    self.parent.lift()

                # 關閉對話框
                self.window.destroy()
                print("訊息對話框已安全關閉")

        except tk.TclError:
            pass

    def close(self):
        """關閉對話框 - 相容性方法"""
        self._close_dialog_safely()

    @staticmethod
    def show_info(parent, message, title="資訊"):
        """顯示資訊對話框"""
        dialog = UnifiedMessageDialog(parent, title, message, "info")
        dialog.window.wait_window()

    @staticmethod
    def show_success(parent, message, title="成功"):
        dlg = UnifiedMessageDialog(parent, title, message, "success")
        dlg.window.wait_window()

    @staticmethod
    def show_warning(parent, message, title="警告"):
        dlg = UnifiedMessageDialog(parent, title, message, "warning")
        dlg.window.wait_window()

    @staticmethod
    def show_error(parent, message, title="錯誤"):
        dlg = UnifiedMessageDialog(parent, title, message, "error")
        dlg.window.wait_window()



