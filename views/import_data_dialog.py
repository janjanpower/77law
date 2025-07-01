# views/import_data_dialog.py
"""
更新的匯入資料對話框 - 統一使用增強版BaseWindow
移除重複的置頂處理代碼
"""

import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional, Callable
from config.settings import AppConfig
from views.base_window import EnhancedBaseWindow
from views.dialogs import UnifiedMessageDialog

class ImportDataDialog(EnhancedBaseWindow):
    """匯入資料對話框 - 使用增強版BaseWindow"""

    def __init__(self, parent=None, case_controller=None, on_import_complete: Optional[Callable] = None):
        """
        初始化匯入資料對話框

        Args:
            parent: 父視窗
            case_controller: 案件控制器
            on_import_complete: 匯入完成回調函數
        """
        self.case_controller = case_controller
        self.on_import_complete = on_import_complete
        self.selected_file = None

        # 🔥 簡化：使用增強版BaseWindow，自動處理置頂
        super().__init__(
            title="匯入Excel資料",
            width=520,
            height=480,
            resizable=False,
            parent=parent,
            auto_topmost=True  # 自動維持置頂
        )

    def _create_layout(self):
        """覆寫：建立對話框佈局"""
        super()._create_layout()
        self._create_import_content()

    def _create_import_content(self):
        """建立匯入對話框內容"""
        # 主容器
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 說明文字
        info_text = """Excel匯入功能說明：

   • 請確認EXCEL中的含有「民事」或是「刑事」的分頁
   • 系統會截取相關必要資料自動新增案件
"""

        info_label = tk.Label(
            main_frame,
            text=info_text,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            justify='left',
            wraplength=470
        )
        info_label.pack(pady=(0, 20))

        # 檔案選擇
        file_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        file_frame.pack(fill='x', pady=(0, 15))

        tk.Label(
            file_frame,
            text="選擇Excel檔案：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        ).pack(anchor='w', pady=(0, 15))

        file_select_frame = tk.Frame(file_frame, bg=AppConfig.COLORS['window_bg'])
        file_select_frame.pack(fill='x')

        self.file_path_var = tk.StringVar(value="請選擇Excel檔案...")
        self.file_path_label = tk.Label(
            file_select_frame,
            textvariable=self.file_path_var,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text'],
            relief='sunken',
            borderwidth=1,
            anchor='w'
        )
        self.file_path_label.pack(side='left', fill='x', expand=True, padx=(0, 10))

        select_btn = tk.Button(
            file_select_frame,
            text='瀏覽',
            command=self._select_file,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        select_btn.pack(side='right')

        # 按鈕區域
        button_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=30)

        # 匯入按鈕
        import_btn = tk.Button(
            button_frame,
            text='開始匯入',
            command=self._start_import,
            bg='#4CAF50',
            fg='white',
            font=AppConfig.FONTS['button'],
            width=12,
            height=2
        )
        import_btn.pack(side='left', padx=10)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=2
        )
        cancel_btn.pack(side='left', padx=10)

    def _select_file(self):
        """選擇Excel檔案"""
        file_types = [
            ('Excel files', '*.xlsx *.xls'),
            ('All files', '*.*')
        ]

        file_path = filedialog.askopenfilename(
            title="選擇Excel檔案",
            filetypes=file_types,
            parent=self.window
        )

        if file_path:
            self.selected_file = file_path
            self.file_path_var.set(f"已選擇：{file_path}")
            # 🔥 使用統一的置頂確保
            self.ensure_topmost()

    def _start_import(self):
        """開始匯入"""
        if not self.selected_file:
            UnifiedMessageDialog.show_error(self.window, "請先選擇Excel檔案")
            return

        if not self.case_controller:
            UnifiedMessageDialog.show_error(self.window, "系統錯誤：案件控制器未初始化")
            return

        try:
            success = self.case_controller.import_from_excel(self.selected_file)
            if success:
                UnifiedMessageDialog.show_success(self.window, "Excel資料匯入成功！")
                if self.on_import_complete:
                    self.on_import_complete()
                self.close()
            else:
                UnifiedMessageDialog.show_error(self.window, "匯入失敗，請檢查Excel檔案格式")
        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"匯入過程發生錯誤：{str(e)}")

    def _select_file(self):
        """選擇Excel檔案並自動分析"""
        file_path = filedialog.askopenfilename(
            title="選擇Excel檔案",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self.selected_file = file_path

            # 顯示檔案名稱
            import os
            filename = os.path.basename(file_path)
            self.file_path_var.set(f"已選擇：{filename}")

            # 自動分析檔案並啟用匯入按鈕
            self._analyze_file()
            self.import_btn.config(state='normal')

    @staticmethod
    def show_import_dialog(parent, case_controller, on_import_complete: Callable = None):
        """顯示匯入資料對話框"""
        dialog = ImportDataDialog(parent, case_controller, on_import_complete)
        dialog.window.wait_window()