# hardware_id_tool_standalone.py
"""
📍 客戶取得硬體ID的工具（獨立執行）
使用專案統一樣式設計
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox


# 添加專案路徑
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

try:
    from utils.hardware_utils import HardwareUtils
    from config.settings import AppConfig
    from views.base_window import BaseWindow
    from views.dialogs import UnifiedMessageDialog
except ImportError:
    # 如果無法導入專案模組，使用獨立實作
    import hashlib
    import platform
    import uuid

    class HardwareUtils:
        @staticmethod
        def get_hardware_id():
            try:
                mac = uuid.getnode()
                computer_name = platform.node()
                unique_string = f"{mac}_{computer_name}"
                return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
            except:
                return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]

        @staticmethod
        def get_system_info():
            return {
                'computer_name': platform.node(),
                'system': platform.system(),
                'release': platform.release(),
                'hardware_id': HardwareUtils.get_hardware_id()
            }

    # 簡化的設定
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


class HardwareIDTool:
    """硬體ID查詢工具（使用專案統一樣式）"""

    def __init__(self):
        self.window = tk.Tk()
        self.drag_data = {"x": 0, "y": 0}
        self.hardware_info = HardwareUtils.get_system_info()

        self._setup_window()
        self._create_ui()

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title("硬體ID查詢工具")
        self.window.geometry("600x500")
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.resizable(False, False)

        # 置中顯示
        self._center_window()

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 300
        y = (self.window.winfo_screenheight() // 2) - 250
        self.window.geometry(f"600x500+{x}+{y}")

    def _create_ui(self):
        """建立使用者介面"""
        # 主容器
        main_frame = tk.Frame(self.window, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True)

        # 自定義標題列
        title_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['title_bg'], height=25)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="硬體ID查詢工具",
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
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)

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

        info_label = tk.Label(
            content_frame,
            text=info_text,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            justify='left'
        )
        info_label.pack(pady=(0, 20))

        # 硬體ID顯示區域
        id_frame = tk.LabelFrame(
            content_frame,
            text="您的硬體ID",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        id_frame.pack(pady=20, fill='x')

        id_display_frame = tk.Frame(id_frame, bg=AppConfig.COLORS['window_bg'])
        id_display_frame.pack(pady=15)

        self.id_entry = tk.Entry(
            id_display_frame,
            width=25,
            font=('Arial', 14, 'bold'),
            justify='center',
            state='readonly',
            bg='#f0f0f0'
        )
        self.id_entry.pack(side='left', padx=5)

        self.id_entry.config(state='normal')
        self.id_entry.insert(0, self.hardware_info['hardware_id'])
        self.id_entry.config(state='readonly')

        # 複製按鈕
        copy_btn = tk.Button(
            id_display_frame,
            text="📋 複製硬體ID",
            command=self._copy_hardware_id,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=15,
            height=2
        )
        copy_btn.pack(side='left', padx=10)

        # 電腦資訊
        info_frame = tk.LabelFrame(
            content_frame,
            text="電腦資訊",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        info_frame.pack(pady=10, fill='x')

        computer_info = f"""
💻 電腦名稱：{self.hardware_info['computer_name']}
🖥️ 作業系統：{self.hardware_info['system']} {self.hardware_info['release']}
        """

        tk.Label(
            info_frame,
            text=computer_info,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            justify='left'
        ).pack(pady=10, padx=10, anchor='w')

        # 關閉按鈕
        tk.Button(
            content_frame,
            text="關閉",
            command=self.window.destroy,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12,
            height=2
        ).pack(pady=20)

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

    def _copy_hardware_id(self):
        """複製硬體ID到剪貼簿"""
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(self.hardware_info['hardware_id'])

            # 使用統一對話框樣式（如果可用）
            try:
                temp_root = tk.Tk()
                temp_root.withdraw()
                UnifiedMessageDialog.show_success(
                    temp_root,
                    f"硬體ID已複製到剪貼簿！\n\n📝 硬體ID：{self.hardware_info['hardware_id']}\n\n"
                    "請將此ID提供給軟體供應商以取得授權碼。"
                )
                temp_root.destroy()
            except:
                # 回退到標準對話框
                messagebox.showinfo(
                    "✅ 複製成功",
                    f"硬體ID已複製到剪貼簿！\n\n📝 硬體ID：{self.hardware_info['hardware_id']}\n\n"
                    "請將此ID提供給軟體供應商以取得授權碼。"
                )
        except Exception as e:
            messagebox.showerror("❌ 錯誤", f"複製失敗：{str(e)}")

    def run(self):
        """執行工具"""
        self.window.mainloop()


if __name__ == "__main__":
    tool = HardwareIDTool()
    tool.run()