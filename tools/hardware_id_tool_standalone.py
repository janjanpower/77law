# hardware_id_tool_standalone.py
"""
📍 1. 客戶取得硬體ID的工具（獨立執行）
客戶使用這個檔案來取得他們的硬體ID
"""

import tkinter as tk
from tkinter import messagebox
import uuid
import platform
import hashlib

class HardwareIDTool:
    """硬體ID查詢工具（客戶端使用）"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("硬體ID查詢工具")
        self.window.geometry("600x400")
        self.window.resizable(False, False)

        # 置中顯示
        x = (self.window.winfo_screenwidth() // 2) - 300
        y = (self.window.winfo_screenheight() // 2) - 200
        self.window.geometry(f"600x1000+{x}+{y}")

        self.hardware_id = self._get_hardware_id()
        self._create_ui()

    def _get_hardware_id(self):
        """取得硬體ID"""
        try:
            mac = uuid.getnode()
            computer_name = platform.node()
            unique_string = f"{mac}_{computer_name}"
            return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        except:
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]

    def _create_ui(self):
        """建立使用者介面"""
        # 標題
        title_label = tk.Label(self.window, text="硬體ID查詢工具",
                              font=("Arial", 18, "bold"))
        title_label.pack(pady=20)

        # 說明文字
        info_text = """
🖥️ 此工具用於取得您電腦的唯一硬體識別碼

📋 使用步驟：
1. 點擊下方的「複製硬體ID」按鈕
2. 將硬體ID提供給軟體供應商
3. 供應商會根據此ID生成您的專屬授權碼
4. 取得授權碼後即可開始使用軟體

⚠️ 注意：請在需要使用軟體的電腦上執行此工具
        """

        info_label = tk.Label(self.window, text=info_text,
                             font=("Arial", 11), justify='left')
        info_label.pack(pady=20, padx=20)

        # 硬體ID顯示區域
        id_frame = tk.LabelFrame(self.window, text="您的硬體ID", font=("Arial", 12))
        id_frame.pack(pady=20, padx=40, fill='x')

        id_display_frame = tk.Frame(id_frame)
        id_display_frame.pack(pady=15)

        self.id_entry = tk.Entry(id_display_frame, width=25, font=("Arial", 14, "bold"),
                                justify='center', state='readonly', bg='#f0f0f0')
        self.id_entry.pack(side='left', padx=5)

        self.id_entry.config(state='normal')
        self.id_entry.insert(0, self.hardware_id)
        self.id_entry.config(state='readonly')

        # 複製按鈕
        copy_btn = tk.Button(id_display_frame, text="📋 複製硬體ID",
                           command=self._copy_hardware_id,
                           width=15, height=2, font=("Arial", 11),
                           bg='#4CAF50', fg='white')
        copy_btn.pack(side='left', padx=10)

        # 電腦資訊
        info_frame = tk.LabelFrame(self.window, text="電腦資訊", font=("Arial", 12))
        info_frame.pack(pady=10, padx=40, fill='x')

        computer_info = f"""
💻 電腦名稱：{platform.node()}
🖥️ 作業系統：{platform.system()} {platform.release()}
        """

        tk.Label(info_frame, text=computer_info, font=("Arial", 10),
                justify='left').pack(pady=10, padx=10, anchor='w')

        # 關閉按鈕
        tk.Button(self.window, text="關閉", command=self.window.destroy,
                 width=12, height=2, font=("Arial", 11)).pack(pady=20)

    def _copy_hardware_id(self):
        """複製硬體ID到剪貼簿"""
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(self.hardware_id)
            messagebox.showinfo("✅ 複製成功",
                f"硬體ID已複製到剪貼簿！\n\n📝 硬體ID：{self.hardware_id}\n\n"
                "請將此ID提供給軟體供應商以取得授權碼。")
        except Exception as e:
            messagebox.showerror("❌ 錯誤", f"複製失敗：{str(e)}")

    def run(self):
        """執行工具"""
        self.window.mainloop()

if __name__ == "__main__":
    tool = HardwareIDTool()
    tool.run()