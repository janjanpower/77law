# -*- coding: utf-8 -*-
"""
views/dialog_base.py
通用子視窗基底：穩定顯示、置頂在主視窗前、可選用自訂標題列（無邊框）
用法：
    from views.dialog_base import CustomDialog, open_modal_dialog
"""
from __future__ import annotations
import tkinter as tk
from typing import Optional, Callable, Tuple

try:
    # 你的專案配色/字型
    from law_controller.config.settings import AppConfig  # 若你的套件層級不同可調整
except Exception:
    class AppConfig:
        COLORS = {
            "window_bg": "#FFFFFF",
            "title_bg": "#2c3e50",
            "title_fg": "#ecf0f1",
        }
        FONTS = {
            "title": ("Microsoft JhengHei", 12, "bold"),
            "text": ("Microsoft JhengHei", 10),
            "button": ("Microsoft JhengHei", 10, "bold"),
        }

class ParentTopmostGuard:
    """在開子視窗期間，暫停主視窗置頂；結束後恢復。"""
    def __init__(self, parent: tk.Misc):
        self.parent = parent
        self.prev_topmost = False
        self.has_suspend = hasattr(parent, "suspend_topmost")
        self.has_resume = hasattr(parent, "resume_topmost")

    def __enter__(self):
        try:
            if self.has_suspend:
                self.parent.suspend_topmost()
            else:
                self.prev_topmost = bool(self.parent.attributes("-topmost"))
                self.parent.attributes("-topmost", False)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.has_resume:
                self.parent.resume_topmost()
            else:
                self.parent.attributes("-topmost", self.prev_topmost)
                if self.prev_topmost:
                    self.parent.lift()
        except Exception:
            pass

def center_geometry(parent: tk.Misc, w: int, h: int) -> str:
    """回傳置中的 geometry 字串。"""
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

class CustomDialog:
    """
    可重用子視窗基底：
      - 先畫 UI → 顯示/抓焦點 →（可選）再切無邊框 overiderirect(True)
      - 預設使用自訂標題列（可拖曳、關閉），失敗會自動回退不當機
    子類別需覆寫：
      - build_body(self, parent): 建立內容
      - （可選）self.first_focus: Callable，指定首個聚焦行為
    """
    def __init__(
        self,
        parent: tk.Misc,
        title: str = "對話框",
        size: Tuple[int, int] = (360, 300),
        borderless: bool = True,
        modal: bool = True,
    ):
        self.parent = parent
        self.borderless = borderless
        self.modal = modal
        self.first_focus: Optional[Callable[[], None]] = None

        # 1) 先用標準 Toplevel 畫完 UI（避免空白/崩潰）
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        self.top.resizable(False, False)
        self.top.configure(bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.top.geometry(center_geometry(parent, *size))

        # 自訂標題列（先畫好，稍後才隱藏原生標題）
        self._build_title_bar(title)

        # 內容區容器
        self.body_frame = tk.Frame(self.top, bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        self.body_frame.pack(fill="both", expand=True, padx=16, pady=12)

        # 交由子類別建立表單
        self.build_body(self.body_frame)

        # 2) 顯示＋置頂＋（可選）modal 抓焦點
        self.top.deiconify()
        self.top.lift(parent)
        self.top.update_idletasks()
        if self.modal:
            try:
                self.top.grab_set()
            except Exception:
                pass
        self.top.wait_visibility()
        self._focus_first()

        # 3) 最後才嘗試隱藏原生標題（無邊框），失敗回退
        if self.borderless:
            try:
                self.top.overrideredirect(True)
                self.top.attributes("-topmost", True)
                self.top.bind("<FocusOut>", lambda e: self._focus_first())
            except Exception:
                # 回退：使用原生標題，但保持置頂
                self.top.overrideredirect(False)
                self.top.attributes("-topmost", True)

    # ====== 子類別要覆寫 ======
    def build_body(self, parent: tk.Frame) -> None:
        """子類別覆寫：建立表單/內容"""
        pass

    # ====== 自訂標題列（含拖曳、關閉）======
    def _build_title_bar(self, title: str) -> None:
        bar = tk.Frame(self.top, bg=AppConfig.COLORS.get("title_bg", "#2c3e50"), height=34)
        bar.pack(fill="x"); bar.pack_propagate(False)

        lbl = tk.Label(
            bar, text=title,
            bg=AppConfig.COLORS.get("title_bg", "#2c3e50"),
            fg=AppConfig.COLORS.get("title_fg", "#ecf0f1"),
            font=AppConfig.FONTS.get("title", ("Microsoft JhengHei", 12, "bold")),
        )
        lbl.pack(side="left", padx=10)

        btn = tk.Button(
            bar, text="✕",
            bg=AppConfig.COLORS.get("title_bg", "#2c3e50"),
            fg=AppConfig.COLORS.get("title_fg", "#ecf0f1"),
            bd=0, width=3, command=self.close
        )
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

        self._title_bar = bar

    def _focus_first(self) -> None:
        try:
            self.top.attributes("-topmost", True)
            self.top.lift()
            self.top.focus_force()
            if callable(self.first_focus):
                self.first_focus()
            else:
                # 預設：找第一個 Entry 聚焦
                for child in self.body_frame.winfo_children():
                    if isinstance(child, tk.Entry):
                        child.focus_set()
                        try: child.icursor(tk.END)
                        except Exception: pass
                        break
        except Exception:
            pass

    def close(self) -> None:
        try:
            self.top.grab_release()
        except Exception:
            pass
        self.top.destroy()

def open_modal_dialog(parent: tk.Misc, dialog_cls, *args, **kwargs):
    """
    統一開啟子視窗：暫停主窗置頂 → 開窗（modal）→ 等待 → 恢復
    回傳：(result, dialog_instance)
    """
    with ParentTopmostGuard(parent):
        dlg = dialog_cls(parent, *args, **kwargs)
        parent.wait_window(dlg.top)
    return getattr(dlg, "result", None), dlg
