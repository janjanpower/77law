import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
from typing import Optional, Callable
from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow
from views.dialogs import UnifiedMessageDialog
class UploadFileDialog(BaseWindow):
    """上傳資料對話框"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 folder_manager=None, on_upload_complete: Optional[Callable] = None):
        """
        初始化上傳資料對話框

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

        title = "上傳資料"
        super().__init__(title=title, width=500, height=500, resizable=False, parent=parent)
        if parent:
            self.window.lift()
            self.window.attributes('-topmost', True)
            self.window.focus_force()
            # 確保視窗完全顯示後再設定事件
            self.window.after(100, self._ensure_topmost)

    def _ensure_topmost(self):
        """🔥 新增：確保視窗保持置頂"""
        try:
            if self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
        except:
            pass
    def _create_layout(self):
        """建立對話框佈局"""
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
            ).pack(expand=True)
            return

        # 主容器
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 第一行：當事人資訊
        client_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        client_frame.pack(fill='x', pady=(0, 15))

        tk.Label(
            client_frame,
            text=f"當事人：{self.case_data.client}",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['button']
        ).pack(anchor='w')

        # 第二行：目標資料夾選擇
        folder_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        folder_frame.pack(fill='x', pady=(0, 15))

        tk.Label(
            folder_frame,
            text="目標資料夾：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(0, 5))

        # 下拉式選單
        self.folder_var = tk.StringVar()
        self.folder_combo = ttk.Combobox(
            folder_frame,
            textvariable=self.folder_var,
            state='readonly',
            width=50,
            font=AppConfig.FONTS['text']
        )
        self.folder_combo.pack(fill='x')

        # 載入可用的子資料夾
        self._load_available_folders()

        # 第三行：檔案選擇
        file_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        file_frame.pack(fill='x', pady=(0, 15))

        tk.Label(
            file_frame,
            text="選擇檔案：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(0, 5))

        # 檔案選擇按鈕
        file_select_frame = tk.Frame(file_frame, bg=AppConfig.COLORS['window_bg'])
        file_select_frame.pack(fill='x')

        select_file_btn = tk.Button(
            file_select_frame,
            text='選擇檔案',
            command=self._select_files,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=12,
            height=1
        )
        select_file_btn.pack(side='left', padx=(0, 10))

        # 清除選擇按鈕
        clear_btn = tk.Button(
            file_select_frame,
            text='清除',
            command=self._clear_files,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['text'],
            width=8,
            height=1
        )
        clear_btn.pack(side='left')

        # 檔案列表顯示
        list_frame = tk.Frame(file_frame, bg=AppConfig.COLORS['window_bg'])
        list_frame.pack(fill='both', expand=True, pady=(10, 0))

        tk.Label(
            list_frame,
            text="已選擇的檔案：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w')

        # 檔案列表框
        self.file_listbox = tk.Listbox(
            list_frame,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text'],
            height=6
        )
        self.file_listbox.pack(fill='both', expand=True, pady=(5, 0))

        # 按鈕區域
        self._create_upload_buttons(main_frame)

    def _load_available_folders(self):
        """載入可用的子資料夾"""
        try:
            if not self.folder_manager:
                self.folder_combo['values'] = ["錯誤：無法取得資料夾管理器"]
                return

            # 取得案件資料夾路徑
            case_folder = self.folder_manager.get_case_folder_path(self.case_data)
            if not case_folder or not os.path.exists(case_folder):
                self.folder_combo['values'] = ["錯誤：找不到案件資料夾"]
                return

            # 掃描所有子資料夾
            subfolders = []
            for item in os.listdir(case_folder):
                item_path = os.path.join(case_folder, item)
                if os.path.isdir(item_path):
                    subfolders.append(item)

                    # 如果是"進度追蹤"資料夾，也掃描其子資料夾
                    if item == "進度追蹤":
                        try:
                            for progress_item in os.listdir(item_path):
                                progress_path = os.path.join(item_path, progress_item)
                                if os.path.isdir(progress_path):
                                    subfolders.append(f"進度追蹤/{progress_item}")
                        except:
                            pass

            if subfolders:
                self.folder_combo['values'] = sorted(subfolders)
                self.folder_combo.current(0)  # 預設選擇第一個
            else:
                self.folder_combo['values'] = ["無可用的子資料夾"]

        except Exception as e:
            print(f"載入資料夾失敗: {e}")
            self.folder_combo['values'] = [f"錯誤：{str(e)}"]

    def _select_files(self):
        """選擇檔案"""
        try:
            file_paths = filedialog.askopenfilenames(
                title="選擇要上傳的檔案",
                filetypes=[
                    ("所有檔案", "*.*"),
                    ("圖片檔案", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff"),
                    ("音訊檔案", "*.mp3 *.wav *.flac *.aac *.ogg"),
                    ("影片檔案", "*.mp4 *.avi *.mkv *.mov *.wmv"),
                    ("文件檔案", "*.pdf *.doc *.docx *.txt *.rtf"),
                    ("Excel檔案", "*.xlsx *.xls"),
                    ("壓縮檔案", "*.zip *.rar *.7z")
                ]
            )

            if file_paths:
                # 將新選擇的檔案加入列表（避免重複）
                for file_path in file_paths:
                    if file_path not in self.selected_files:
                        self.selected_files.append(file_path)

                self._update_file_list()

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"選擇檔案時發生錯誤：{str(e)}")

    def _clear_files(self):
        """清除已選擇的檔案"""
        self.selected_files.clear()
        self._update_file_list()

    def _update_file_list(self):
        """更新檔案列表顯示"""
        self.file_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            filename = os.path.basename(file_path)
            self.file_listbox.insert(tk.END, filename)

    def _create_upload_buttons(self, parent):
        """建立上傳按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=20)

        # 上傳按鈕
        upload_btn = tk.Button(
            button_frame,
            text='確定',
            command=self._start_upload,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        upload_btn.pack(side='left', padx=5,pady=(0,20))

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
        cancel_btn.pack(side='left', padx=5,pady=(0,20))

    def _start_upload(self):
        """開始上傳檔案"""
        try:
            # 驗證選擇
            if not self.selected_files:
                UnifiedMessageDialog.show_success(self.window, "請先選擇要上傳的檔案")
                return

            selected_folder = self.folder_var.get()
            if not selected_folder or selected_folder in ["錯誤：找不到案件資料夾", "無可用的子資料夾"]:
                UnifiedMessageDialog.show_success(self.window, "請選擇目標資料夾")
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
                        elif not response:  # 否（跳過）
                            continue

                    # 複製檔案
                    shutil.copy2(file_path, destination)
                    success_count += 1
                    print(f"檔案上傳成功: {filename} -> {destination}")

                except Exception as file_error:
                    error_files.append(f"{os.path.basename(file_path)}: {str(file_error)}")
                    print(f"檔案上傳失敗: {file_path} - {file_error}")

            # 顯示結果
            result_message = f"上傳完成！\n\n成功上傳 {success_count} 個檔案到：\n{selected_folder}"

            if error_files:
                result_message += f"\n\n失敗的檔案：\n" + "\n".join(error_files[:5])
                if len(error_files) > 5:
                    result_message += f"\n... 以及其他 {len(error_files) - 5} 個檔案"

            if success_count > 0:
                UnifiedMessageDialog.show_success(self.window, result_message)

                # 呼叫完成回調
                if self.on_upload_complete:
                    self.on_upload_complete()

                self.close()
            else:
                UnifiedMessageDialog.show_error(self.window,"沒有檔案成功上傳。\n\n" + result_message)

        except Exception as e:
            print(f"上傳檔案時發生錯誤: {e}")
            UnifiedMessageDialog.show_error(self.window, f"上傳過程發生錯誤：{str(e)}")

    @staticmethod
    def show_upload_dialog(parent, case_data: CaseData, folder_manager, on_upload_complete: Callable = None):
        """顯示上傳檔案對話框"""
        dialog = UploadFileDialog(parent, case_data, folder_manager, on_upload_complete)
        dialog.window.wait_window()