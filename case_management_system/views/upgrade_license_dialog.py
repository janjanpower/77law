import tkinter as tk
from tkinter import messagebox
from config.settings import AppConfig

class UpgradeLicenseDialog:
    """升級授權對話框"""

    def __init__(self, parent=None, current_license_info=None):
        self.result = None
        self.upgrade_key = ""
        self.current_license_info = current_license_info

        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("授權升級")
        self.window.geometry("600x500")
        self.window.resizable(False, False)

        # 置中顯示
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 300
        y = (self.window.winfo_screenheight() // 2) - 250
        self.window.geometry(f"600x500+{x}+{y}")

        self._create_ui()

        if parent:
            self.window.transient(parent)
            self.window.grab_set()

    def _create_ui(self):
        """建立UI介面"""
        # 標題
        title_label = tk.Label(self.window, text="授權升級服務",
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        # 當前授權資訊
        if self.current_license_info:
            current_frame = tk.LabelFrame(self.window, text="當前授權資訊", font=("Arial", 12))
            current_frame.pack(pady=10, padx=40, fill='x')

            expire_date = self.current_license_info.get('expire_date', '未知')
            remaining_days = self.current_license_info.get('remaining_days', 0)

            current_info = f"""
授權類型：單設備授權
到期日：{expire_date.strftime('%Y-%m-%d') if hasattr(expire_date, 'strftime') else expire_date}
剩餘時間：{remaining_days} 天
            """

            tk.Label(current_frame, text=current_info, justify='left',
                    font=("Arial", 10)).pack(anchor='w', padx=10, pady=10)

        # 升級說明
        info_text = """
🚀 升級為多設備授權的優勢：

✅ 多台電腦同時使用：可在辦公室、家裡、筆電等多台設備上使用
✅ 保持原有授權時間：升級後到期時間不變，不會損失剩餘時間
✅ 靈活設備管理：支援設備更換，適合團隊協作
✅ 一次購買長期使用：無需為每台設備單獨購買授權

升級流程：
1. 聯繫供應商申請升級授權碼（需告知設備數量需求）
2. 在此輸入升級授權碼完成升級
3. 在其他設備上使用相同授權碼註冊額外設備

注意：升級後將保持您當前授權的到期時間
        """

        info_label = tk.Label(self.window, text=info_text, font=("Arial", 10),
                             justify='left', wraplength=520)
        info_label.pack(pady=10, padx=40)

        # 升級授權碼輸入
        input_frame = tk.Frame(self.window)
        input_frame.pack(pady=20)

        tk.Label(input_frame, text="升級授權碼：", font=("Arial", 12)).pack(anchor='w')

        self.upgrade_entry = tk.Entry(input_frame, width=60, font=("Arial", 11))
        self.upgrade_entry.pack(pady=5)
        self.upgrade_entry.focus()

        # 授權碼示例
        example_frame = tk.LabelFrame(self.window, text="升級授權碼格式示例", font=("Arial", 10))
        example_frame.pack(pady=10, padx=40, fill='x')

        example_text = "VVBHV1VRRUl8QUJDREU0NTY3ODkwfDN8WEFCQ0RFRkc="

        tk.Label(example_frame, text=example_text, font=("Arial", 9),
                fg='blue').pack(pady=5, padx=10)

        # 按鈕區域
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=30)

        tk.Button(button_frame, text="確認升級", command=self._apply_upgrade,
                 width=12, height=2, font=("Arial", 11),
                 bg='#4CAF50', fg='white').pack(side='left', padx=10)

        tk.Button(button_frame, text="聯繫供應商", command=self._contact_supplier,
                 width=12, height=2, font=("Arial", 11)).pack(side='left', padx=10)

        tk.Button(button_frame, text="取消", command=self._cancel,
                 width=12, height=2, font=("Arial", 11)).pack(side='left', padx=10)

        # 綁定Enter鍵
        self.upgrade_entry.bind('<Return>', lambda e: self._apply_upgrade())

    def _apply_upgrade(self):
        """應用升級"""
        upgrade_key = self.upgrade_entry.get().strip()

        if not upgrade_key:
            messagebox.showerror("錯誤", "請輸入升級授權碼")
            return

        try:
            from auth.license_upgrade_manager import LicenseUpgradeManager
            upgrade_manager = LicenseUpgradeManager()

            success, message = upgrade_manager.apply_upgrade(upgrade_key)

            if success:
                messagebox.showinfo("升級成功", message)
                self.result = True
                self.upgrade_key = upgrade_key
                self.window.destroy()
            else:
                messagebox.showerror("升級失敗", message)

        except Exception as e:
            messagebox.showerror("錯誤", f"升級過程發生錯誤：{str(e)}")

    def _contact_supplier(self):
        """聯繫供應商"""
        contact_info = """
聯繫供應商申請升級授權：

📧 郵件：your-email@example.com
📞 電話：0900-000-000
💬 LINE：@your-line-id

申請升級時請提供：
1. 您的客戶名稱或郵件
2. 當前使用的硬體ID
3. 需要的設備數量（2-50台）
4. 特殊需求或備註

我們將在24小時內為您生成專屬的升級授權碼。
        """

        messagebox.showinfo("聯繫資訊", contact_info)

    def _cancel(self):
        """取消"""
        self.result = False
        self.window.destroy()
