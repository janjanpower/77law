# -*- coding: utf-8 -*-
# views/windowing.py
import platform
import tkinter as tk
from typing import Tuple

def center_on_parent(parent: tk.Misc, size: Tuple[int, int]) -> str:
    w, h = size
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

def open_modal(parent: tk.Tk | tk.Toplevel, dialog_cls, *args, **kwargs):
    """
    統一開啟子視窗：Windows 會暫時禁用父窗，所有平台都使用 modal（grab_set + wait_window）。
    回傳 dialog.result
    """
    is_windows = platform.system().lower() == "windows"
    if is_windows:
        try:
            parent.wm_attributes("-disabled", True)
        except Exception:
            pass

    dlg = dialog_cls(parent, *args, **kwargs)
    try:
        parent.wait_window(dlg.win)
    finally:
        if is_windows:
            try:
                parent.wm_attributes("-disabled", False)
                parent.focus_force()
                parent.lift()
            except Exception:
                pass
    return getattr(dlg, "result", None)
