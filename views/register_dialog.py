# -*- coding: utf-8 -*-
"""
views/auth/register_dialog.py
A Tkinter dialog for registering a new tenant (law firm).
Sends POST {API_BASE_URL}/api/auth/register with JSON body.

Fields:
- client_name (required)
- client_id   (required, 3~50, A-Za-z0-9_.-)
- password    (required, >=6)
- plan_type   (optional, default 'unpaid')

Success: show secret_code and close, or keep dialog if you want.
"""

import os
import json
import threading
import re
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import requests  # make sure 'requests' exists in requirements.txt
except Exception:
    requests = None

DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")

class RegisterDialog(tk.Toplevel):
    def __init__(self, master=None, api_base: str | None = None, on_success=None):
        super().__init__(master)
        self.title("註冊事務所")
        self.resizable(False, False)
        self.grab_set()  # modal window

        self.api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        self.on_success = on_success  # callback(dict)

        # ===== UI =====
        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="事務所名稱（必填）").grid(row=0, column=0, sticky="w", **pad)
        self.var_name = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_name, width=32).grid(row=0, column=1, **pad)

        ttk.Label(frm, text="帳號 ID（必填，3~50，英數/_.-）").grid(row=1, column=0, sticky="w", **pad)
        self.var_id = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_id, width=32).grid(row=1, column=1, **pad)

        ttk.Label(frm, text="密碼（必填，≥6）").grid(row=2, column=0, sticky="w", **pad)
        self.var_pwd = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_pwd, show="•", width=32).grid(row=2, column=1, **pad)

        ttk.Label(frm, text="方案（可選，不填=unpaid）").grid(row=3, column=0, sticky="w", **pad)
        self.var_plan = tk.StringVar(value="")  # 空字串 → 不傳，後端預設 unpaid
        plan_box = ttk.Combobox(frm, textvariable=self.var_plan, width=29, state="readonly",
                                values=["", "unpaid", "basic_5", "standard_10", "premium_20", "enterprise_50"])
        plan_box.grid(row=3, column=1, **pad)
        plan_box.set("")  # 默認空白 = 不傳

        self.lbl_status = ttk.Label(frm, text="", foreground="#666")
        self.lbl_status.grid(row=4, column=0, columnspan=2, sticky="w", **pad)

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, sticky="e", **pad)
        self.btn_submit = ttk.Button(btns, text="送出註冊", command=self.submit)
        self.btn_submit.grid(row=0, column=0, padx=(0,6))
        ttk.Button(btns, text="取消", command=self.safe_close).grid(row=0, column=1)

        self.bind("<Return>", lambda e: self.submit())
        self.bind("<Escape>", lambda e: self.safe_close())

        # keyboard focus
        self.after(100, lambda: self.focus_force())

    # ===== helpers =====
    def set_busy(self, busy: bool, msg: str = ""):
        if busy:
            self.btn_submit.configure(state="disabled")
            self.lbl_status.configure(text=msg or "處理中，請稍候…")
        else:
            self.btn_submit.configure(state="normal")
            self.lbl_status.configure(text=msg)

    def safe_close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def validate(self) -> tuple[bool, str]:
        name = self.var_name.get().strip()
        cid  = self.var_id.get().strip()
        pwd  = self.var_pwd.get()

        if not name:
            return False, "請輸入事務所名稱。"
        if not cid or not ID_PATTERN.match(cid):
            return False, "帳號 ID 需為 3~50 字，且僅能包含英數、底線、點與減號。"
        if not pwd or len(pwd) < 6:
            return False, "密碼長度需至少 6。"
        return True, ""

    # ===== networking =====
    def submit(self):
        ok, msg = self.validate()
        if not ok:
            messagebox.showwarning("欄位有誤", msg, parent=self)
            return
        if requests is None:
            messagebox.showerror("缺少依賴", "找不到 requests 套件，請先安裝。", parent=self)
            return

        payload = {
            "client_name": self.var_name.get().strip(),
            "client_id":   self.var_id.get().strip(),
            "password":    self.var_pwd.get(),
        }
        plan = self.var_plan.get().strip()
        if plan:  # 空字串不送，後端預設 unpaid；指定其他就送出
            payload["plan_type"] = plan

        url = f"{self.api_base}/api/auth/register"
        self.set_busy(True, "正在送出註冊…")

        def _worker():
            try:
                resp = requests.post(url, json=payload, timeout=20)
                data = resp.json() if resp.content else {}
                if resp.status_code >= 400:
                    raise RuntimeError(data.get("detail") or f"HTTP {resp.status_code}")

                # success
                secret = data.get("secret_code", "")
                msg_ok = f"註冊成功！\n\nclient_id：{data.get('client_id')}\nsecret_code：{secret}"
                self.after(0, lambda: self._on_success(data, msg_ok))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))
            finally:
                self.after(0, lambda: self.set_busy(False, ""))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_success(self, data: dict, message: str):
        messagebox.showinfo("成功", message, parent=self)
        if callable(self.on_success):
            try:
                self.on_success(data)
            except Exception:
                pass
        self.safe_close()

    def _on_error(self, err: str):
        messagebox.showerror("註冊失敗", str(err), parent=self)

# ===== helper to open dialog =====
def show_register_dialog(master=None, api_base: str | None = None, on_success=None):
    dlg = RegisterDialog(master=master, api_base=api_base, on_success=on_success)
    dlg.wait_window()
