import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional, Callable
from config.settings import AppConfig
from views.base_window import BaseWindow
from views.dialogs import UnifiedMessageDialog

class ImportDataDialog(BaseWindow):
    """匯入資料對話框"""

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

        title = "匯入Excel資料"
        super().__init__(title=title, width=520, height=420, resizable=False, parent=parent)
        if parent:
            self.window.lift()
            self.window.attributes('-topmost', True)
            self.window.after(100, lambda: self.window.attributes('-topmost', False))

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._create_import_content()

    def _create_import_content(self):
        """建立匯入對話框內容"""
        # 主容器
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 說明文字
        info_text = """📋 Excel自動匯入功能說明：

🔍 自動識別功能：
   • 系統會自動分析Excel檔案中的所有工作表
   • 系統會顯示詳細的匯入結果報告
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
        ).pack(anchor='w', pady=(0, 5))

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
            anchor='w',
            wraplength=350,
            height=2
        )
        self.file_path_label.pack(side='left', fill='x', expand=True, padx=(0, 10))

        select_btn = tk.Button(
            file_select_frame,
            text='瀏覽檔案',
            command=self._select_file,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=2
        )
        select_btn.pack(side='right')

        # 分析結果顯示區域
        self.analysis_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        self.analysis_frame.pack(fill='x', pady=(10, 0))

        self.analysis_label = tk.Label(
            self.analysis_frame,
            text="",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['text'],
            justify='left',
            wraplength=470
        )
        self.analysis_label.pack(anchor='w')

        # 按鈕區域
        self._create_import_buttons(main_frame)

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

            # 自動分析檔案
            self._analyze_file()

    def _analyze_file(self):
        """分析Excel檔案"""
        if not self.selected_file:
            return

        try:
            from utils.excel_handler import ExcelHandler

            # 顯示分析中...
            self.analysis_label.config(text="🔍 正在分析Excel檔案...", fg='#FF9800')
            self.window.update()

            # 執行分析
            success, message, categorized_sheets = ExcelHandler.analyze_excel_sheets(self.selected_file)

            if success:
                # 統計結果
                civil_count = len(categorized_sheets.get('民事', []))
                criminal_count = len(categorized_sheets.get('刑事', []))
                unknown_count = len(categorized_sheets.get('unknown', []))

                if civil_count > 0 or criminal_count > 0:
                    analysis_text = f"✅ 檔案分析完成！\n\n{message}"
                    self.analysis_label.config(text=analysis_text, fg='#4CAF50')
                else:
                    analysis_text = f"⚠️ 分析完成，但未找到民事或刑事工作表\n\n{message}"
                    self.analysis_label.config(text=analysis_text, fg='#FF9800')
            else:
                self.analysis_label.config(text=f"❌ 分析失敗：{message}", fg='#F44336')

        except Exception as e:
            self.analysis_label.config(text=f"❌ 分析過程發生錯誤：{str(e)}", fg='#F44336')

    def _create_import_buttons(self, parent):
        """建立匯入按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=20)

        # 匯入按鈕
        self.import_btn = tk.Button(
            button_frame,
            text='開始匯入',
            command=self._start_import,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1,
            state='disabled'  # 初始狀態為禁用
        )
        self.import_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        cancel_btn.pack(side='left', padx=5)

    def _start_import(self):
        """開始匯入資料"""
        if not self.selected_file:
            UnifiedMessageDialog.show_error(self.window, "請先選擇Excel檔案")
            return

        if not self.case_controller:
            UnifiedMessageDialog.show_error(self.window, "案件控制器未初始化")
            return

        try:
            # 執行自動匯入
            success, message = self.case_controller.import_cases_from_excel_auto(self.selected_file)

            if success:
                UnifiedMessageDialog.show_success(self.window, message)

                # 呼叫完成回調
                if self.on_import_complete:
                    self.on_import_complete()

                self.close()
            else:
                UnifiedMessageDialog.show_error(self.window, message)

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