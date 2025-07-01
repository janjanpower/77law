# views/upload_file_dialog.py
"""
更新的上傳檔案對話框 - 統一使用增強版BaseWindow
移除重複的置頂處理代碼
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
from typing import Optional, Callable
from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import EnhancedBaseWindow
from views.dialogs import UnifiedMessageDialog

class UploadFileDialog(EnhancedBaseWindow):
    """上傳檔案對話框 - 使用增強版BaseWindow"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 folder_manager=None, on_upload_complete: Optional[Callable] = None):
        """
        初始化上傳檔案對話框

        Args:
            parent: 父視窗
            case_data: 選中的案件資料
            folder_manager: 資料夾管理器
            on_upload_complete: 上傳完成回調函數
        """
        self.case_data = case_data
        self.folder_manager = folder_manager
        self.on_upload_complete = on_upload_complete
        self.selected_files = []
        self.target_folder = None

        # 🔥 簡化：使用增強版BaseWindow，自動處理置頂
        super().__init__(
            title="上傳檔案",
            width=500,
            height=500,
            resizable=False,
            parent=parent,
            auto_topmost=True  # 自動維持置頂
        )

    def _create_layout(self):
        """覆寫：建立對話框佈局"""
        super()._create_layout()
        self._create_upload_content()

    def _create_upload_content(self):
        """建立上傳對話框內容"""
        if not self.case_data:
            tk.Label(
                self.content_frame,
                text="錯誤：未選擇案件",
                bg=AppConfig.COLORS['window_bg'],
                fg='red',
                font=AppConfig.FONTS['text']
            ).pack(pady=20)
            return

        # 案件資訊
        info_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        info_frame.pack(fill='x', pady=(0, 20))

        case_display_name = AppConfig.format_case_display_name(self.case_data)
        tk.Label(
            info_frame,
            text=f"案件：{case_display_name}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        ).pack(anchor='w')

        # 目標資料夾選擇
        folder_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        folder_frame.pack(fill='x', pady=(0, 15))

        tk.Label(
            folder_frame,
            text="選擇目標資料夾：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(0, 5))

        # 取得可用的子資料夾
        available_folders = self._get_available_folders()

        self.folder_var = tk.StringVar()
        if available_folders:
            self.folder_var.set(available_folders[0])

        folder_combo = ttk.Combobox(
            folder_frame,
            textvariable=self.folder_var,
            values=available_folders,
            state='readonly',
            width=40,
            font=AppConfig.FONTS['text']
        )
        folder_combo.pack(fill='x', pady=(0, 10))

        # 檔案選擇
        file_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        file_frame.pack(fill='both', expand=True, pady=(0, 15))

        tk.Label(
            file_frame,
            text="選擇要上傳的檔案：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(0, 5))

        # 檔案列表框架
        list_frame = tk.Frame(file_frame, bg=AppConfig.COLORS['window_bg'])
        list_frame.pack(fill='both', expand=True)

        # 檔案列表
        self.file_listbox = tk.Listbox(
            list_frame,
            font=AppConfig.FONTS['text'],
            selectmode='extended'
        )
        self.file_listbox.pack(side='left', fill='both', expand=True)

        # 滾動條
        scrollbar = tk.Scrollbar(list_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y')
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)

        # 檔案操作按鈕
        file_btn_frame = tk.Frame(file_frame, bg=AppConfig.COLORS['window_bg'])
        file_btn_frame.pack(fill='x', pady=(10, 0))

        add_files_btn = tk.Button(
            file_btn_frame,
            text='選擇檔案',
            command=self._add_files,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12,
            height=1
        )
        add_files_btn.pack(side='left', padx=(0, 10))

        remove_files_btn = tk.Button(
            file_btn_frame,
            text='移除選中',
            command=self._remove_selected_files,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12,
            height=1
        )
        remove_files_btn.pack(side='left')

        # 按鈕區域
        button_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=(20, 0))

        # 上傳按鈕
        upload_btn = tk.Button(
            button_frame,
            text='開始上傳',
            command=self._start_upload,
            bg='#4CAF50',
            fg='white',
            font=AppConfig.FONTS['button'],
            width=12,
            height=1
        )
        upload_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        cancel_btn.pack(side='left', padx=5)

    def _get_available_folders(self):
        """取得可用的資料夾列表"""
        if not self.folder_manager or not self.case_data:
            return ["錯誤：找不到案件資料夾"]

        case_folder = self.folder_manager.get_case_folder_path(self.case_data)
        if not case_folder or not os.path.exists(case_folder):
            return ["錯誤：找不到案件資料夾"]

        try:
            available_folders = []
            for item in os.listdir(case_folder):
                item_path = os.path.join(case_folder, item)
                if os.path.isdir(item_path):
                    available_folders.append(item)

            if available_folders:
                return sorted(available_folders)
            else:
                return ["無可用的子資料夾"]

        except Exception as e:
            print(f"取得資料夾列表失敗: {e}")
            return ["錯誤：讀取資料夾失敗"]

    def _add_files(self):
        """選擇並新增檔案"""
        file_paths = filedialog.askopenfilenames(
            title="選擇要上傳的檔案",
            parent=self.window
        )

        for file_path in file_paths:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                filename = os.path.basename(file_path)
                self.file_listbox.insert(tk.END, filename)

        # 🔥 使用統一的置頂確保
        self.ensure_topmost()

    def _remove_selected_files(self):
        """移除選中的檔案"""
        selected_indices = self.file_listbox.curselection()

        # 從後往前刪除，避免索引錯亂
        for index in reversed(selected_indices):
            self.file_listbox.delete(index)
            if index < len(self.selected_files):
                del self.selected_files[index]

    def _start_upload(self):
        """開始上傳檔案"""
        try:
            # 驗證選擇
            if not self.selected_files:
                UnifiedMessageDialog.show_error(self.window, "請先選擇要上傳的檔案")
                return

            selected_folder = self.folder_var.get()
            if not selected_folder or selected_folder in ["錯誤：找不到案件資料夾", "無可用的子資料夾"]:
                UnifiedMessageDialog.show_error(self.window, "請選擇目標資料夾")
                return

            # 建立目標路徑
            case_folder = self.folder_manager.get_case_folder_path(self.case_data)
            target_path = os.path.join(case_folder, selected_folder)

            if not os.path.exists(target_path):
                UnifiedMessageDialog.show_error(self.window, f"目標資料夾不存在：{target_path}")
                return

            # 開始複製檔案
            success_count = 0
            error_files = []

            for file_path in self.selected_files:
                try:
                    filename = os.path.basename(file_path)
                    destination = os.path.join(target_path, filename)

                    # 檢查是否已存在同名檔案
                    if os.path.exists(destination):
                        response = messagebox.askyesnocancel(
                            "檔案已存在",
                            f"檔案 '{filename}' 已存在於目標資料夾。\n\n是否要覆蓋？\n\n（是=覆蓋，否=跳過，取消=停止上傳）"
                        )

                        if response is None:  # 取消
                            break
                        elif not response:  # 否，跳過
                            continue

                    # 複製檔案
                    shutil.copy2(file_path, destination)
                    success_count += 1

                except Exception as e:
                    error_files.append(f"{filename}: {str(e)}")

            # 顯示結果
            if success_count > 0:
                success_msg = f"成功上傳 {success_count} 個檔案到 '{selected_folder}' 資料夾"
                if error_files:
                    error_msg = "\n\n上傳失敗的檔案：\n" + "\n".join(error_files)
                    UnifiedMessageDialog.show_warning(self.window, success_msg + error_msg)
                else:
                    UnifiedMessageDialog.show_success(self.window, success_msg)

                # 呼叫完成回調
                if self.on_upload_complete:
                    self.on_upload_complete()

                self.close()
            else:
                if error_files:
                    UnifiedMessageDialog.show_error(self.window, "所有檔案上傳失敗：\n" + "\n".join(error_files))
                else:
                    UnifiedMessageDialog.show_warning(self.window, "沒有檔案被上傳")

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"上傳過程發生錯誤：{str(e)}")