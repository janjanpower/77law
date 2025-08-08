# views/base_window.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正版BaseWindow - 智能置頂處理，解決下拉選單顯示問題
避免與ttk.Combobox等子控件衝突
"""

import tkinter as tk
from tkinter import ttk
from config.settings import AppConfig

class BaseWindow:
    """基礎視窗類別 - 智能置頂和控件相容性處理"""

    def __init__(self, title="視窗", width=600, height=400, resizable=True, parent=None):
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
        self.drag_data = {"x": 0, "y": 0}

        # 🔥 新增：智能置頂管理
        self.is_topmost = False
        self.is_modal = False
        self.smart_topmost = True  # 智能置頂模式
        self.combobox_widgets = []  # 追蹤combobox控件
        self.dropdown_open = False  # 下拉選單是否開啟
        self.monitor_job = None

        # 立即隱藏視窗，在所有設定完成前不顯示
        self.window.withdraw()

        # 設定視窗基本屬性
        self._setup_window()

        # 建立佈局（子類可覆寫）
        self._create_layout()

        # 如果有父視窗，設定為模態和置頂
        if parent:
            self.window.after(10, self._show_and_setup_modal)
        else:
            self.window.after(10, self._show_window)

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title(self.title)
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.resizable(self.resizable, self.resizable)
        self.window.overrideredirect(True)

        # 設定大小和位置
        self._center_window()

    def _center_window(self):
        """將視窗置中顯示"""
        x = (self.window.winfo_screenwidth() // 2) - (self.width // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.height // 2)
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _create_layout(self):
        """建立基礎佈局（子類應覆寫此方法）"""
        # 標題列
        self.title_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['title_bg'],
            height=40
        )
        self.title_frame.pack(fill='x')
        self.title_frame.pack_propagate(False)

        self.title_label = tk.Label(
            self.title_frame,
            text=self.title,
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        self.title_label.pack(side='left', padx=10, pady=10)

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
        self.close_btn.pack(side='right', padx=5, pady=5)

        # 設定拖曳
        self._setup_drag()

        # 內容區域
        self.content_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        self.content_frame.pack(fill='both', expand=True, padx=10, pady=10)

    def _setup_drag(self):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        self.title_frame.bind("<Button-1>", start_drag)
        self.title_frame.bind("<B1-Motion>", on_drag)
        self.title_label.bind("<Button-1>", start_drag)
        self.title_label.bind("<B1-Motion>", on_drag)

    def _show_window(self):
        """顯示視窗"""
        try:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
        except tk.TclError:
            pass

    def _show_and_setup_modal(self):
        """🔥 修正：顯示視窗並設定模態狀態，智能處理置頂"""
        try:
            self.window.deiconify()
            self.window.transient(self.parent)
            self.window.grab_set()

            # 🔥 修正：使用智能置頂模式
            if self.smart_topmost:
                self.window.lift()
                self.window.focus_force()
                self._start_smart_topmost_monitoring()
            else:
                # 傳統置頂模式（可能會有問題）
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()

            self.is_topmost = True
            self.is_modal = True

        except tk.TclError:
            pass

    def _start_smart_topmost_monitoring(self):
        """🔥 新增：智能置頂監控 - 避免與下拉選單衝突"""
        if not self.is_topmost or not self.window.winfo_exists():
            return

        try:
            # 檢查是否有下拉選單開啟
            if not self._check_dropdown_status():
                # 沒有下拉選單開啟時才置頂
                self.window.lift()
                # 短暫置頂後立即取消，避免阻擋下拉選單
                self.window.attributes('-topmost', True)
                self.window.after(100, lambda: self._reset_topmost())

            # 繼續監控
            self.monitor_job = self.window.after(300, self._start_smart_topmost_monitoring)

        except Exception as e:
            print(f"智能置頂監控錯誤: {e}")

    def _reset_topmost(self):
        """重置置頂狀態"""
        try:
            if self.window.winfo_exists():
                self.window.attributes('-topmost', False)
        except:
            pass

    def _check_dropdown_status(self):
        """🔥 新增：檢查是否有下拉選單開啟"""
        try:
            # 檢查是否有子視窗（可能是下拉選單）
            children = self.window.winfo_children()
            for child in children:
                if isinstance(child, ttk.Combobox):
                    # 檢查combobox是否有焦點（可能正在使用）
                    if str(self.window.focus_get()).startswith(str(child)):
                        return True

            # 檢查系統是否有其他頂層視窗（下拉選單）
            all_windows = self.window.tk.call('wm', 'stackorder', '.')
            current_top = all_windows[-1] if all_windows else None

            # 如果最頂層視窗不是我們的視窗，可能有下拉選單
            if current_top and current_top != str(self.window):
                return True

            return False

        except Exception as e:
            print(f"檢查下拉狀態錯誤: {e}")
            return False

    def register_combobox(self, combobox):
        """🔥 新增：註冊combobox控件，以便監控"""
        if combobox not in self.combobox_widgets:
            self.combobox_widgets.append(combobox)

            # 綁定事件
            combobox.bind('<Button-1>', self._on_combobox_click)
            combobox.bind('<<ComboboxSelected>>', self._on_combobox_selected)
            combobox.bind('<FocusIn>', self._on_combobox_focus_in)
            combobox.bind('<FocusOut>', self._on_combobox_focus_out)

    def _on_combobox_click(self, event):
        """Combobox點擊事件"""
        self.dropdown_open = True
        # 暫時停止置頂
        self._reset_topmost()

    def _on_combobox_selected(self, event):
        """Combobox選擇事件"""
        self.dropdown_open = False
        # 延遲恢復置頂
        self.window.after(200, self._restore_topmost)

    def _on_combobox_focus_in(self, event):
        """Combobox獲得焦點"""
        # 暫時停止置頂，準備可能的下拉
        self._reset_topmost()

    def _on_combobox_focus_out(self, event):
        """Combobox失去焦點"""
        self.dropdown_open = False
        # 延遲恢復置頂
        self.window.after(100, self._restore_topmost)

    def _restore_topmost(self):
        """恢復置頂狀態"""
        if self.is_topmost and self.window.winfo_exists() and not self.dropdown_open:
            try:
                self.window.lift()
            except:
                pass

    def ensure_topmost(self):
        """🔥 修正：確保視窗和所有日曆控件置頂"""
        try:
            if self.window.winfo_exists() and not self.dropdown_open:
                if self.smart_topmost:
                    self.window.lift()
                else:
                    self.window.attributes('-topmost', True)
                    self.window.lift()
                    self.window.focus_force()

                TopmostDateEntryManager.ensure_all_calendars_topmost(self.window)
        except:
            pass

    def create_topmost_date_entry(self, parent, **kwargs):
        """🔥 新增：創建置頂日期控件的便利方法"""
        return TopmostDateEntryManager.create_date_entry(
            parent,
            parent_window=self.window,
            **kwargs
        )

    def close(self):
        """關閉視窗"""
        try:
            self.is_topmost = False
            self.is_modal = False

            # 停止監控
            if self.monitor_job:
                self.window.after_cancel(self.monitor_job)
                self.monitor_job = None

            if self.window:
                if self.is_modal:
                    self.window.grab_release()
                self.window.destroy()
        except:
            pass


class EnhancedBaseWindow(BaseWindow):
    """增強版BaseWindow - 提供更多置頂功能"""

    def __init__(self, title="視窗", width=600, height=400, resizable=True, parent=None,
                 auto_topmost=True, monitor_interval=300):
        """
        初始化增強版基礎視窗

        Args:
            title: 視窗標題
            width: 視窗寬度
            height: 視窗高度
            resizable: 是否可調整大小
            parent: 父視窗
            auto_topmost: 是否自動維持置頂
            monitor_interval: 置頂監控間隔（毫秒）
        """
        self.auto_topmost = auto_topmost
        self.monitor_interval = monitor_interval
        self.focus_lost_count = 0  # 失去焦點次數

        super().__init__(title, width, height, resizable, parent)

        # 綁定焦點事件
        if auto_topmost:
            self._setup_focus_monitoring()

    def _setup_focus_monitoring(self):
        """設定焦點監控"""
        self.window.bind('<FocusIn>', self._on_focus_in)
        self.window.bind('<FocusOut>', self._on_focus_out)

    def _on_focus_in(self, event=None):
        """獲得焦點時處理"""
        self.focus_lost_count = 0
        if self.auto_topmost and not self.dropdown_open:
            self.ensure_topmost()

    def _on_focus_out(self, event=None):
        """失去焦點時處理"""
        self.focus_lost_count += 1

        # 如果頻繁失去焦點，可能有子視窗（如日曆）打開
        if self.focus_lost_count > 3 and self.auto_topmost:
            self.window.after(100, self._delayed_topmost_check)

    def _delayed_topmost_check(self):
        """延遲的置頂檢查"""
        if self.window.winfo_exists() and self.auto_topmost and not self.dropdown_open:
            self.ensure_topmost()


