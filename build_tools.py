"""
用於建立各種工具的打包腳本
"""

import os
import subprocess
import sys

def build_hardware_tool():
    """打包硬體ID查詢工具"""
    script_content = '''
import tkinter as tk
from tkinter import messagebox
import uuid
import platform
import hashlib

class HardwareIDTool:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("硬體ID查詢工具")
        self.window.geometry("600x400")
        self.window.resizable(False, False)

        x = (self.window.winfo_screenwidth() // 2) - 300
        y = (self.window.winfo_screenheight() // 2) - 200
        self.window.geometry(f"600x400+{x}+{y}")

        self.hardware_id = self._get_hardware_id()
        self._create_ui()

    def _get_hardware_id(self):
        try:
            mac = uuid.getnode()
            computer_name = platform.node()
            unique_string = f"{mac}_{computer_name}"
            return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        except:
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]

    def _create_ui(self):
        title_label = tk.Label(self.window, text="硬體ID查詢工具",
                              font=("Arial", 18, "bold"))
        title_label.pack(pady=20)

        info_text = """此工具用於取得您電腦的唯一硬體識別碼。

請按照以下步驟操作：
1. 點擊「複製硬體ID」按鈕
2. 將硬體ID提供給軟體供應商
3. 供應商會根據此ID為您生成專屬的授權碼
4. 在軟體中輸入授權碼即可開始使用

注意：硬體ID與您的電腦硬體特徵綁定，
請確保在需要授權的電腦上執行此工具。"""

        info_label = tk.Label(self.window, text=info_text,
                             font=("Arial", 11), justify='left')
        info_label.pack(pady=20, padx=20)

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

        copy_btn = tk.Button(id_display_frame, text="複製硬體ID",
                           command=self._copy_hardware_id,
                           width=12, height=1, font=("Arial", 11))
        copy_btn.pack(side='left', padx=10)

        info_frame = tk.LabelFrame(self.window, text="電腦資訊", font=("Arial", 12))
        info_frame.pack(pady=10, padx=40, fill='x')

        computer_info = f"""電腦名稱：{platform.node()}
作業系統：{platform.system()} {platform.release()}
處理器：{platform.processor() or "未知"}"""

        tk.Label(info_frame, text=computer_info, font=("Arial", 10),
                justify='left').pack(pady=10, padx=10, anchor='w')

        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)

        tk.Button(button_frame, text="關閉", command=self.window.destroy,
                 width=12, height=2, font=("Arial", 11)).pack()

    def _copy_hardware_id(self):
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(self.hardware_id)
            messagebox.showinfo("成功",
                f"硬體ID已複製到剪貼簿！\\n\\n硬體ID：{self.hardware_id}\\n\\n"
                "請將此ID提供給軟體供應商以取得授權碼。")
        except Exception as e:
            messagebox.showerror("錯誤", f"複製失敗：{str(e)}")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    tool = HardwareIDTool()
    tool.run()
'''

    # 寫入獨立的硬體ID工具檔案
    with open('hardware_id_tool_standalone.py', 'w', encoding='utf-8') as f:
        f.write(script_content)

    print("已建立獨立的硬體ID查詢工具：hardware_id_tool_standalone.py")
    print("您可以將此檔案發送給客戶使用")

def create_installation_guide():
    """建立安裝說明文件"""
    guide_content = """
# 案件管理系統 - 授權使用說明

## 客戶端使用流程

### 步驟一：取得硬體ID
1. 執行「硬體ID查詢工具.exe」
2. 點擊「複製硬體ID」按鈕
3. 將硬體ID記錄下來或直接從剪貼簿貼出

### 步驟二：申請授權碼
1. 聯繫軟體供應商
2. 提供您的硬體ID
3. 告知需要的授權期限
4. 等待供應商提供授權碼

### 步驟三：激活軟體
1. 執行「案件管理系統.exe」
2. 系統會提示輸入授權碼
3. 輸入供應商提供的授權碼
4. 點擊「驗證授權」
5. 驗證成功後即可正常使用

## 注意事項

1. **硬體綁定**：授權碼與您的電腦硬體綁定，無法在其他電腦使用
2. **時間限制**：授權碼有使用期限，到期後需重新申請
3. **網路需求**：軟體激活時不需要網路連線
4. **備份建議**：請妥善保管您的授權碼，以備重新安裝時使用

## 常見問題

**Q：授權碼輸入後顯示「與此電腦不匹配」？**
A：請確認您是在申請授權時的同一台電腦上使用，如果更換了硬體，需要重新申請授權碼。

**Q：授權快到期了怎麼辦？**
A：系統會在到期前30天開始提醒，請提前聯繫供應商續期。

**Q：可以在多台電腦上使用同一個授權碼嗎？**
A：不可以，每個授權碼只能在特定的一台電腦上使用。

**Q：軟體重新安裝後還能使用原授權碼嗎？**
A：可以，只要是在同一台電腦上重新安裝，原授權碼仍然有效。

## 聯繫方式

如有任何問題，請聯繫：
- 供應商：[您的聯繫方式]
- 郵件：[您的郵件地址]
- 電話：[您的電話號碼]
"""

    with open('授權使用說明.md', 'w', encoding='utf-8') as f:
        f.write(guide_content)

    print("已建立授權使用說明文件：授權使用說明.md")

if __name__ == "__main__":
    print("正在建立授權工具包...")
    build_hardware_tool()
    create_installation_guide()
    print("授權工具包建立完成！")

