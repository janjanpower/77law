#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
匯入資料對話框 - 🔥 視窗層級修正版
解決檔案選擇對話框被覆蓋的問題
"""
import os
import tkinter as tk
from tkinter import filedialog
from typing import Callable, Optional

from config.settings import AppConfig
from views.base_window import BaseWindow


# 🔥 使用安全導入方式
try:
    from views.dialogs import UnifiedMessageDialog
    DIALOGS_AVAILABLE = True
except ImportError as e:
    print(f"警告：無法導入對話框模組 - {e}")
    import tkinter.messagebox as messagebox
    DIALOGS_AVAILABLE = False

    class UnifiedMessageDialog:
        @staticmethod
        def show_success(parent, message, title="成功"):
            messagebox.showinfo(title, message)

        @staticmethod
        def show_error(parent, message, title="錯誤"):
            messagebox.showerror(title, message)


class ImportDataDialog(BaseWindow):
    """匯入資料對話框 - 🔥 視窗層級修正版"""

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
        self.parent_window = parent  # 🔥 修正：保存父視窗引用

        title = "匯入Excel資料"
        super().__init__(title=title, width=520, height=700, resizable=False, parent=parent)

        # 🔥 修正：正確的視窗層級設定
        self._setup_proper_window_hierarchy(parent)

    def _setup_proper_window_hierarchy(self, parent):
        """🔥 修正版：設定正確的視窗層級關係"""
        if parent and self.window:
            try:
                # 設定父子關係
                self.window.transient(parent)

                # 初始顯示設定
                self.window.lift()
                self.window.focus_force()

                # 🔥 關鍵：不要設定 -topmost，讓系統自然管理層級
                # 只在需要時臨時置頂

                # 延遲確保視窗正確顯示
                self.window.after(100, self._ensure_proper_display)

            except Exception as e:
                print(f"設定視窗層級失敗: {e}")

    def _ensure_proper_display(self):
        """🔥 確保視窗正確顯示但不干擾系統對話框"""
        try:
            if self.window and self.window.winfo_exists():
                # 只提升視窗到前面，不設定永久置頂
                self.window.lift()
                self.window.focus_force()
        except Exception as e:
            print(f"確保顯示失敗: {e}")

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
        """🔥 修正版：選擇Excel檔案並正確處理視窗層級"""
        try:
            # 🔥 關鍵修正：暫時隱藏主對話框，讓檔案選擇對話框正常顯示
            self.window.withdraw()

            file_path = filedialog.askopenfilename(
                title="選擇Excel檔案",
                filetypes=[
                    ("Excel files", "*.xlsx *.xls"),
                    ("All files", "*.*")
                ],
                parent=self.parent_window if self.parent_window else None  # 🔥 修正：安全地使用父視窗
            )

            # 🔥 檔案選擇完成後，重新顯示主對話框
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

            if file_path:
                self.selected_file = file_path

                # 顯示檔案名稱
                filename = os.path.basename(file_path)
                self.file_path_var.set(f"已選擇：{filename}")

                # 自動分析檔案
                self._analyze_file()
            else:
                # 如果沒有選擇檔案，確保對話框仍然可見
                self.window.after(100, lambda: self.window.focus_force())

        except Exception as e:
            # 發生錯誤時確保對話框重新顯示
            self.window.deiconify()
            self.window.lift()
            print(f"選擇檔案時發生錯誤: {e}")
            UnifiedMessageDialog.show_error(self.window, f"選擇檔案時發生錯誤：{str(e)}")

    def _analyze_file(self):
        """分析Excel檔案"""
        if not self.selected_file:
            return

        try:
            from utils.excel import ExcelHandler

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

                    # 啟用匯入按鈕
                    if hasattr(self, 'import_btn'):
                        self.import_btn.config(state='normal')
                else:
                    analysis_text = f"⚠️ 未找到可匯入的工作表\n\n{message}"
                    self.analysis_label.config(text=analysis_text, fg='#FF9800')
            else:
                error_text = f"❌ 分析失敗：{message}"
                self.analysis_label.config(text=error_text, fg='#F44336')

        except Exception as e:
            error_text = f"❌ 分析過程發生錯誤：{str(e)}"
            self.analysis_label.config(text=error_text, fg='#F44336')
            print(f"分析Excel檔案失敗: {e}")

    def _create_import_buttons(self, parent):
        """建立匯入按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(fill='x', pady=(20, 0))

        # 匯入按鈕
        self.import_btn = tk.Button(
            button_frame,
            text='開始匯入',
            command=self._start_import,
            bg='#4CAF50',
            fg='white',
            font=AppConfig.FONTS['button'],
            width=12,
            height=2,
            state='disabled'  # 初始禁用，分析成功後啟用
        )
        self.import_btn.pack(side='left', padx=(0, 10))

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12,
            height=2
        )
        cancel_btn.pack(side='left')

    def _start_import(self):
        """開始匯入資料"""
        if not self.selected_file:
            UnifiedMessageDialog.show_error(self.window, "請先選擇Excel檔案")
            return

        if not self.case_controller:
            UnifiedMessageDialog.show_error(self.window, "案件控制器未初始化")
            return

        try:
            # 顯示匯入中
            self.analysis_label.config(text="🚀 正在匯入資料，請稍候...", fg='#2196F3')
            self.import_btn.config(state='disabled', text='匯入中...')
            self.window.update()

            # 執行匯入
            from utils.excel import ExcelHandler
            success, message, categorized_cases = ExcelHandler.import_cases_by_category(self.selected_file)

            if success:
                # 將案件加入到控制器
                total_imported = 0
                for case_type, cases in categorized_cases.items():
                    for case in cases:
                        try:
                            if self.case_controller.add_case(case):
                                total_imported += 1
                        except Exception as e:
                            print(f"加入案件失敗: {e}")

                if total_imported > 0:
                    success_message = f"✅ 匯入成功！共匯入 {total_imported} 筆"
                    # 先關閉自己
                    parent_for_msg = self.parent_window or self.window
                    try:
                        self.close()
                    except Exception:
                        pass

                    # 再跳成功訊息（放到 event loop 下一輪，確保視窗已經關閉）
                    (parent_for_msg or self.window).after(
                        50, lambda: UnifiedMessageDialog.show_success(parent_for_msg, success_message)
                    )

                    # 若有回調，最後再通知外部
                    try:
                        if callable(getattr(self, 'on_import_complete', None)):
                            self.on_import_complete()
                    except Exception:
                        pass
                    return

                else:
                    UnifiedMessageDialog.show_error(self.window, "沒有成功匯入任何案件")
            else:
                UnifiedMessageDialog.show_error(self.window, f"匯入失敗：{message}")

        except Exception as e:
            error_message = f"匯入過程發生錯誤：{str(e)}"
            UnifiedMessageDialog.show_error(self.window, error_message)
            print(f"匯入資料失敗: {e}")

        finally:
            # 恢復按鈕狀態
            self.import_btn.config(state='normal', text='開始匯入')

    def show(self):
        """🔥 修正版：顯示對話框"""
        if self.window:
            try:
                self.window.deiconify()
                self.window.lift()
                self.window.focus_force()

                # 🔥 設定模態對話框
                if self.parent_window:
                    self.window.grab_set()

                return True
            except Exception as e:
                print(f"顯示對話框失敗: {e}")
                return False
        return False

    def close(self):
        """🔥 修正版：關閉對話框"""
        try:
            # 釋放grab
            if self.window:
                self.window.grab_release()

            # 呼叫父類的關閉方法
            super().close()

        except Exception as e:
            print(f"關閉對話框失敗: {e}")

    def on_window_close(self):
        """視窗關閉事件處理"""
        self.close()

    @staticmethod
    def show_import_dialog(parent, case_controller, on_import_complete: Callable = None):
        """🔥 靜態方法：顯示匯入資料對話框"""
        try:
            dialog = ImportDataDialog(parent, case_controller, on_import_complete)
            dialog.show()

            # 🔥 等待對話框關閉（模態對話框）
            if dialog.window:
                dialog.window.wait_window()

        except Exception as e:
            print(f"顯示匯入對話框失敗: {e}")
            import tkinter.messagebox as messagebox
            messagebox.showerror("錯誤", f"無法開啟匯入對話框：{str(e)}")