# -*- coding: utf-8 -*-
"""
與 CaseOverviewWindow._on_upload_to_database 相容的進度視窗
方法接口：
- show_upload_dialog(parent, total_cases, on_cancel) -> UploadProgressDialog
- update_progress(percent:int, message:str) -> None
- update_stats(uploaded:int, failed:int) -> None
- add_log(msg:str, level:str='info') -> None
- on_upload_complete(success:bool, summary:dict) -> None
"""
import tkinter as tk
from tkinter import ttk

class UploadProgressDialog(tk.Toplevel):
    def __init__(self, parent, total_cases: int, on_cancel=None):
        super().__init__(parent)
        self.title("上傳進度")
        self.geometry("520x360")
        self.resizable(False, False)
        self.configure(bg="#2b2b2b")
        self.transient(parent)
        self.grab_set()

        self.on_cancel = on_cancel
        self.total_cases = total_cases

        # 百分比＋狀態
        self.percent_var = tk.IntVar(value=0)
        self.status_var = tk.StringVar(value="準備上傳…")

        # ====== UI ======
        pad = 12

        title = tk.Label(self, text="資料上傳至雲端", fg="white", bg="#2b2b2b", font=("Microsoft JhengHei", 14, "bold"))
        title.pack(anchor="w", padx=pad, pady=(pad, 6))

        # 統計
        stat_frame = tk.Frame(self, bg="#2b2b2b")
        stat_frame.pack(fill="x", padx=pad)

        self.uploaded_var = tk.StringVar(value="成功：0")
        self.failed_var = tk.StringVar(value="失敗：0")
        self.total_var = tk.StringVar(value=f"總筆數：{total_cases}")

        tk.Label(stat_frame, textvariable=self.total_var, fg="#bdbdbd", bg="#2b2b2b").pack(side="left")
        tk.Label(stat_frame, textvariable=self.uploaded_var, fg="#9ccc65", bg="#2b2b2b").pack(side="left", padx=(12,0))
        tk.Label(stat_frame, textvariable=self.failed_var, fg="#ef5350", bg="#2b2b2b").pack(side="left", padx=(12,0))

        # 進度條
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=100, length=480)
        self.progress.pack(padx=pad, pady=(10, 4))
        self.progress["value"] = 0

        self.status_label = tk.Label(self, textvariable=self.status_var, fg="white", bg="#2b2b2b")
        self.status_label.pack(anchor="w", padx=pad)

        # 日誌
        log_label = tk.Label(self, text="日誌", fg="#bdbdbd", bg="#2b2b2b")
        log_label.pack(anchor="w", padx=pad, pady=(8, 0))
        self.log = tk.Text(self, height=10, width=60, bg="#1e1e1e", fg="#dcdcdc", relief="flat")
        self.log.pack(fill="both", expand=True, padx=pad, pady=(4, 0))
        self.log.configure(state="disabled")

        # 動作列
        action = tk.Frame(self, bg="#2b2b2b")
        action.pack(fill="x", pady=(8, pad))
        self.cancel_btn = tk.Button(action, text="取消", command=self._on_cancel, width=10)
        self.cancel_btn.pack(side="right", padx=pad)

    # ====== 與 CaseOverviewWindow 相容的方法 ======
    @classmethod
    def show_upload_dialog(cls, parent, total_cases: int, on_cancel=None):
        dlg = cls(parent, total_cases, on_cancel=on_cancel)
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
        self.log.insert("end", f"{msg}\n", ())
        self.log.tag_add(level, "end-1l linestart", "end-1l lineend")
        self.log.tag_config(level, foreground=color)
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def on_upload_complete(self, success: bool, summary: dict):
        # 完成後把取消變成「關閉」
        self.cancel_btn.configure(text="關閉", command=self.destroy)
        if success:
            ok = summary.get("uploaded", 0)
            fail = summary.get("failed", 0)
            total = summary.get("total", ok + fail)
            self.update_progress(100, f"完成：{ok}/{total} 成功，{fail} 失敗")
            self.add_log("上傳完成", "success")
        else:
            self.add_log(summary.get("message", "上傳失敗"), "error")

    # ====== 內部 ======
    def _on_cancel(self):
        if callable(self.on_cancel):
            try:
                self.on_cancel()
            except Exception:
                pass
        # 交由外部取消邏輯處理；本視窗不直接關閉
