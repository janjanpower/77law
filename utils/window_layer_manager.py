#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class WindowLayerManager:
    """統一的視窗層級管理器"""

    _instance = None
    _active_windows = []  # 活躍視窗堆疊
    _modal_stack = []     # 模態對話框堆疊

    def __new__(cls):
        """單例模式"""
        if cls._instance is None:
            cls._instance = super(WindowLayerManager, cls).__new__(cls)
        return cls._instance

    def register_window(self, window, window_type="normal", parent=None):
        """
        註冊視窗到管理器

        Args:
            window: Tkinter 視窗物件
            window_type: 視窗類型 ("normal", "dialog", "modal", "topmost")
            parent: 父視窗
        """
        window_info = {
            'window': window,
            'type': window_type,
            'parent': parent,
            'is_active': True
        }

        if window_type == "modal":
            self._modal_stack.append(window_info)
            self._set_modal_window(window, parent)
        else:
            self._active_windows.append(window_info)
            self._manage_window_layers()

    def unregister_window(self, window):
        """從管理器移除視窗"""
        # 從活躍視窗列表移除
        self._active_windows = [w for w in self._active_windows if w['window'] != window]

        # 從模態堆疊移除
        self._modal_stack = [w for w in self._modal_stack if w['window'] != window]

        # 重新管理視窗層級
        self._manage_window_layers()

    def _set_modal_window(self, window, parent=None):
        """設定模態視窗"""
        try:
            if window and hasattr(window, 'winfo_exists') and window.winfo_exists():
                # 暫時停用所有其他視窗的置頂
                self._disable_all_topmost()

                # 設定模態視窗
                if parent:
                    window.transient(parent)

                window.grab_set()
                window.lift()
                window.focus_force()
                window.attributes('-topmost', True)

                # 延遲移除置頂，避免永久置頂
                window.after(300, lambda: self._manage_topmost_for_modal(window))

        except Exception as e:
            print(f"設定模態視窗失敗: {e}")

    def _manage_topmost_for_modal(self, modal_window):
        """管理模態視窗的置頂狀態"""
        try:
            if modal_window and hasattr(modal_window, 'winfo_exists') and modal_window.winfo_exists():
                # 移除永久置頂，但保持在最前面
                modal_window.attributes('-topmost', False)
                modal_window.lift()
                modal_window.focus_force()
        except Exception as e:
            print(f"管理模態視窗置頂失敗: {e}")

    def _disable_all_topmost(self):
        """暫時停用所有視窗的置頂屬性"""
        for window_info in self._active_windows:
            try:
                window = window_info['window']
                if window and hasattr(window, 'winfo_exists') and window.winfo_exists():
                    window.attributes('-topmost', False)
            except Exception as e:
                print(f"停用視窗置頂失敗: {e}")

    def _manage_window_layers(self):
        """管理視窗層級"""
        try:
            # 確保模態對話框在最頂層
            if self._modal_stack:
                top_modal = self._modal_stack[-1]['window']
                if top_modal and hasattr(top_modal, 'winfo_exists') and top_modal.winfo_exists():
                    top_modal.lift()
                    top_modal.focus_force()

            # 管理普通視窗的層級
            for window_info in reversed(self._active_windows):
                window = window_info['window']
                if window and hasattr(window, 'winfo_exists') and window.winfo_exists():
                    if window_info['type'] == "topmost":
                        window.attributes('-topmost', True)
                    window.lift()

        except Exception as e:
            print(f"管理視窗層級失敗: {e}")

    def show_modal_dialog(self, dialog_window, parent=None):
        """顯示模態對話框的統一方法"""
        self.register_window(dialog_window, "modal", parent)

        # 等待對話框關閉
        try:
            dialog_window.wait_window()
        finally:
            self.unregister_window(dialog_window)
            self._restore_parent_focus(parent)

    def _restore_parent_focus(self, parent):
        """恢復父視窗焦點"""
        try:
            if parent and hasattr(parent, 'winfo_exists') and parent.winfo_exists():
                parent.lift()
                parent.focus_force()
                # 如果父視窗需要置頂，重新設定
                if any(w['window'] == parent and w['type'] == "topmost" for w in self._active_windows):
                    parent.attributes('-topmost', True)
        except Exception as e:
            print(f"恢復父視窗焦點失敗: {e}")

    def ensure_dialog_visible(self, dialog_window, parent=None):
        """確保對話框可見並在最前面"""
        try:
            if dialog_window and hasattr(dialog_window, 'winfo_exists') and dialog_window.winfo_exists():
                # 暫時停用父視窗置頂
                if parent and hasattr(parent, 'winfo_exists') and parent.winfo_exists():
                    parent.attributes('-topmost', False)

                # 設定對話框置頂並置中
                dialog_window.lift()
                dialog_window.focus_force()
                dialog_window.attributes('-topmost', True)

                # 延遲恢復正常狀態
                dialog_window.after(200, lambda: self._normalize_dialog_state(dialog_window, parent))

        except Exception as e:
            print(f"確保對話框可見失敗: {e}")

    def _normalize_dialog_state(self, dialog_window, parent):
        """正常化對話框狀態"""
        try:
            if dialog_window and hasattr(dialog_window, 'winfo_exists') and dialog_window.winfo_exists():
                dialog_window.attributes('-topmost', False)
                dialog_window.lift()
        except Exception as e:
            print(f"正常化對話框狀態失敗: {e}")


# 全域管理器實例
window_layer_manager = WindowLayerManager()