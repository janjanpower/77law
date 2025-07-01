# utils/topmost_date_entry.py
"""
修正版自定義DateEntry控件，確保日曆展開時保持置頂
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
    """置頂日期選擇控件包裝器 - 修正版"""

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
        self.calendar_window_id = None  # 🔥 新增：層級管理系統的視窗ID
        self.is_monitoring = False
        self.monitor_job = None

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
        """創建tkcalendar控件 - 修正版"""
        self.date_entry = BaseDateEntry(self.parent, **kwargs)

        # 🔥 修正：只綁定必要的事件，避免與內建事件衝突
        # 使用 <ButtonRelease-1> 而非 <Button-1>，避免阻擋原始點擊事件
        self.date_entry.bind('<ButtonRelease-1>', self._on_date_entry_activated)
        self.date_entry.bind('<KeyRelease-Return>', self._on_date_entry_activated)
        self.date_entry.bind('<KeyRelease-space>', self._on_date_entry_activated)

        # 🔥 修正：使用更簡單的監控機制
        self._start_monitoring()

    def _create_fallback_widget(self, kwargs):
        """創建降級Entry控件"""
        self.date_entry = tk.Entry(
            self.parent,
            width=kwargs.get('width', 12),
            font=kwargs.get('font', AppConfig.FONTS['text'])
        )

    def _on_date_entry_activated(self, event=None):
        """🔥 修正：日期控件激活事件處理"""
        # 延遲處理，確保tkcalendar的內建事件先執行
        self.parent.after(100, self._check_for_calendar)
        self.parent.after(300, self._check_for_calendar)
        self.parent.after(500, self._check_for_calendar)

    def _start_monitoring(self):
        """🔥 修正：開始監控日曆視窗"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self._monitor_calendar()

    def _stop_monitoring(self):
        """🔥 新增：停止監控"""
        self.is_monitoring = False
        if self.monitor_job:
            try:
                self.parent.after_cancel(self.monitor_job)
            except:
                pass
            self.monitor_job = None

    def _monitor_calendar(self):
        """🔥 修正：監控日曆視窗狀態"""
        if not self.is_monitoring:
            return

        try:
            self._check_for_calendar()
            # 繼續監控
            self.monitor_job = self.parent.after(200, self._monitor_calendar)
        except tk.TclError:
            # 控件已銷毀，停止監控
            self._stop_monitoring()

    def _check_for_calendar(self):
        """🔥 修正：簡化的日曆檢測方法"""
        if not self.date_entry:
            return

        # 🔥 修正：使用更簡單可靠的檢測方法
        root = self.parent.winfo_toplevel()

        try:
            # 獲取所有Toplevel視窗
            for widget in root.winfo_children():
                if isinstance(widget, tk.Toplevel) and self._is_calendar_window(widget):
                    if self.calendar_window != widget:
                        self._setup_calendar_topmost(widget)
                    return

            # 🔥 新增：檢查是否有新出現的Toplevel視窗
            for child in tk._default_root.winfo_children() if tk._default_root else []:
                if isinstance(child, tk.Toplevel) and self._is_calendar_window(child):
                    if self.calendar_window != child:
                        self._setup_calendar_topmost(child)
                    return

        except Exception as e:
            print(f"日曆檢測時發生錯誤: {e}")

    def _is_calendar_window(self, window):
        """🔥 修正：簡化的日曆視窗判斷方法"""
        try:
            if not window or not window.winfo_exists():
                return False

            # 檢查視窗大小（日曆通常是固定大小）
            width = window.winfo_width()
            height = window.winfo_height()
            if not (150 <= width <= 350 and 150 <= height <= 350):
                return False

            # 檢查是否包含Calendar控件
            def contains_calendar_widget(widget):
                try:
                    class_name = widget.winfo_class().lower()
                    if 'calendar' in class_name:
                        return True
                    for child in widget.winfo_children():
                        if contains_calendar_widget(child):
                            return True
                    return False
                except:
                    return False

            return contains_calendar_widget(window)
        except:
            return False

    def _setup_calendar_topmost(self, calendar_window):
        """🔥 修正：設定日曆視窗置頂（整合層級管理系統）"""
        if self.calendar_window == calendar_window:
            return  # 已經處理過

        self.calendar_window = calendar_window
        print(f"找到日曆視窗，設定置頂: {calendar_window}")

        try:
            # 🔥 整合層級管理系統
            try:
                from utils.window_hierarchy_manager import register_calendar_popup
                self.calendar_window_id = register_calendar_popup(calendar_window)
            except ImportError:
                # 降級處理：直接設定置頂
                calendar_window.attributes('-topmost', True)
                calendar_window.lift()

            # 確保父視窗也保持置頂
            if self.parent_window:
                self.parent_window.attributes('-topmost', True)
                self.parent_window.lift()

            # 🔥 修正：簡化事件綁定
            calendar_window.bind('<Destroy>', self._on_calendar_destroy, add='+')

        except Exception as e:
            print(f"設定日曆置頂時發生錯誤: {e}")

    def _on_calendar_destroy(self, event=None):
        """🔥 修正：日曆視窗關閉事件"""
        print("日曆視窗已關閉")
        self.calendar_window = None

        # 確保父視窗重新獲得焦點和置頂
        if self.parent_window:
            try:
                self.parent_window.after(50, self._restore_parent_focus)
            except:
                pass

    def _restore_parent_focus(self):
        """恢復父視窗焦點"""
        try:
            if self.parent_window and self.parent_window.winfo_exists():
                self.parent_window.attributes('-topmost', True)
                self.parent_window.lift()
                self.parent_window.focus_force()
        except Exception as e:
            print(f"恢復父視窗焦點時發生錯誤: {e}")

    # 🔥 修正：代理方法，讓此類表現得像DateEntry
    def get(self):
        """獲取日期字符串"""
        if self.date_entry:
            return self.date_entry.get()
        return ""

    def get_date(self):
        """獲取日期對象（僅tkcalendar可用）"""
        if CALENDAR_AVAILABLE and hasattr(self.date_entry, 'get_date'):
            try:
                return self.date_entry.get_date()
            except:
                return None
        return None

    def set_date(self, date):
        """設定日期"""
        if CALENDAR_AVAILABLE and hasattr(self.date_entry, 'set_date'):
            try:
                self.date_entry.set_date(date)
            except Exception as e:
                print(f"設定日期失敗: {e}")
        elif self.date_entry:
            try:
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, str(date))
            except Exception as e:
                print(f"設定日期失敗: {e}")

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
        """🔥 修正：銷毀控件"""
        # 停止監控
        self._stop_monitoring()

        # 銷毀日曆視窗
        if self.calendar_window:
            try:
                self.calendar_window.destroy()
            except:
                pass
            self.calendar_window = None

        # 銷毀主控件
        if self.date_entry:
            try:
                self.date_entry.destroy()
            except:
                pass
            self.date_entry = None


class TopmostDateEntryManager:
    """🔥 修正：置頂日期控件管理器 - 單例模式"""

    _instance = None
    _active_entries = []

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
        entry = TopmostDateEntry(parent, parent_window, **kwargs)
        cls._active_entries.append(entry)
        return entry

    @classmethod
    def cleanup_destroyed_entries(cls):
        """🔥 新增：清理已銷毀的控件"""
        cls._active_entries = [entry for entry in cls._active_entries
                              if entry.date_entry and hasattr(entry.date_entry, 'winfo_exists')]

    @classmethod
    def ensure_all_calendars_topmost(cls, target_window):
        """🔥 修正：確保所有日曆控件置頂"""
        try:
            cls.cleanup_destroyed_entries()

            # 檢查所有活動的日期控件
            for entry in cls._active_entries:
                if entry.calendar_window and entry.calendar_window.winfo_exists():
                    entry.calendar_window.attributes('-topmost', True)
                    entry.calendar_window.lift()

            # 確保目標視窗置頂
            if target_window and target_window.winfo_exists():
                target_window.attributes('-topmost', True)
                target_window.lift()

        except Exception as e:
            print(f"確保日曆置頂時發生錯誤: {e}")