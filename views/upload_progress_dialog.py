# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk

class UploadProgressDialog(tk.Toplevel):
    def __init__(self, parent, total_cases: int, on_cancel=None, title_text="資料上傳至雲端"):
        super().__init__(parent)

        # ===== 無邊框 & 透明邊緣設定 =====
        self.overrideredirect(True)           # 移除原生標題列
        self.configure(bg="#000000")          # 外框底色（做出一圈 1px 邊界感）
        self._content_bg = "#2b2b2b"          # 內層底色（原本你的深色）
        self._header_bg = "#1f1f1f"           # 標題列底色
        self._border_radius = 0               # Tk 不支援真正圓角，保留參數以後好擴充

        # modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self.on_cancel = on_cancel
        self.total_cases = total_cases

        # 狀態變數
        self.percent_var = tk.IntVar(value=0)
        self.status_var = tk.StringVar(value="準備上傳…")
        self.uploaded_var = tk.StringVar(value="成功：0")
        self.failed_var = tk.StringVar(value="失敗：0")
        self.total_var = tk.StringVar(value=f"總筆數：{total_cases}")

        # ===== 佈局：外框 -> 內層容器 =====
        outer = tk.Frame(self, bg="#000000")  # 模擬 1px 邊界
        outer.pack(padx=1, pady=1, fill="both", expand=True)

        root = tk.Frame(outer, bg=self._content_bg)
        root.pack(fill="both", expand=True)

        # ===== 自訂標題列 =====
        self._make_header(root, title_text)

        # ===== 內容區 =====
        body = tk.Frame(root, bg=self._content_bg)
        body.pack(fill="both", expand=True, padx=14, pady=(8, 10))

        # 統計列
        stat = tk.Frame(body, bg=self._content_bg)
        stat.pack(fill="x")
        tk.Label(stat, textvariable=self.total_var, fg="#bdbdbd", bg=self._content_bg).pack(side="left")
        tk.Label(stat, textvariable=self.uploaded_var, fg="#9ccc65", bg=self._content_bg).pack(side="left", padx=(12,0))
        tk.Label(stat, textvariable=self.failed_var, fg="#ef5350", bg=self._content_bg).pack(side="left", padx=(12,0))

        # 進度條
        self.progress = ttk.Progressbar(body, orient="horizontal", mode="determinate", maximum=100, length=480)
        self.progress.pack(pady=(10, 4), fill="x")
        self.progress["value"] = 0

        # 狀態訊息
        tk.Label(body, textvariable=self.status_var, fg="#ffffff", bg=self._content_bg).pack(anchor="w")

        # 日誌
        tk.Label(body, text="日誌", fg="#bdbdbd", bg=self._content_bg).pack(anchor="w", pady=(8, 0))
        self.log = tk.Text(body, height=10, bg="#1e1e1e", fg="#dcdcdc", relief="flat")
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        self.log.configure(state="disabled")

        # 動作列
        footer = tk.Frame(body, bg=self._content_bg)
        footer.pack(fill="x", pady=(10, 0))
        self.cancel_btn = tk.Button(footer, text="取消", command=self._on_cancel_click, width=10)
        self.cancel_btn.pack(side="right")

        # 尺寸與置中
        self.update_idletasks()
        w, h = 540, 380
        self.geometry(self._center(parent, w, h))

        # Esc 關閉（等同點右上角關閉）
        self.bind("<Escape>", lambda e: self._on_close_click())

        # 最上層（避免被主視窗遮住）
        try:
            self.wm_attributes("-topmost", True)
        except Exception:
            pass

    # ===== 自訂標題列 =====
    def _make_header(self, root, title_text: str):
        header = tk.Frame(root, bg=self._header_bg, height=40)
        header.pack(fill="x")

        # 拖曳移動
        header.bind("<ButtonPress-1>", self._start_move)
        header.bind("<B1-Motion>", self._on_move)

        # 標題文字
        ttl = tk.Label(header, text=title_text, fg="#ffffff", bg=self._header_bg,
                       font=("Microsoft JhengHei", 12, "bold"))
        ttl.pack(side="left", padx=12)
        ttl.bind("<ButtonPress-1>", self._start_move)
        ttl.bind("<B1-Motion>", self._on_move)

        # 視窗控制鈕
        btn_wrap = tk.Frame(header, bg=self._header_bg)
        btn_wrap.pack(side="right", padx=6)

        # 最小化
        min_btn = tk.Button(btn_wrap, text="—", command=self._on_minimize, width=3,
                            relief="flat", bg=self._header_bg, fg="#dddddd", activebackground="#333333")
        min_btn.pack(side="right", padx=(0, 4))

        # 關閉
        close_btn = tk.Button(btn_wrap, text="×", command=self._on_close_click, width=3,
                              relief="flat", bg=self._header_bg, fg="#ff6b6b", activebackground="#333333")
        close_btn.pack(side="right")

    # ===== 對外 API（與原版相容） =====
    @classmethod
    def show_upload_dialog(cls, parent, total_cases: int, on_cancel=None, title_text="資料上傳至雲端"):
        dlg = cls(parent, total_cases, on_cancel=on_cancel, title_text=title_text)
        parent.update_idletasks()
        return dlg

    def update_progress(self, percent: int, message: str):
        percent = max(0, min(100, int(percent)))
        self.percent_var.set(percent)
        self.progress["value"] = percent
        self.status_var.set(message)
        self.update_idletasks()

    def update_stats(self, uploaded: int, failed: int):
        self.uploaded_var.set(f"成功：{uploaded}")
        self.failed_var.set(f"失敗：{failed}")
        self.update_idletasks()

    def add_log(self, msg: str, level: str = "info"):
        color = {"info": "#dcdcdc", "success": "#9ccc65", "error": "#ef5350"}.get(level, "#dcdcdc")
        self.log.configure(state="normal")
        self.log.insert("end", f"{msg}\n")
        # 簡單用顏色區分等級
        self.log.tag_add(level, "end-1l linestart", "end-1l lineend")
        self.log.tag_config(level, foreground=color)
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def on_upload_complete(self, success: bool, summary: dict):
        # 完成後把「取消」變「關閉」
        self.cancel_btn.configure(text="關閉", command=self._on_close_click)
        if success:
            ok = summary.get("uploaded", 0)
            fail = summary.get("failed", 0)
            total = summary.get("total", ok + fail)
            self.update_progress(100, f"完成：{ok}/{total} 成功，{fail} 失敗")
            self.add_log("上傳完成", "success")
        else:
            self.add_log(summary.get("message", "上傳失敗"), "error")

    # ===== 內部：拖曳、最小化、關閉、取消 =====
    def _start_move(self, event):
        self._drag_off_x = event.x
        self._drag_off_y = event.y

    def _on_move(self, event):
        try:
            x = self.winfo_pointerx() - self._drag_off_x
            y = self.winfo_pointery() - self._drag_off_y
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _on_minimize(self):
        # 無邊框時最小化需先 temporary 關閉 overrideredirect
        try:
            self.overrideredirect(False)
            self.iconify()
            # 還原時再關閉標題列
            def _restore(_e):
                self.overrideredirect(True)
                self.unbind("<Map>", _restore)
            self.bind("<Map>", _restore)
        except Exception:
            pass

    def _on_close_click(self):
        # 關閉時釋放 grab，避免母視窗無法操作
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_cancel_click(self):
        if callable(self.on_cancel):
            try:
                self.on_cancel()
            except Exception:
                pass
        self._on_close_click()

    # ===== 工具 =====
    def _center(self, parent, w: int, h: int) -> str:
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        except Exception:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
        return f"{w}x{h}+{x}+{y}"
