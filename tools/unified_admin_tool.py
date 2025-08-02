#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# unified_admin_tool.py
"""
📍 供應商統一管理工具
使用專案統一樣式設計
"""

import base64
import hashlib
import json
import os
import sys
import tkinter as tk
import uuid
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

# 添加專案路徑
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

try:
    from config.settings import AppConfig
    from views.base_window import BaseWindow
    from views.dialogs import UnifiedMessageDialog
    USE_PROJECT_STYLE = True
except ImportError:
    # 如果無法導入專案模組，使用簡化樣式
    class AppConfig:
        COLORS = {
            'window_bg': '#383838',
            'title_bg': '#8B8B8B',
            'title_fg': 'white',
            'button_bg': '#8B8B8B',
            'button_fg': 'white',
            'text_color': 'white'
        }
        FONTS = {
            'title': ('Microsoft JhengHei', 11, 'bold'),
            'button': ('Microsoft JhengHei', 9),
            'text': ('Microsoft JhengHei', 9)
        }
    USE_PROJECT_STYLE = False


class UnifiedAdminTool:
    """統一授權管理工具（使用專案統一樣式）"""

    def __init__(self):
        self.window = tk.Tk()
        self.drag_data = {"x": 0, "y": 0}

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.customers_file = os.path.join(script_dir, "all_customers.json")
        self.customers = self._load_customers()
        self.secret_salt = "CaseManagement2024"

        self._setup_window()
        self._create_ui()

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title("📋 統一授權管理工具")
        self.window.geometry("900x700")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])

        if USE_PROJECT_STYLE:
            self.window.overrideredirect(True)
            self._center_window()

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 450
        y = (self.window.winfo_screenheight() // 2) - 350
        self.window.geometry(f"900x700+{x}+{y}")

    def _load_customers(self):
        """載入客戶資料"""
        if os.path.exists(self.customers_file):
            try:
                with open(self.customers_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_customers(self):
        """儲存客戶資料"""
        try:
            with open(self.customers_file, 'w', encoding='utf-8') as f:
                json.dump(self.customers, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._show_error(f"儲存客戶資料失敗：{str(e)}")

    def _show_success(self, message):
        """顯示成功訊息"""
        if USE_PROJECT_STYLE:
            try:
                UnifiedMessageDialog.show_success(self.window, message)
                return
            except:
                pass
        messagebox.showinfo("✅ 成功", message)

    def _show_error(self, message):
        """顯示錯誤訊息"""
        if USE_PROJECT_STYLE:
            try:
                UnifiedMessageDialog.show_error(self.window, message)
                return
            except:
                pass
        messagebox.showerror("❌ 錯誤", message)

    def _create_ui(self):
        """建立管理介面"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        if USE_PROJECT_STYLE:
            # 自定義標題列
            title_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['title_bg'], height=25)
            title_frame.pack(fill='x')
            title_frame.pack_propagate(False)

            title_label = tk.Label(
                title_frame,
                text="📋 統一授權管理工具",
                bg=AppConfig.COLORS['title_bg'],
                fg=AppConfig.COLORS['title_fg'],
                font=AppConfig.FONTS['title']
            )
            title_label.pack(side='left', padx=10)

            close_btn = tk.Button(
                title_frame,
                text="✕",
                bg=AppConfig.COLORS['title_bg'],
                fg=AppConfig.COLORS['title_fg'],
                font=('Arial', 12, 'bold'),
                bd=0,
                width=3,
                command=self.window.destroy
            )
            close_btn.pack(side='right', padx=10)

            # 設定拖曳功能
            self._setup_drag(title_frame, title_label)

            # 內容區域
            content_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
            content_frame.pack(fill='both', expand=True, padx=10, pady=10)
        else:
            # 標準標題
            title_label = tk.Label(
                main_frame,
                text="📋 統一授權管理工具",
                font=("Arial", 16, "bold"),
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color']
            )
            title_label.pack(pady=10)
            content_frame = main_frame

        # 建立筆記本控件
        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # 生成授權頁面
        generate_frame = ttk.Frame(notebook)
        notebook.add(generate_frame, text="🎫 生成授權碼")
        self._create_generate_tab(generate_frame)

        # 客戶管理頁面
        customer_frame = ttk.Frame(notebook)
        notebook.add(customer_frame, text="👥 客戶管理")
        self._create_customer_tab(customer_frame)

        # 說明頁面
        help_frame = ttk.Frame(notebook)
        notebook.add(help_frame, text="❓ 使用說明")
        self._create_help_tab(help_frame)

    def _setup_drag(self, title_frame, title_label):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", on_drag)
        title_label.bind("<Button-1>", start_drag)
        title_label.bind("<B1-Motion>", on_drag)

    def _create_generate_tab(self, parent):
        """建立授權生成頁面"""
        # 客戶基本資訊
        basic_frame = tk.LabelFrame(parent, text="👤 客戶基本資訊", font=AppConfig.FONTS['button'])
        basic_frame.pack(pady=10, padx=20, fill='x')

        tk.Label(basic_frame, text="客戶名稱：", font=AppConfig.FONTS['text']).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.name_entry = tk.Entry(basic_frame, width=30, font=AppConfig.FONTS['text'])
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(basic_frame, text="電子郵件：", font=AppConfig.FONTS['text']).grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.email_entry = tk.Entry(basic_frame, width=30, font=AppConfig.FONTS['text'])
        self.email_entry.grid(row=1, column=1, padx=5, pady=5)

        # 授權類型選擇
        type_frame = tk.LabelFrame(parent, text="🎫 授權類型", font=AppConfig.FONTS['button'])
        type_frame.pack(pady=10, padx=20, fill='x')

        self.license_type = tk.StringVar(value="single")

        tk.Radiobutton(type_frame, text="💻 單設備授權", variable=self.license_type,
                      value="single", command=self._on_type_change,
                      font=AppConfig.FONTS['text']).grid(row=0, column=0, sticky='w', padx=10, pady=5)

        tk.Radiobutton(type_frame, text="🖥️🖥️🖥️ 多設備授權", variable=self.license_type,
                      value="multi", command=self._on_type_change,
                      font=AppConfig.FONTS['text']).grid(row=0, column=1, sticky='w', padx=10, pady=5)

        tk.Radiobutton(type_frame, text="🚀 升級授權", variable=self.license_type,
                      value="upgrade", command=self._on_type_change,
                      font=AppConfig.FONTS['text']).grid(row=0, column=2, sticky='w', padx=10, pady=5)

        # 授權參數設定
        param_frame = tk.LabelFrame(parent, text="⚙️ 授權參數", font=AppConfig.FONTS['button'])
        param_frame.pack(pady=10, padx=20, fill='x')

        # 硬體ID
        tk.Label(param_frame, text="硬體ID：", font=AppConfig.FONTS['text']).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.hardware_entry = tk.Entry(param_frame, width=30, font=AppConfig.FONTS['text'])
        self.hardware_entry.grid(row=0, column=1, padx=5, pady=5)
        self.hardware_label = tk.Label(param_frame, text="（單設備和升級授權必填）",
                                      font=('Arial', 9), fg='gray')
        self.hardware_label.grid(row=0, column=2, sticky='w', padx=5)

        # 設備數量
        tk.Label(param_frame, text="設備數量：", font=AppConfig.FONTS['text']).grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.devices_var = tk.StringVar(value="3")
        self.devices_combo = ttk.Combobox(param_frame, textvariable=self.devices_var,
                                         values=["2", "3", "5", "10", "20", "50"], width=10)
        self.devices_combo.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.devices_label = tk.Label(param_frame, text="（多設備和升級授權需要）",
                                     font=('Arial', 9), fg='gray')
        self.devices_label.grid(row=1, column=2, sticky='w', padx=5)

        # 授權期限
        tk.Label(param_frame, text="授權期限：", font=AppConfig.FONTS['text']).grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.duration_var = tk.StringVar(value="12")
        duration_combo = ttk.Combobox(param_frame, textvariable=self.duration_var,
                                     values=["1", "3", "6", "12", "24", "36"], width=10)
        duration_combo.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        tk.Label(param_frame, text="個月", font=AppConfig.FONTS['text']).grid(row=2, column=2, sticky='w', padx=5)

        # 生成按鈕
        tk.Button(param_frame, text="🎫 生成授權碼", command=self._generate_license,
                 width=20, height=2, font=AppConfig.FONTS['button'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).grid(row=3, column=0, columnspan=3, pady=20)

        # 結果顯示
        self.result_text = tk.Text(parent, height=10, width=80, font=AppConfig.FONTS['text'])
        self.result_text.pack(pady=10, padx=20, fill='both', expand=True)

        # 操作按鈕
        button_frame = tk.Frame(parent)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="📋 複製授權碼", command=self._copy_license,
                 width=15, font=AppConfig.FONTS['text'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).pack(side='left', padx=5)

        tk.Button(button_frame, text="🗑️ 清除結果",
                 command=lambda: self.result_text.delete(1.0, tk.END),
                 width=15, font=AppConfig.FONTS['text'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).pack(side='left', padx=5)

        # 初始化界面狀態
        self._on_type_change()

    def _on_type_change(self):
        """授權類型改變時更新界面"""
        license_type = self.license_type.get()

        if license_type == "single":
            self.hardware_entry.config(state='normal', bg='white')
            self.hardware_label.config(text="（必填）", fg='red')
            self.devices_combo.config(state='disabled')
            self.devices_label.config(text="（不需要）", fg='gray')
        elif license_type == "multi":
            self.hardware_entry.config(state='disabled', bg='#f0f0f0')
            self.hardware_label.config(text="（不需要）", fg='gray')
            self.devices_combo.config(state='normal')
            self.devices_label.config(text="（必填）", fg='red')
        elif license_type == "upgrade":
            self.hardware_entry.config(state='normal', bg='white')
            self.hardware_label.config(text="（原設備硬體ID，必填）", fg='red')
            self.devices_combo.config(state='normal')
            self.devices_label.config(text="（升級後設備數，必填）", fg='red')

    def _generate_license(self):
        """生成授權碼"""
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        license_type = self.license_type.get()

        if not all([name, email]):
            self._show_error("請填寫客戶名稱和電子郵件")
            return

        try:
            if license_type == "single":
                result = self._generate_single_license(name, email)
            elif license_type == "multi":
                result = self._generate_multi_license(name, email)
            elif license_type == "upgrade":
                result = self._generate_upgrade_license(name, email)

            if result:
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, result)

                # 清空輸入欄位
                self.name_entry.delete(0, tk.END)
                self.email_entry.delete(0, tk.END)
                self.hardware_entry.delete(0, tk.END)

        except Exception as e:
            self._show_error(f"生成授權碼失敗：{str(e)}")

    def _generate_single_license(self, name, email):
        """生成單設備授權"""
        hardware_id = self.hardware_entry.get().strip()
        duration = int(self.duration_var.get())

        if not hardware_id:
            self._show_error("單設備授權需要硬體ID")
            return None

        # 生成單設備授權碼
        expire_date = datetime.now() + timedelta(days=duration * 30)
        expire_date_str = expire_date.isoformat()

        checksum = hashlib.sha256(
            f"SINGLE_{hardware_id}_{expire_date_str}_{self.secret_salt}".encode()
        ).hexdigest()[:8]

        license_data = f"SINGLE|{hardware_id}|{expire_date_str}|{checksum}"
        license_key = base64.b64encode(license_data.encode()).decode()

        # 儲存客戶資料
        customer_id = f"SINGLE_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.customers[customer_id] = {
            'name': name,
            'email': email,
            'type': 'single',
            'hardware_id': hardware_id,
            'license_key': license_key,
            'duration_months': duration,
            'expire_date': expire_date_str,
            'created_date': datetime.now().isoformat()
        }
        self._save_customers()

        return f"""
✅ 單設備授權碼生成成功！

👤 客戶資訊：
姓名：{name}
郵件：{email}
硬體ID：{hardware_id}

🎫 授權詳情：
授權碼：{license_key}
授權類型：單設備授權（僅限一台電腦）
授權期限：{duration} 個月
到期日：{expire_date.strftime('%Y-%m-%d %H:%M:%S')}
生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 請將授權碼提供給客戶使用。
        """

    def _generate_multi_license(self, name, email):
        """生成多設備授權"""
        max_devices = int(self.devices_var.get())
        duration = int(self.duration_var.get())

        # 生成多設備授權碼
        license_id = str(uuid.uuid4()).replace('-', '')[:16].upper()
        expire_date = datetime.now() + timedelta(days=duration * 30)
        expire_date_str = expire_date.isoformat()

        checksum = hashlib.sha256(
            f"MULTI_{license_id}_{max_devices}_{expire_date_str}_{self.secret_salt}".encode()
        ).hexdigest()[:8]

        license_data = f"MULTI|{license_id}|{max_devices}|{expire_date_str}|{checksum}"
        license_key = base64.b64encode(license_data.encode()).decode()

        # 儲存客戶資料
        customer_id = f"MULTI_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.customers[customer_id] = {
            'name': name,
            'email': email,
            'type': 'multi',
            'license_id': license_id,
            'max_devices': max_devices,
            'license_key': license_key,
            'duration_months': duration,
            'expire_date': expire_date_str,
            'created_date': datetime.now().isoformat()
        }
        self._save_customers()

        return f"""
✅ 多設備授權碼生成成功！

👤 客戶資訊：
姓名：{name}
郵件：{email}

🎫 授權詳情：
授權碼：{license_key}
授權類型：多設備授權
最大設備數：{max_devices} 台
授權ID：{license_id}
授權期限：{duration} 個月
到期日：{expire_date.strftime('%Y-%m-%d %H:%M:%S')}
生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 客戶可在最多 {max_devices} 台設備上使用此授權碼。
        """

    def _generate_upgrade_license(self, name, email):
        """生成升級授權"""
        original_hardware_id = self.hardware_entry.get().strip()
        new_max_devices = int(self.devices_var.get())

        if not original_hardware_id:
            self._show_error("升級授權需要原設備的硬體ID")
            return None

        # 生成升級授權碼
        checksum = hashlib.sha256(
            f"UPGRADE_{original_hardware_id}_{new_max_devices}_{self.secret_salt}".encode()
        ).hexdigest()[:8]

        license_data = f"UPGRADE|{original_hardware_id}|{new_max_devices}|{checksum}"
        upgrade_key = base64.b64encode(license_data.encode()).decode()

        # 儲存升級記錄
        upgrade_id = f"UPGRADE_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.customers[upgrade_id] = {
            'name': name,
            'email': email,
            'type': 'upgrade',
            'original_hardware_id': original_hardware_id,
            'new_max_devices': new_max_devices,
            'upgrade_key': upgrade_key,
            'created_date': datetime.now().isoformat()
        }
        self._save_customers()

        return f"""
✅ 升級授權碼生成成功！

👤 客戶資訊：
姓名：{name}
郵件：{email}
原始硬體ID：{original_hardware_id}

🚀 升級詳情：
升級授權碼：{upgrade_key}
升級類型：單設備 → 多設備授權
升級後設備數：{new_max_devices} 台
生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 使用說明：
1. 客戶在原設備上輸入此升級授權碼進行升級
2. 升級後保持原有的授權到期時間
3. 客戶可在其他設備上使用相同升級授權碼註冊額外設備
4. 總設備數不可超過 {new_max_devices} 台
        """

    def _copy_license(self):
        """複製授權碼"""
        try:
            content = self.result_text.get(1.0, tk.END)
            # 尋找授權碼
            lines = content.split('\n')
            license_lines = [line for line in lines if ('授權碼：' in line or '升級授權碼：' in line)]

            if license_lines:
                license_key = license_lines[0].split('：')[1].strip()
                self.window.clipboard_clear()
                self.window.clipboard_append(license_key)
                self._show_success("授權碼已複製到剪貼簿")
            else:
                self._show_error("未找到授權碼")
        except Exception as e:
            self._show_error(f"複製失敗：{str(e)}")

    def _create_customer_tab(self, parent):
        """建立客戶管理頁面"""
        # 客戶列表
        list_frame = tk.LabelFrame(parent, text="👥 客戶列表", font=AppConfig.FONTS['button'])
        list_frame.pack(pady=10, padx=20, fill='both', expand=True)

        # 建立表格
        columns = ('客戶名稱', '類型', '詳情', '生成日期', '狀態')
        self.customer_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.customer_tree.heading(col, text=col)
            self.customer_tree.column(col, width=150, anchor='center')

        self.customer_tree.pack(pady=10, fill='both', expand=True)

        # 重新整理客戶列表
        self._refresh_customer_list()

        # 按鈕區域
        button_frame = tk.Frame(list_frame)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="👁️ 查看詳情", command=self._show_customer_detail,
                 width=12, font=AppConfig.FONTS['text'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).pack(side='left', padx=5)

        tk.Button(button_frame, text="🔄 重新整理", command=self._refresh_customer_list,
                 width=12, font=AppConfig.FONTS['text'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).pack(side='left', padx=5)

        tk.Button(button_frame, text="🗑️ 刪除記錄", command=self._delete_customer,
                 width=12, font=AppConfig.FONTS['text'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).pack(side='left', padx=5)

    def _refresh_customer_list(self):
        """重新整理客戶列表"""
        # 清空現有項目
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        # 填入客戶資料
        for customer_id, customer in self.customers.items():
            customer_type = customer['type']

            if customer_type == 'single':
                detail = f"硬體ID: {customer['hardware_id'][:8]}..."
                type_display = "💻 單設備"
            elif customer_type == 'multi':
                detail = f"設備數: {customer['max_devices']} 台"
                type_display = "🖥️ 多設備"
            elif customer_type == 'upgrade':
                detail = f"升級至: {customer['new_max_devices']} 台"
                type_display = "🚀 升級"
            else:
                detail = "未知"
                type_display = "❓ 未知"

            created_date = datetime.fromisoformat(customer['created_date'])

            # 判斷狀態
            if customer_type in ['single', 'multi']:
                try:
                    expire_date = datetime.fromisoformat(customer['expire_date'])
                    status = "✅ 有效" if datetime.now() < expire_date else "❌ 已過期"
                except:
                    status = "❓ 未知"
            else:
                status = "🚀 升級碼"

            self.customer_tree.insert('', tk.END, values=(
                customer['name'],
                type_display,
                detail,
                created_date.strftime('%Y-%m-%d'),
                status
            ), tags=(customer_id,))

    def _show_customer_detail(self):
        """顯示客戶詳情"""
        selection = self.customer_tree.selection()
        if not selection:
            self._show_error("請選擇一個客戶")
            return

        item = self.customer_tree.item(selection[0])
        customer_id = item['tags'][0]
        customer = self.customers[customer_id]

        # 建立詳情視窗
        detail_window = tk.Toplevel(self.window)
        detail_window.title(f"客戶詳情 - {customer['name']}")
        detail_window.geometry("600x500")
        detail_window.configure(bg=AppConfig.COLORS['window_bg'])

        # 顯示詳細資訊
        if customer['type'] == 'single':
            detail_text = f"""
👤 客戶名稱：{customer['name']}
📧 電子郵件：{customer['email']}
🎫 授權類型：單設備授權
🖥️ 硬體ID：{customer['hardware_id']}
📅 授權期限：{customer['duration_months']} 個月
⏰ 到期日：{customer['expire_date']}
📋 授權碼：{customer['license_key']}
🕐 建立時間：{customer['created_date']}
            """
        elif customer['type'] == 'multi':
            detail_text = f"""
👤 客戶名稱：{customer['name']}
📧 電子郵件：{customer['email']}
🎫 授權類型：多設備授權
🖥️ 最大設備數：{customer['max_devices']} 台
🆔 授權ID：{customer['license_id']}
📅 授權期限：{customer['duration_months']} 個月
⏰ 到期日：{customer['expire_date']}
📋 授權碼：{customer['license_key']}
🕐 建立時間：{customer['created_date']}
            """
        elif customer['type'] == 'upgrade':
            detail_text = f"""
👤 客戶名稱：{customer['name']}
📧 電子郵件：{customer['email']}
🎫 授權類型：升級授權
🖥️ 原始硬體ID：{customer['original_hardware_id']}
📈 升級後設備數：{customer['new_max_devices']} 台
📋 升級授權碼：{customer['upgrade_key']}
🕐 建立時間：{customer['created_date']}
            """

        text_widget = tk.Text(detail_window, wrap=tk.WORD, font=AppConfig.FONTS['text'],
                             bg='white', fg='black')
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, detail_text)
        text_widget.config(state='disabled')

        # 複製授權碼按鈕
        def copy_customer_license():
            key_field = 'license_key' if customer['type'] != 'upgrade' else 'upgrade_key'
            detail_window.clipboard_clear()
            detail_window.clipboard_append(customer[key_field])
            self._show_success("授權碼已複製")

        button_frame = tk.Frame(detail_window, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="📋 複製授權碼", command=copy_customer_license,
                 width=15, font=AppConfig.FONTS['text'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).pack(side='left', padx=5)

        tk.Button(button_frame, text="❌ 關閉", command=detail_window.destroy,
                 width=15, font=AppConfig.FONTS['text'],
                 bg=AppConfig.COLORS['button_bg'], fg=AppConfig.COLORS['button_fg']).pack(side='left', padx=5)

    def _delete_customer(self):
        """刪除客戶記錄"""
        selection = self.customer_tree.selection()
        if not selection:
            self._show_error("請選擇一個客戶")
            return

        item = self.customer_tree.item(selection[0])
        customer_id = item['tags'][0]
        customer_name = self.customers[customer_id]['name']

        if messagebox.askyesno("❓ 確認刪除", f"確定要刪除客戶 {customer_name} 的記錄嗎？"):
            del self.customers[customer_id]
            self._save_customers()
            self._refresh_customer_list()
            self._show_success(f"已刪除客戶 {customer_name} 的記錄")

    def _create_help_tab(self, parent):
        """建立使用說明頁面"""
        help_text = """
📋 統一授權管理工具使用說明

🎯 功能概述：
此工具可以生成三種類型的授權碼，滿足不同客戶需求：

1️⃣ 💻 單設備授權
   • 適用：個人用戶、固定辦公
   • 需要：客戶的硬體ID
   • 特點：與特定電腦綁定，安全性高

2️⃣ 🖥️🖥️🖥️ 多設備授權
   • 適用：團隊用戶、多辦公室
   • 需要：設定設備數量
   • 特點：可在多台電腦使用，靈活管理

3️⃣ 🚀 升級授權
   • 適用：現有單設備用戶想升級
   • 需要：原設備硬體ID + 新設備數量
   • 特點：保持原授權時間，平滑升級

📋 操作流程：

第一步：客戶取得硬體ID
• 客戶執行「hardware_id_tool_standalone.py」
• 複製硬體ID並提供給您

第二步：您生成授權碼
• 在「生成授權碼」頁面填寫客戶資訊
• 選擇授權類型並填寫相應參數
• 點擊「生成授權碼」按鈕
• 複製授權碼提供給客戶

第三步：客戶使用授權碼
• 客戶執行「main_unified.py」
• 輸入您提供的授權碼
• 系統自動識別並處理

💡 提示：
• 單設備授權需要硬體ID，多設備授權不需要
• 升級授權既需要原硬體ID也需要新設備數量
• 所有客戶記錄都會自動保存在「all_customers.json」文件中
• 可在「客戶管理」頁面查看和管理所有客戶記錄

❓ 如有問題，請參考主程式中的詳細說明。
        """

        text_widget = tk.Text(parent, wrap=tk.WORD, font=AppConfig.FONTS['text'],
                             bg='white', fg='black')
        text_widget.pack(fill='both', expand=True, padx=20, pady=20)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state='disabled')

    def run(self):
        """執行管理工具"""
        self.window.mainloop()


if __name__ == "__main__":
    app = UnifiedAdminTool()
    app.run()