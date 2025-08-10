# -*- coding: utf-8 -*-
# views/register_dialog.py — 無邊框註冊視窗（自訂標題） + 串接 /api/auth/register
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
import requests

try:
    from config.settings import AppConfig
except Exception:
    class AppConfig:
        COLORS = {"window_bg": "#FFFFFF", "title_bg": "#2c3e50", "title_fg": "#ecf0f1", "text_color": "#2c3e50",
                  "button_bg": "#3498db", "button_fg": "#ffffff"}
        FONTS  = {"title": ("Microsoft JhengHei", 12, "bold"),
                  "text": ("Microsoft JhengHei", 10),
                  "button": ("Microsoft JhengHei", 10, "bold")}

def _center_on_parent(parent: tk.Misc, w: int, h: int) -> str:
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

class RegisterDialog:
    """立即無邊框：在 Toplevel 建立後立刻 overrideredirect(True)"""
    def __init__(self, parent, api_base_url: str):
        self.parent = parent
        self.api_base_url = api_base_url.rstrip("/")
        self.result = None

        self.win = tk.Toplevel(parent)
        self.win.withdraw()
        try:
            self.win.overrideredirect(True)  # 立刻無邊框
        except Exception:
            pass

        self.win.configure(bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        self.win.geometry(_center_on_parent(parent, 340, 280))

        self._build_title_bar("註冊用戶")

        body = tk.Frame(self.win, bg=AppConfig.COLORS.get("window_bg", "#FFFFFF"))
        body.pack(fill="both", expand=True, padx=16, pady=12)
        self._build_form(body)

        self.win.deiconify()
        try: self.win.attributes("-topmost", True)
        except Exception: pass
        self.win.lift(parent)
        try: self.win.grab_set()
        except Exception: pass
        self.win.update_idletasks()
        self.win.focus_force()

        self.win.bind("<Escape>", lambda e: self.close())
        self.win.bind("<Return>", lambda e: self._submit())

    # ---------- UI ----------
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

        drag = {"x":0, "y":0}
        def start_drag(e): drag.update(x=e.x, y=e.y)
        def on_drag(e):
            nx = self.win.winfo_x() + (e.x - drag["x"])
            ny = self.win.winfo_y() + (e.y - drag["y"])
            self.win.geometry(f"+{nx}+{ny}")
        for w in (bar, lbl):
            w.bind("<Button-1>", start_drag)
            w.bind("<B1-Motion>", on_drag)

    def _build_form(self, body: tk.Frame):
        tk.Label(body, text="事務所名稱",
                 font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                 bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'),
                 fg=AppConfig.COLORS.get('text_color', '#2c3e50')).grid(row=0, column=0, sticky="w", pady=(0,4))
        self.var_name = tk.StringVar()
        self.entry_name = tk.Entry(body, textvariable=self.var_name,
                                   font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)), width=26)
        self.entry_name.grid(row=1, column=0, sticky="we", pady=(0,8))

        tk.Label(body, text="帳號（client_id）",
                 font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                 bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'),
                 fg=AppConfig.COLORS.get('text_color', '#2c3e50')).grid(row=2, column=0, sticky="w", pady=(0,4))
        self.var_id = tk.StringVar()
        self.entry_id = tk.Entry(body, textvariable=self.var_id,
                                 font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)), width=26)
        self.entry_id.grid(row=3, column=0, sticky="we", pady=(0,8))

        tk.Label(body, text="密碼",
                 font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                 bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'),
                 fg=AppConfig.COLORS.get('text_color', '#2c3e50')).grid(row=4, column=0, sticky="w", pady=(0,4))
        self.var_pwd = tk.StringVar()
        self.entry_pwd = tk.Entry(body, textvariable=self.var_pwd,
                                  font=AppConfig.FONTS.get('text', ('Microsoft JhengHei', 10)),
                                  show="*", width=26)
        self.entry_pwd.grid(row=5, column=0, sticky="we", pady=(0,8))

        body.grid_columnconfigure(0, weight=1)

        btns = tk.Frame(body, bg=AppConfig.COLORS.get('window_bg', '#FFFFFF'))
        btns.grid(row=6, column=0, pady=(6, 0))
        tk.Button(btns, text="送出註冊",
                  font=AppConfig.FONTS.get('button', ('Microsoft JhengHei', 10, 'bold')),
                  bg=AppConfig.COLORS.get('button_bg', '#3498db'),
                  fg=AppConfig.COLORS.get('button_fg', '#ffffff'),
                  width=10, command=self._submit).pack(side="left", padx=10)
        tk.Button(btns, text="取消",
                  font=AppConfig.FONTS.get('button', ('Microsoft JhengHei', 10, 'bold')),
                  bg=AppConfig.COLORS.get('button_bg', '#3498db'),
                  fg=AppConfig.COLORS.get('button_fg', '#ffffff'),
                  width=10, command=self.close).pack(side="left", padx=10)

        self.entry_name.focus_set()
        self.entry_name.icursor("end")

    # ---------- 行為 ----------
    def _submit(self):
        name = self.var_name.get().strip()
        cid  = self.var_id.get().strip()
        pwd  = self.var_pwd.get().strip()

        if not name:
            messagebox.showwarning("提示", "請輸入事務所名稱", parent=self.win); return
        if len(cid) < 3:
            messagebox.showwarning("提示", "帳號長度至少 3 個字元", parent=self.win); return
        if len(pwd) < 6:
            messagebox.showwarning("提示", "密碼長度至少 6 個字元", parent=self.win); return

        # ✅ 改這裡：打 /api/auth/register（後端會預設 plan_type=unpaid → tenant_status=NULL）
        url = f"{self.api_base_url}/api/auth/register"
        print(f"[RegisterDialog] POST -> {url}")
        try:
            resp = requests.post(
                url,
                json={"client_name": name, "client_id": cid, "password": pwd},
                timeout=12
            )
        except requests.exceptions.ConnectTimeout:
            messagebox.showerror("連線逾時", f"連不上伺服器（timeout）。\nURL: {url}", parent=self.win); return
        except requests.exceptions.ConnectionError as e:
            messagebox.showerror("連線失敗", f"無法連線：{e}\nURL: {url}", parent=self.win); return
        except Exception as e:
            messagebox.showerror("錯誤", f"請求送出前就失敗：{e}\nURL: {url}", parent=self.win); return

        if resp.status_code == 201:
            data = resp.json()
            # 回傳給登入視窗用（自動帶回帳密）
            self.result = {
                "success": True,
                "client_id": data.get("client_id"),
                "secret_code": data.get("secret_code"),
                "password": pwd
            }
            # 可選：提示成功再關閉

            self.close()
        else:
            try:
                detail = resp.json().get("detail")
            except Exception:
                detail = resp.text
            messagebox.showwarning("註冊失敗", f"HTTP {resp.status_code}\nURL: {url}\n{detail or '無訊息'}", parent=self.win)

    def close(self):
        try: self.win.grab_release()
        except Exception: pass
        self.win.destroy()
