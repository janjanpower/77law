# views/base_window.py
"""
增強版BaseWindow - 統一置頂處理和日期控件管理
避免重複代碼，提供一致的視窗行為
"""

import tkinter as tk
from config.settings import AppConfig
from utils.topmost_date_entry import TopmostDateEntryManager

class BaseWindow:
    """基礎視窗類別 - 統一置頂和日期控件處理"""

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

        # 置頂和模態狀態管理
        self.is_topmost = False
        self.is_modal = False

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
        """🔥 改進：顯示視窗並設定模態狀態，確保日曆置頂"""
        try:
            self.window.deiconify()
            self.window.transient(self.parent)
            self.window.grab_set()
            self.window.attributes('-topmost', True)
            self.window.lift()
            self.window.focus_force()

            self.is_topmost = True
            self.is_modal = True

            # 🔥 新增：確保所有日曆控件置頂
            TopmostDateEntryManager.ensure_all_calendars_topmost(self.window)

            # 🔥 新增：定期檢查並維持置頂狀態
            self._start_topmost_monitoring()

        except tk.TclError:
            pass

    def _start_topmost_monitoring(self):
        """🔥 新增：開始置頂狀態監控"""
        if self.is_topmost and self.window.winfo_exists():
            try:
                # 檢查並維持置頂
                self.window.attributes('-topmost', True)
                TopmostDateEntryManager.ensure_all_calendars_topmost(self.window)

                # 每500ms檢查一次
                self.window.after(500, self._start_topmost_monitoring)
            except:
                pass

    def ensure_topmost(self):
        """🔥 新增：確保視窗和所有日曆控件置頂"""
        try:
            if self.window.winfo_exists():
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

            if self.window:
                if self.is_modal:
                    self.window.grab_release()
                self.window.destroy()
        except:
            pass


class EnhancedBaseWindow(BaseWindow):
    """增強版BaseWindow - 提供更多置頂功能"""

    def __init__(self, title="視窗", width=600, height=400, resizable=True, parent=None,
                 auto_topmost=True, monitor_interval=500):
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
        if self.auto_topmost:
            self.ensure_topmost()

    def _on_focus_out(self, event=None):
        """失去焦點時處理"""
        self.focus_lost_count += 1

        # 如果頻繁失去焦點，可能有子視窗（如日曆）打開
        if self.focus_lost_count > 3 and self.auto_topmost:
            self.window.after(100, self._delayed_topmost_check)

    def _delayed_topmost_check(self):
        """延遲的置頂檢查"""
        if self.window.winfo_exists() and self.auto_topmost:
            self.ensure_topmost()

    def _start_topmost_monitoring(self):
        """覆寫：更智慧的置頂監控"""
        if self.is_topmost and self.window.winfo_exists() and self.auto_topmost:
            try:
                # 檢查是否真的需要重新置頂
                current_focus = self.window.focus_get()

                # 如果焦點在當前視窗或其子控件上，確保置頂
                if (current_focus is None or
                    str(current_focus).startswith(str(self.window))):
                    self.window.attributes('-topmost', True)
                    TopmostDateEntryManager.ensure_all_calendars_topmost(self.window)

                # 動態調整監控間隔
                interval = self.monitor_interval
                if self.focus_lost_count > 5:
                    interval = min(interval * 2, 2000)  # 最大2秒

                self.window.after(interval, self._start_topmost_monitoring)
            except:
                pass


# 🔥 新增：工具函數，簡化其他模組的使用
def create_topmost_dialog(parent, title, width=400, height=300, resizable=False):
    """
    快速創建置頂對話框

    Args:
        parent: 父視窗
        title: 標題
        width: 寬度
        height: 高度
        resizable: 是否可調整大小

    Returns:
        EnhancedBaseWindow: 增強版基礎視窗實例
    """
    return EnhancedBaseWindow(
        title=title,
        width=width,
        height=height,
        resizable=resizable,
        parent=parent,
        auto_topmost=True
    )

def ensure_all_windows_topmost():
    """確保所有視窗和日曆控件置頂"""
    TopmostDateEntryManager.ensure_all_calendars_topmost(tk._default_root)