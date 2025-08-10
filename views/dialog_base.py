# -*- coding: utf-8 -*-
# views/dialog_base.py
import platform
import sys
import tkinter as tk
from typing import Optional, Callable, Tuple
from .windowing import center_on_parent,open_modal

try:
    from config.settings import AppConfig
except Exception:
    class AppConfig:
        COLORS = {"window_bg": "#FFFFFF", "title_bg": "#2c3e50", "title_fg": "#ecf0f1"}
        FONTS  = {"title": ("Microsoft JhengHei", 12, "bold"),
                  "text": ("Microsoft JhengHei", 10),
                  "button": ("Microsoft JhengHei", 10, "bold")}

class ModalDialog:
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        size: Tuple[int, int] = (340, 280),
        topmost: bool = True,
        borderless: bool = False,   # ← 開這個就去除 tk 標題
    ):
        self.parent = parent
        self.result = None
        self.first_focus: Optional[Callable[[], None]] = None
        self._borderless = borderless
        self._is_windows = sys.platform.startswith("win")

        # 先建立 Toplevel（還不顯示）
        self.win = tk.Toplevel(parent)
        self.win.withdraw()
        self.win.title(title)
        self.win.transient(parent)
        self.win.resizable(False, False)
        self.win.configure(bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        self.win.protocol("WM_DELETE_WINDOW", self.close)

        # 幾何先算好
        geom = center_on_parent(parent, size)
        self.win.geometry(geom)

        # **Windows + 無邊框：顯示前就切無邊框（關鍵！）**
        if self._borderless and self._is_windows:
            try:
                self.win.overrideredirect(True)
                # 視窗變無邊框後，幾何要再設一次以免跳位
                self.win.geometry(geom)
            except Exception:
                # 失敗就回退（但通常 Windows 會成功）
                self.win.overrideredirect(False)

        # 自訂標題列（自己畫）
        self._build_title_bar(title)

        # 內容
        body = tk.Frame(self.win, bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        body.pack(fill="both", expand=True, padx=16, pady=12)
        self.build(body)

        # 顯示 + 置前 + modal
        self.win.deiconify()
        if topmost:
            try: self.win.attributes("-topmost", True)
            except Exception: pass
        self.win.lift(parent)
        try: self.win.grab_set()
        except Exception: pass
        self.win.update_idletasks()
        self.win.wait_visibility()
        self._focus_first()

        # 非 Windows（macOS / Linux）如果也要求無邊框，再用「延遲套用」法（這兩家對無邊框較敏感）
        if self._borderless and not self._is_windows:
            self.win.after(150, self._apply_borderless_safely)

        # ESC 關閉
        self.win.bind("<Escape>", lambda e: self.close())

    def build(self, body: tk.Frame) -> None:
        pass

    def _build_title_bar(self, title: str):
        bar = tk.Frame(self.win, bg=AppConfig.COLORS.get("title_bg", "#2c3e50"), height=36)
        bar.pack(fill="x"); bar.pack_propagate(False)
        lbl = tk.Label(bar, text=title,
                       bg=AppConfig.COLORS.get("title_bg", "#2c3e50"),
                       fg=AppConfig.COLORS.get("title_fg", "#ecf0f1"),
                       font=AppConfig.FONTS.get("title", ("Microsoft JhengHei", 12, "bold")))
        lbl.pack(side="left", padx=10)
        btn = tk.Button(bar, text="✕",
                        bg=AppConfig.COLORS.get("title_bg", "#2c3e50"),
                        fg=AppConfig.COLORS.get("title_fg", "#ecf0f1"),
                        bd=0, width=3, command=self.close)
        btn.pack(side="right", padx=6)
        # 拖曳
        drag = {"x": 0, "y": 0}
        def start_drag(e): drag.update(x=e.x, y=e.y)
        def on_drag(e):
            nx = self.win.winfo_x() + (e.x - drag["x"])
            ny = self.win.winfo_y() + (e.y - drag["y"])
            self.win.geometry(f"+{nx}+{ny}")
        for w in (bar, lbl):
            w.bind("<Button-1>", start_drag)
            w.bind("<B1-Motion>", on_drag)

    def _focus_first(self):
        try:
            self.win.focus_force()
            if callable(self.first_focus):
                self.first_focus()
            else:
                for child in self.win.winfo_children():
                    if isinstance(child, tk.Entry):
                        child.focus_set()
                        try: child.icursor("end")
                        except Exception: pass
                        return
                    if hasattr(child, "winfo_children"):
                        for sub in child.winfo_children():
                            if isinstance(sub, tk.Entry):
                                sub.focus_set()
                                try: sub.icursor("end")
                                except Exception: pass
                                return
        except Exception:
            pass

    def _apply_borderless_safely(self):
        # macOS / Linux 專用的「延遲套用」；Windows 走預顯示套用
        if not self.win.winfo_exists():
            return
        try:
            geom = self.win.geometry()
            self.win.overrideredirect(True)
            self.win.geometry(geom)
            self.win.update_idletasks()
            self.win.lift(self.parent)
            try: self.win.attributes("-topmost", True)
            except Exception: pass
            self.win.bind("<FocusOut>", lambda e: self._focus_first())
        except Exception:
            try:
                self.win.overrideredirect(False)
                self.win.attributes("-topmost", True)
            except Exception:
                pass

    def close(self):
        try: self.win.grab_release()
        except Exception: pass
        self.win.destroy()

# ---------- helpers ----------
def _center_geometry(parent: tk.Misc, w: int, h: int) -> str:
    try:
        parent.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        if pw <= 1 or ph <= 1:
            sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
            x, y = (sw - w)//2, (sh - h)//2
        else:
            x = px + max((pw - w)//2, 0)
            y = py + max((ph - h)//2, 0)
    except Exception:
        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        x, y = (sw - w)//2, (sh - h)//2
    return f"{w}x{h}+{x}+{y}"

class ParentTopmostGuard:
    """
    開子視窗期間：暫停父窗置頂；Windows 另外把父窗暫時 -disabled，退出時恢復。
    兼容 BaseWindow.suspend_topmost()/resume_topmost()；沒有就降級處理。
    """
    def __init__(self, parent: tk.Misc):
        self.parent = parent
        self.prev_topmost = False
        self.has_suspend = hasattr(parent, "suspend_topmost")
        self.has_resume  = hasattr(parent, "resume_topmost")
        self._win_disabled = False
        self._os = platform.system().lower()

    def __enter__(self):
        try:
            if self.has_suspend:
                self.parent.suspend_topmost()
            else:
                self.prev_topmost = bool(self.parent.attributes("-topmost"))
                self.parent.attributes("-topmost", False)
        except Exception:
            pass
        if self._os == "windows":
            try:
                self.parent.wm_attributes("-disabled", True)
                self._win_disabled = True
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._win_disabled:
            try: self.parent.wm_attributes("-disabled", False)
            except Exception: pass
        try:
            if self.has_resume:
                self.parent.resume_topmost()
            else:
                self.parent.attributes("-topmost", self.prev_topmost)
                if self.prev_topmost:
                    self.parent.lift()
        except Exception:
            pass

# ---------- Dialog base ----------
class CustomDialog:
    """
    穩定子視窗基底：
      1) 先建 UI → 顯示/置前/抓焦點（modal）
      2) 短暫 keep-front（0.8s）防止被搶
      3) 僅 Windows 延遲套 overrideredirect(True)；其它 OS 保留原生標題
    子類別需覆寫：
      - build_body(self, parent): 建立內容
      - （可選）self.first_focus: Callable
    """
    def __init__(self, parent: tk.Misc, title: str = "對話框",
                 size: Tuple[int, int] = (360, 300),
                 borderless: Optional[bool] = None,  # None=自動：Windows True，其它 False
                 modal: bool = True):
        self.parent = parent
        self._os = platform.system().lower()
        self.borderless = (borderless if borderless is not None else self._os == "windows")
        self.modal = modal
        self.first_focus: Optional[Callable[[], None]] = None

        # 1) 建 UI（標準 Toplevel）
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        self.top.resizable(False, False)
        self.top.configure(bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.top.geometry(_center_geometry(parent, *size))

        # 自訂標題列（就算保留原生標題也能沿用樣式）
        self._build_title_bar(title)

        # 內容框
        self.body_frame = tk.Frame(self.top, bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        self.body_frame.pack(fill="both", expand=True, padx=16, pady=12)
        self.build_body(self.body_frame)

        # 2) 顯示＋置前＋modal 抓焦點
        self.top.deiconify()
        self.top.lift(parent)
        self.top.update_idletasks()
        if self.modal:
            try: self.top.grab_set()
            except Exception: pass
        self.top.wait_visibility()
        self._focus_first()

        # keep-front（避免 OS/父窗在短時間內搶回）
        self._keep_front_ticks = 8
        self._keep_front_loop()

        # 3) Windows 再延遲套無邊框（其它 OS 維持原生標題）
        if self.borderless and self._os == "windows":
            self.top.after(150, self._apply_borderless_safely)

    # 子類別必需覆寫
    def build_body(self, parent: tk.Frame) -> None:
        pass

    # 自訂標題列（含拖曳/關閉）
    def _build_title_bar(self, title: str):
        bar = tk.Frame(self.top, bg=AppConfig.COLORS.get("title_bg", "#2c3e50"), height=34)
        bar.pack(fill="x"); bar.pack_propagate(False)
        lbl = tk.Label(bar, text=title,
                       bg=AppConfig.COLORS.get("title_bg", "#2c3e50"),
                       fg=AppConfig.COLORS.get("title_fg", "#ecf0f1"),
                       font=AppConfig.FONTS.get("title", ("Microsoft JhengHei", 12, "bold")))
        lbl.pack(side="left", padx=10)
        btn = tk.Button(bar, text="✕",
                        bg=AppConfig.COLORS.get("title_bg", "#2c3e50"),
                        fg=AppConfig.COLORS.get("title_fg", "#ecf0f1"),
                        bd=0, width=3, command=self.close)
        btn.pack(side="right", padx=6)

        # 拖曳
        drag = {"x": 0, "y": 0}
        def start_drag(e): drag.update(x=e.x, y=e.y)
        def on_drag(e):
            nx = self.top.winfo_x() + (e.x - drag["x"])
            ny = self.top.winfo_y() + (e.y - drag["y"])
            self.top.geometry(f"+{nx}+{ny}")
        for w in (bar, lbl):
            w.bind("<Button-1>", start_drag)
            w.bind("<B1-Motion>", on_drag)

    def _focus_first(self):
        try:
            self.top.attributes("-topmost", True)
            self.top.lift()
            self.top.focus_force()
            if callable(self.first_focus):
                self.first_focus()
            else:
                for child in self.body_frame.winfo_children():
                    if isinstance(child, tk.Entry):
                        child.focus_set()
                        try: child.icursor("end")
                        except Exception: pass
                        break
        except Exception:
            pass

    def _keep_front_loop(self):
        if not self.top.winfo_exists():
            return
        try:
            self.top.attributes("-topmost", True)
            self.top.lift(self.parent)
            self.top.focus_force()
        except Exception:
            pass
        self._keep_front_ticks -= 1
        if self._keep_front_ticks > 0:
            self.top.after(100, self._keep_front_loop)

    def _apply_borderless_safely(self):
        if not self.top.winfo_exists():
            return
        try:
            self.top.overrideredirect(True)
            self.top.update_idletasks()
            self.top.lift(self.parent)
            self.top.attributes("-topmost", True)
            self.top.bind("<FocusOut>", lambda e: self._focus_first())
        except Exception:
            try:
                self.top.overrideredirect(False)
                self.top.attributes("-topmost", True)
            except Exception:
                pass

    def close(self):
        try: self.top.grab_release()
        except Exception: pass
        self.top.destroy()

# 統一開窗：暫停父窗置頂/禁用（Win）→ 等待 → 恢復
def open_modal_dialog(parent: tk.Misc, dialog_cls, *args, **kwargs):
    with ParentTopmostGuard(parent):
        dlg = dialog_cls(parent, *args, **kwargs)
        parent.wait_window(dlg.top)
    return getattr(dlg, "result", None), dlg
