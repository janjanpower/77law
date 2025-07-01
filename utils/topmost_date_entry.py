# utils/topmost_date_entry.py
"""
自定義DateEntry控件，確保日曆展開時保持置頂
統一的日期控件解決方案，避免重複代碼
"""

import tkinter as tk
from typing import Optional, Callable
from config.settings import AppConfig

try:
    from tkcalendar import DateEntry as BaseDateEntry
    CALENDAR_AVAILABLE = True
except ImportError:
    print("警告：tkcalendar 套件未安裝，請執行：pip install tkcalendar")
    CALENDAR_AVAILABLE = False
    BaseDateEntry = None

class TopmostDateEntry:
    """置頂日期選擇控件包裝器"""

    def __init__(self, parent, parent_window=None, **kwargs):
        """
        初始化置頂日期控件

        Args:
            parent: 父控件
            parent_window: 父視窗（用於確保置頂）
            **kwargs: DateEntry的其他參數
        """
        self.parent = parent
        self.parent_window = parent_window
        self.date_entry = None
        self.calendar_window = None
        self.original_focus_callback = None

        # 設定預設參數
        default_kwargs = {
            'width': 12,
            'background': 'darkblue',
            'foreground': 'white',
            'borderwidth': 2,
            'date_pattern': 'yyyy-mm-dd',
            'font': AppConfig.FONTS['text']
        }
        default_kwargs.update(kwargs)

        if CALENDAR_AVAILABLE:
            self._create_calendar_widget(default_kwargs)
        else:
            self._create_fallback_widget(default_kwargs)

    def _create_calendar_widget(self, kwargs):
        """創建tkcalendar控件"""
        self.date_entry = BaseDateEntry(self.parent, **kwargs)

        # 監聽日曆展開事件
        self.date_entry.bind('<Button-1>', self._on_date_entry_click)
        self.date_entry.bind('<Return>', self._on_date_entry_click)
        self.date_entry.bind('<space>', self._on_date_entry_click)

        # 定期檢查日曆是否展開
        self._check_calendar_window()

    def _create_fallback_widget(self, kwargs):
        """創建降級Entry控件"""
        self.date_entry = tk.Entry(
            self.parent,
            width=kwargs.get('width', 12),
            font=kwargs.get('font', AppConfig.FONTS['text'])
        )

    def _on_date_entry_click(self, event=None):
        """日期控件點擊事件處理"""
        # 延遲檢查日曆視窗，確保有時間創建
        self.parent.after(100, self._find_and_setup_calendar)

    def _check_calendar_window(self):
        """定期檢查日曆視窗狀態"""
        try:
            self._find_and_setup_calendar()
            # 每100ms檢查一次
            self.parent.after(100, self._check_calendar_window)
        except tk.TclError:
            # 控件已銷毀，停止檢查
            pass

    def _find_and_setup_calendar(self):
        """查找並設定日曆視窗置頂"""
        if not self.date_entry:
            return

        # 查找所有頂級視窗
        for widget in self.parent.winfo_toplevel().winfo_children():
            if isinstance(widget, tk.Toplevel):
                # 檢查是否為日曆視窗
                if self._is_calendar_window(widget):
                    self._setup_calendar_topmost(widget)
                    break

    def _is_calendar_window(self, window):
        """判斷是否為日曆視窗"""
        try:
            # tkcalendar的日曆視窗特徵：
            # 1. 沒有標題或標題為空
            # 2. overrideredirect為True
            # 3. 包含Calendar控件
            if not hasattr(window, 'winfo_class'):
                return False

            # 檢查是否有Calendar子控件
            for child in window.winfo_children():
                if hasattr(child, 'winfo_class') and 'Calendar' in str(child.winfo_class()):
                    return True

            return False
        except:
            return False

    def _setup_calendar_topmost(self, calendar_window):
        """設定日曆視窗置頂"""
        if self.calendar_window == calendar_window:
            return  # 已經處理過

        self.calendar_window = calendar_window

        try:
            # 設定置頂
            calendar_window.attributes('-topmost', True)
            calendar_window.lift()

            # 確保父視窗也保持置頂
            if self.parent_window:
                self.parent_window.attributes('-topmost', True)
                self.parent_window.lift()

            # 監聽關閉事件
            calendar_window.bind('<Destroy>', self._on_calendar_destroy)
            calendar_window.bind('<FocusOut>', self._on_calendar_focus_out)

        except tk.TclError:
            pass

    def _on_calendar_destroy(self, event=None):
        """日曆視窗關閉事件"""
        self.calendar_window = None

        # 確保父視窗重新獲得焦點和置頂
        if self.parent_window:
            try:
                self.parent_window.after(50, self._restore_parent_focus)
            except:
                pass

    def _on_calendar_focus_out(self, event=None):
        """日曆失去焦點時的處理"""
        # 延遲檢查，避免頻繁觸發
        if self.calendar_window:
            self.calendar_window.after(100, self._check_calendar_focus)

    def _check_calendar_focus(self):
        """檢查日曆焦點狀態"""
        if not self.calendar_window:
            return

        try:
            # 如果日曆視窗仍存在但失去焦點，重新設定置頂
            if self.calendar_window.winfo_exists():
                self.calendar_window.attributes('-topmost', True)
                self.calendar_window.lift()
        except:
            pass

    def _restore_parent_focus(self):
        """恢復父視窗焦點"""
        try:
            if self.parent_window and self.parent_window.winfo_exists():
                self.parent_window.attributes('-topmost', True)
                self.parent_window.lift()
                self.parent_window.focus_force()
        except:
            pass

    # 代理方法，讓此類表現得像DateEntry
    def get(self):
        """獲取日期字符串"""
        if self.date_entry:
            return self.date_entry.get()
        return ""

    def get_date(self):
        """獲取日期對象（僅tkcalendar可用）"""
        if CALENDAR_AVAILABLE and hasattr(self.date_entry, 'get_date'):
            return self.date_entry.get_date()
        return None

    def set_date(self, date):
        """設定日期"""
        if CALENDAR_AVAILABLE and hasattr(self.date_entry, 'set_date'):
            self.date_entry.set_date(date)
        elif self.date_entry:
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, str(date))

    def grid(self, **kwargs):
        """Grid佈局"""
        if self.date_entry:
            self.date_entry.grid(**kwargs)

    def pack(self, **kwargs):
        """Pack佈局"""
        if self.date_entry:
            self.date_entry.pack(**kwargs)

    def place(self, **kwargs):
        """Place佈局"""
        if self.date_entry:
            self.date_entry.place(**kwargs)

    def bind(self, sequence, func):
        """綁定事件"""
        if self.date_entry:
            self.date_entry.bind(sequence, func)

    def focus_set(self):
        """設定焦點"""
        if self.date_entry:
            self.date_entry.focus_set()

    def destroy(self):
        """銷毀控件"""
        if self.calendar_window:
            try:
                self.calendar_window.destroy()
            except:
                pass
        if self.date_entry:
            self.date_entry.destroy()


class TopmostDateEntryManager:
    """置頂日期控件管理器 - 單例模式"""

    _instance = None
    _active_calendars = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True

    @classmethod
    def create_date_entry(cls, parent, parent_window=None, **kwargs):
        """
        統一創建置頂日期控件的入口

        Args:
            parent: 父控件
            parent_window: 父視窗
            **kwargs: DateEntry參數

        Returns:
            TopmostDateEntry: 置頂日期控件實例
        """
        return TopmostDateEntry(parent, parent_window, **kwargs)

    @classmethod
    def ensure_all_calendars_topmost(cls, target_window):
        """確保所有日曆控件置頂"""
        try:
            for widget in target_window.winfo_toplevel().winfo_children():
                if isinstance(widget, tk.Toplevel):
                    # 檢查是否為日曆視窗
                    for child in widget.winfo_children():
                        if hasattr(child, 'winfo_class') and 'Calendar' in str(child.winfo_class()):
                            widget.attributes('-topmost', True)
                            widget.lift()
                            break
        except:
            pass