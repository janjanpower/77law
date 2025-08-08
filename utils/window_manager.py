# utils/window_manager.py - 修改版本
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一視窗管理器 - 解決確認視窗被覆蓋問題
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Callable
from enum import Enum, auto
import threading
import time

class WindowPriority(Enum):
    """視窗優先級 - 修改：調整優先級順序"""
    BACKGROUND = 1       # 背景視窗（主視窗）
    NORMAL = 2          # 普通視窗
    FLOATING = 3        # 浮動視窗（功能按鈕）
    DIALOG = 4          # 對話框
    MODAL = 5           # 模態對話框
    CRITICAL = 6        # 關鍵提示（錯誤、確認）- 最高優先級
    TOOLTIP = 7         # 工具提示

class WindowState(Enum):
    """視窗狀態"""
    HIDDEN = auto()
    NORMAL = auto()
    TOPMOST = auto()
    MODAL = auto()

class ManagedWindow:
    """被管理的視窗物件"""

    def __init__(self, window: tk.Toplevel, priority: WindowPriority,
                 window_id: str, parent_id: Optional[str] = None):
        self.window = window
        self.priority = priority
        self.window_id = window_id
        self.parent_id = parent_id
        self.state = WindowState.NORMAL
        self.is_modal = False
        self.is_dropdown_open = False
        self.last_interaction = time.time()
        self.force_topmost = False  # 新增：強制置頂標記

        # 回調函數
        self.on_focus_callback: Optional[Callable] = None
        self.on_close_callback: Optional[Callable] = None

class WindowManager:
    """統一視窗管理器 - 修改版本"""

    _instance: Optional['WindowManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.managed_windows: Dict[str, ManagedWindow] = {}
        self.window_stack: List[str] = []
        self.current_modal: Optional[str] = None
        self.critical_windows: List[str] = []  # 新增：關鍵視窗列表
        self.focus_monitoring = True
        self.update_interval = 50  # 修改：縮短更新間隔
        self._update_job = None

    def register_window(self, window: tk.Toplevel, priority: WindowPriority,
                       window_id: str, parent_id: Optional[str] = None) -> ManagedWindow:
        """註冊視窗到管理器"""

        managed_window = ManagedWindow(window, priority, window_id, parent_id)
        self.managed_windows[window_id] = managed_window

        # 🔥 新增：關鍵視窗特殊處理
        if priority == WindowPriority.CRITICAL:
            managed_window.force_topmost = True
            self.critical_windows.append(window_id)

        # 綁定事件
        self._bind_window_events(managed_window)

        # 立即更新視窗堆疊
        self._update_window_stack()

        # 🔥 修改：關鍵視窗立即置頂
        if priority == WindowPriority.CRITICAL:
            self._force_critical_window_front(window_id)

        # 開始監控
        if self._update_job is None:
            self._start_monitoring()

        return managed_window

    def _force_critical_window_front(self, window_id: str):
        """🔥 新增：強制關鍵視窗置頂"""
        if window_id not in self.managed_windows:
            return

        managed_window = self.managed_windows[window_id]

        try:
            # 暫時停用所有其他視窗的置頂
            for other_id, other_window in self.managed_windows.items():
                if other_id != window_id and self._is_window_valid(other_window):
                    other_window.window.attributes('-topmost', False)

            # 設定關鍵視窗為置頂
            managed_window.window.attributes('-topmost', True)
            managed_window.window.lift()
            managed_window.window.focus_force()

            # 延遲恢復其他視窗的置頂（給關鍵視窗足夠時間顯示）
            managed_window.window.after(200, lambda: self._restore_window_levels())

        except tk.TclError:
            pass

    def _restore_window_levels(self):
        """🔥 新增：恢復視窗層級"""
        try:
            # 確保關鍵視窗仍然在最前面
            for window_id in self.critical_windows:
                if window_id in self.managed_windows:
                    managed_window = self.managed_windows[window_id]
                    if self._is_window_valid(managed_window):
                        managed_window.window.attributes('-topmost', True)
                        managed_window.window.lift()

            # 然後處理其他視窗
            self._update_window_levels()

        except tk.TclError:
            pass

    def set_modal(self, window_id: str, modal: bool = True):
        """設定視窗為模態 - 修改版本"""
        if window_id not in self.managed_windows:
            return False

        managed_window = self.managed_windows[window_id]

        if modal:
            # 🔥 修改：模態設定邏輯
            if self.current_modal and self.current_modal != window_id:
                self._release_modal(self.current_modal)

            self.current_modal = window_id
            managed_window.is_modal = True
            managed_window.state = WindowState.MODAL

            try:
                managed_window.window.grab_set()
                managed_window.window.transient()

                # 🔥 新增：確保模態視窗在最前面
                if managed_window.priority == WindowPriority.CRITICAL:
                    self._force_critical_window_front(window_id)
                else:
                    managed_window.window.attributes('-topmost', True)
                    managed_window.window.lift()
                    managed_window.window.focus_force()

            except tk.TclError:
                pass

        else:
            self._release_modal(window_id)

        self._update_window_stack()
        return True

    def unregister_window(self, window_id: str):
        """取消註冊視窗 - 修改版本"""
        if window_id in self.managed_windows:
            managed_window = self.managed_windows[window_id]

            # 🔥 新增：從關鍵視窗列表移除
            if window_id in self.critical_windows:
                self.critical_windows.remove(window_id)

            # 如果是當前模態視窗，清除模態狀態
            if self.current_modal == window_id:
                self.current_modal = None

            # 從堆疊移除
            if window_id in self.window_stack:
                self.window_stack.remove(window_id)

            # 執行關閉回調
            if managed_window.on_close_callback:
                managed_window.on_close_callback()

            del self.managed_windows[window_id]

            # 更新剩餘視窗
            self._update_window_stack()

    def _update_window_levels(self):
        """更新視窗層級 - 修改版本"""
        try:
            # 🔥 修改：優先處理關鍵視窗
            for window_id in self.critical_windows:
                if window_id in self.managed_windows:
                    managed_window = self.managed_windows[window_id]
                    if self._is_window_valid(managed_window):
                        managed_window.window.attributes('-topmost', True)
                        managed_window.window.lift()

            # 處理模態視窗
            if self.current_modal and self.current_modal in self.managed_windows:
                modal_window = self.managed_windows[self.current_modal]
                if self._is_window_valid(modal_window):
                    if modal_window.priority == WindowPriority.CRITICAL:
                        # 關鍵模態視窗保持最高優先級
                        modal_window.window.attributes('-topmost', True)
                    modal_window.window.lift()
                    return

            # 處理非模態視窗
            for window_id in self.window_stack:
                if window_id not in self.managed_windows:
                    continue

                managed_window = self.managed_windows[window_id]

                if not self._is_window_valid(managed_window):
                    continue

                # 根據優先級設定置頂狀態
                should_be_topmost = self._should_be_topmost(managed_window)

                if should_be_topmost and not managed_window.is_dropdown_open:
                    managed_window.window.attributes('-topmost', True)
                    managed_window.window.lift()
                else:
                    managed_window.window.attributes('-topmost', False)

        except tk.TclError:
            pass

    def _should_be_topmost(self, managed_window: ManagedWindow) -> bool:
        """判斷視窗是否應該置頂 - 修改版本"""
        # 🔥 修改：強制置頂標記優先
        if managed_window.force_topmost:
            return True

        # 模態視窗總是置頂
        if managed_window.is_modal:
            return True

        # 關鍵優先級總是置頂
        if managed_window.priority == WindowPriority.CRITICAL:
            return True

        # 其他邏輯保持不變
        if managed_window.priority == WindowPriority.DIALOG:
            return not self._has_higher_priority_window(managed_window.priority)

        if managed_window.priority == WindowPriority.FLOATING:
            return not self._has_higher_priority_window(managed_window.priority)

        return False

    def _has_higher_priority_window(self, priority: WindowPriority) -> bool:
        """檢查是否有更高優先級的視窗 - 修改版本"""
        for managed_window in self.managed_windows.values():
            if (self._is_window_valid(managed_window) and
                managed_window.priority.value > priority.value):
                return True
        return False

    # 其他方法保持不變...
    def _bind_window_events(self, managed_window: ManagedWindow):
        """綁定視窗事件"""
        window = managed_window.window
        window_id = managed_window.window_id

        def on_focus_in(event):
            self._on_window_focus(window_id, True)

        def on_focus_out(event):
            self._on_window_focus(window_id, False)

        def on_destroy(event):
            if event.widget == window:
                self.unregister_window(window_id)

        window.bind('<FocusIn>', on_focus_in)
        window.bind('<FocusOut>', on_focus_out)
        window.bind('<Destroy>', on_destroy)

    def _on_window_focus(self, window_id: str, has_focus: bool):
        """處理視窗焦點變化"""
        if window_id not in self.managed_windows:
            return

        managed_window = self.managed_windows[window_id]

        if has_focus:
            managed_window.last_interaction = time.time()

            if managed_window.on_focus_callback:
                managed_window.on_focus_callback(True)

            if window_id in self.window_stack:
                self.window_stack.remove(window_id)
            self.window_stack.append(window_id)
        else:
            if managed_window.on_focus_callback:
                managed_window.on_focus_callback(False)

    def _update_window_stack(self):
        """更新視窗堆疊順序"""
        valid_windows = []

        for window_id in list(self.window_stack):
            if window_id in self.managed_windows:
                managed_window = self.managed_windows[window_id]
                if self._is_window_valid(managed_window):
                    valid_windows.append(window_id)

        valid_windows.sort(key=lambda wid: (
            self.managed_windows[wid].priority.value,
            self.managed_windows[wid].last_interaction
        ))

        self.window_stack = valid_windows
        self._update_window_levels()

    def _is_window_valid(self, managed_window: ManagedWindow) -> bool:
        """檢查視窗是否有效"""
        try:
            return (managed_window.window.winfo_exists() and
                    managed_window.window.winfo_viewable())
        except tk.TclError:
            return False

    def _start_monitoring(self):
        """開始監控視窗狀態"""
        if self._update_job is not None:
            return

        def monitor():
            try:
                self._update_window_levels()
            except Exception as e:
                print(f"視窗監控錯誤: {e}")
            finally:
                if self.managed_windows:
                    self._update_job = None
                    for managed_window in self.managed_windows.values():
                        if self._is_window_valid(managed_window):
                            self._update_job = managed_window.window.after(
                                self.update_interval, monitor
                            )
                            break
                else:
                    self._update_job = None

        monitor()

    def _release_modal(self, window_id: str):
        """釋放模態狀態"""
        if window_id in self.managed_windows:
            managed_window = self.managed_windows[window_id]
            managed_window.is_modal = False
            managed_window.state = WindowState.NORMAL

            try:
                managed_window.window.grab_release()
            except tk.TclError:
                pass

            if self.current_modal == window_id:
                self.current_modal = None

    def bring_to_front(self, window_id: str, force: bool = False):
        """將視窗帶到前景"""
        if window_id not in self.managed_windows:
            return False

        managed_window = self.managed_windows[window_id]

        if not force and self.current_modal and self.current_modal != window_id:
            return False

        try:
            managed_window.window.lift()
            managed_window.window.focus_force()
            managed_window.last_interaction = time.time()

            if window_id in self.window_stack:
                self.window_stack.remove(window_id)
            self.window_stack.append(window_id)

        except tk.TclError:
            return False

        return True

# 單例訪問和便利函數
def get_window_manager() -> WindowManager:
    return WindowManager()

def register_window(window: tk.Toplevel, priority: WindowPriority,
                   window_id: str, parent_id: Optional[str] = None) -> ManagedWindow:
    return get_window_manager().register_window(window, priority, window_id, parent_id)

def unregister_window(window_id: str):
    get_window_manager().unregister_window(window_id)

def set_modal(window_id: str, modal: bool = True):
    return get_window_manager().set_modal(window_id, modal)

def bring_to_front(window_id: str, force: bool = False):
    return get_window_manager().bring_to_front(window_id, force)