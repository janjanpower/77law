#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional

from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow

# 🔥 使用統一的安全導入方式
try:
    from views.dialogs import UnifiedMessageDialog, UnifiedConfirmDialog
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

    class UnifiedConfirmDialog:
        def __init__(self, parent, title="確認", message="", confirm_text="確定", cancel_text="取消"):
            self.result = messagebox.askyesno(title, message)
            self.window = None  # 為了兼容性

        @staticmethod
        def ask_file_overwrite(parent, filename):
            return messagebox.askyesno(
                "檔案已存在",
                f"檔案「{filename}」已存在於目標資料夾。\n\n是否要覆蓋現有檔案？"
            )


class UploadFileDialog(BaseWindow):
    """統一的檔案上傳對話框"""

    def __init__(self, parent, case_data: CaseData, folder_manager, on_upload_complete: Callable = None):
        """初始化上傳檔案對話框"""
        try:
            # 🔥 關鍵修改：確保傳入正確的案件資料物件
            if not case_data or not hasattr(case_data, 'case_type'):
                raise ValueError("無效的案件資料物件")

            self.case_data = case_data
            self.folder_manager = folder_manager
            self.on_upload_complete = on_upload_complete

            # 🔥 安全的資料夾路徑取得
            self.case_folder_path = self._get_safe_case_folder_path()
            if not self.case_folder_path:
                raise ValueError(f"無法取得案件 {case_data.client} 的資料夾路徑")

        except Exception as e:
            print(f"❌ 初始化上傳對話框失敗: {e}")
            raise

        self.case_data = case_data
        self.folder_manager = folder_manager
        self.on_upload_complete = on_upload_complete
        self.selected_files = []

        # 準備資料夾選項
        self.folder_options = self._get_unified_folder_options()
        self.folder_var = tk.StringVar()

        super().__init__(title="上傳檔案", width=350, height=450, resizable=False, parent=parent)

        # 🔥 統一的視窗置頂處理
        self._setup_window_topmost()

    def _get_safe_case_folder_path(self) -> Optional[str]:
        """安全的取得案件資料夾路徑"""
        try:
            # 🔥 驗證案件資料
            if not self.folder_manager.validate_case_data(self.case_data):
                return None

            # 🔥 取得資料夾路徑
            folder_path = self.folder_manager.get_case_folder_path(self.case_data)

            if folder_path and os.path.exists(folder_path):
                print(f"✅ 成功取得案件資料夾路徑: {folder_path}")
                return folder_path
            else:
                print(f"❌ 案件資料夾不存在: {self.case_data.client}")
                return None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑時發生錯誤: {e}")
            return None


    def _setup_window_topmost(self):
        """🔥 統一的視窗置頂設定"""
        if self.window and hasattr(self.window, 'winfo_exists'):
            try:
                self.window.lift()
                self.window.attributes('-topmost', True)
                self.window.focus_force()
                # 延遲設定以確保視窗完全顯示
                self.window.after(100, self._ensure_topmost_continuous)
            except Exception as e:
                print(f"設定視窗置頂失敗: {e}")

    def _ensure_topmost_continuous(self):
        """🔥 持續確保視窗置頂"""
        try:
            if self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
        except Exception as e:
            print(f"持續置頂失敗: {e}")

    def _get_unified_folder_options(self):
        """🔥 統一的資料夾選項取得方法"""
        try:
            case_folder = self.folder_manager.get_case_folder_path(self.case_data)
            if not case_folder or not os.path.exists(case_folder):
                return ["錯誤：找不到案件資料夾"]

            # 統一掃描所有子資料夾，包括進度追蹤的子目錄
            sub_folders = []
            for item in os.listdir(case_folder):
                item_path = os.path.join(case_folder, item)
                if os.path.isdir(item_path):
                    sub_folders.append(item)

                    # 特別處理進度追蹤資料夾的子目錄
                    if item == "進度追蹤":
                        try:
                            for progress_item in os.listdir(item_path):
                                progress_path = os.path.join(item_path, progress_item)
                                if os.path.isdir(progress_path):
                                    sub_folders.append(f"進度追蹤/{progress_item}")
                        except Exception as e:
                            print(f"掃描進度追蹤子資料夾失敗: {e}")

            return sorted(sub_folders) if sub_folders else ["無可用的子資料夾"]

        except Exception as e:
            print(f"取得資料夾選項失敗: {e}")
            return ["錯誤：無法讀取資料夾"]

    def _create_layout(self):
        """建立上傳對話框佈局"""
        super()._create_layout()
        self._create_upload_content()

    def _create_upload_content(self):
        """建立上傳內容"""
        # 主容器
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 案件資訊顯示
        self._create_case_info_section(main_frame)

        # 目標資料夾選擇
        self._create_folder_selection_section(main_frame)

        # 檔案選擇區域
        self._create_file_selection_section(main_frame)

        # 按鈕區域
        self._create_action_buttons(main_frame)

    def _create_case_info_section(self, parent):
        """建立案件資訊區域"""
        info_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        info_frame.pack(fill='x', pady=(0,10))

        case_display_name = AppConfig.format_case_display_name(self.case_data)
        info_text = f"案件：{case_display_name} ({self.case_data.case_type})"

        tk.Label(
            info_frame,
            text=info_text,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w')

    def _create_folder_selection_section(self, parent):
        """建立資料夾選擇區域"""
        folder_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        folder_frame.pack(fill='x', pady=(10, 10))

        tk.Label(
            folder_frame,
            text="目標資料夾：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(0, 5))

        # 資料夾選擇下拉選單
        self.folder_combo = ttk.Combobox(
            folder_frame,
            textvariable=self.folder_var,
            values=self.folder_options,
            state='readonly',
            width=40,
            font=AppConfig.FONTS['text']
        )
        self.folder_combo.pack(fill='x')

        # 預設選擇第一個可用資料夾
        if self.folder_options and not any(self.folder_options[0].startswith(prefix)
                                         for prefix in ["錯誤", "無"]):
            self.folder_var.set(self.folder_options[0])

    def _create_file_selection_section(self, parent):
        """建立檔案選擇區域"""
        file_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        file_frame.pack(fill='both', expand=True, pady=(0, 10))

        tk.Label(
            file_frame,
            text="選擇檔案：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(0, 5))

        # 檔案列表
        self.file_listbox = tk.Listbox(
            file_frame,
            height=3,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text']
        )
        self.file_listbox.pack(fill='both', expand=True, pady=(0, 10))

        # 檔案操作按鈕
        self._create_file_operation_buttons(file_frame)

    def _create_file_operation_buttons(self, parent):
        """建立檔案操作按鈕"""
        file_btn_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        file_btn_frame.pack(fill='x')

        # 新增檔案按鈕
        add_file_btn = tk.Button(
            file_btn_frame,
            text='選擇檔案',
            command=self._select_files_with_topmost,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        add_file_btn.pack(side='left', padx=(0, 5))

        # 移除檔案按鈕
        remove_file_btn = tk.Button(
            file_btn_frame,
            text='移除檔案',
            command=self._remove_selected_file,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        remove_file_btn.pack(side='left', padx=5)

        # 清空檔案按鈕
        clear_files_btn = tk.Button(
            file_btn_frame,
            text='清空',
            command=self._clear_all_files,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        clear_files_btn.pack(side='left', padx=5)

    def _select_files_with_topmost(self):
        """🔥 修正：選擇檔案時保持視窗可見，只調整置頂狀態"""
        try:
            # 🔥 修正：只暫時取消置頂，不隱藏視窗
            original_topmost = self.window.attributes('-topmost')
            self.window.attributes('-topmost', False)

            # 開啟檔案選擇對話框
            files = filedialog.askopenfilenames(
                title="選擇要上傳的檔案",
                parent=self.window,
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

            # 🔥 修正：檔案選擇完成後立即恢復置頂
            self._restore_topmost_immediately()

            # 處理選中的檔案
            if files:
                for file_path in files:
                    if file_path not in self.selected_files:
                        self.selected_files.append(file_path)

                self._update_file_list_display()

        except Exception as e:
            print(f"選擇檔案時發生錯誤: {e}")
            # 確保即使發生錯誤也恢復置頂
            self._restore_topmost_immediately()
            UnifiedMessageDialog.show_error(self.window, f"選擇檔案時發生錯誤：{str(e)}")

    def _remove_selected_file(self):
        """移除選中的檔案"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            self.file_listbox.delete(index)
            del self.selected_files[index]

    def _clear_all_files(self):
        """清空所有已選擇的檔案"""
        self.selected_files.clear()
        self._update_file_list_display()

    def _update_file_list_display(self):
        """更新檔案列表顯示"""
        self.file_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            filename = os.path.basename(file_path)
            self.file_listbox.insert(tk.END, filename)

    def _create_action_buttons(self, parent):
        """建立操作按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=20)

        # 上傳按鈕
        upload_btn = tk.Button(
            button_frame,
            text='開始上傳',
            command=self._start_upload_with_topmost,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
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

    def _start_upload_with_topmost(self):
        """🔥 開始上傳檔案並確保提醒視窗置頂"""
        try:
            # 驗證選擇
            if not self.selected_files:
                self._show_topmost_message("error", "請先選擇要上傳的檔案")
                return

            selected_folder = self.folder_var.get()
            if not selected_folder or selected_folder in ["錯誤：找不到案件資料夾", "無可用的子資料夾"]:
                self._show_topmost_message("error", "請選擇目標資料夾")
                return

            # 建立目標路徑
            case_folder = self.folder_manager.get_case_folder_path(self.case_data)
            target_path = os.path.join(case_folder, selected_folder)

            if not os.path.exists(target_path):
                self._show_topmost_message("error", f"目標資料夾不存在：{target_path}")
                return

            # 執行檔案上傳流程
            self._execute_file_upload(target_path, selected_folder)

        except Exception as e:
            print(f"上傳檔案時發生錯誤: {e}")
            self._show_topmost_message("error", f"上傳過程發生錯誤：{str(e)}")

    def _execute_file_upload(self, target_path, selected_folder):
        """執行檔案上傳邏輯"""
        success_count = 0
        error_files = []

        for file_path in self.selected_files:
            try:
                filename = os.path.basename(file_path)
                destination = os.path.join(target_path, filename)

                # 🔥 檢查檔案是否已存在，使用置頂確認對話框
                if os.path.exists(destination):
                    if not self._ask_file_overwrite_with_topmost(filename):
                        continue  # 跳過此檔案

                # 複製檔案
                shutil.copy2(file_path, destination)
                success_count += 1
                print(f"檔案上傳成功: {filename} -> {destination}")

            except Exception as file_error:
                error_files.append(f"{os.path.basename(file_path)}: {str(file_error)}")
                print(f"檔案上傳失敗: {file_path} - {file_error}")

        # 顯示上傳結果
        self._show_upload_result(success_count, error_files, selected_folder)

    def _ask_file_overwrite_with_topmost(self, filename):
        """🔥 修正：檔案覆蓋確認對話框 - 保持上傳視窗可見"""
        try:
            if DIALOGS_AVAILABLE:
                # 🔥 修正：不隱藏上傳視窗，只暫時取消置頂
                original_topmost = self.window.attributes('-topmost')
                self.window.attributes('-topmost', False)

                try:
                    message = f"檔案「{filename}」已存在於目標資料夾。\n\n是否要覆蓋現有檔案？"
                    overwrite_dialog = UnifiedConfirmDialog(
                        self.window,  # 🔥 修正：直接使用當前視窗作為父級
                        title="檔案已存在",
                        message=message,
                        confirm_text="覆蓋",
                        cancel_text="跳過"
                    )

                    # 等待對話框結果
                    overwrite_dialog.window.wait_window()
                    result = overwrite_dialog.result if overwrite_dialog.result is not None else False

                    # 🔥 修正：立即恢復置頂狀態
                    self.window.attributes('-topmost', True)
                    self.window.lift()

                    return result

                except Exception as dialog_error:
                    print(f"顯示覆蓋確認對話框失敗: {dialog_error}")
                    # 恢復置頂狀態
                    self.window.attributes('-topmost', True)
                    return False
            else:
                return UnifiedConfirmDialog.ask_file_overwrite(self.window, filename)

        except Exception as e:
            print(f"顯示檔案覆蓋確認對話框失敗: {e}")
            return False

    def _show_upload_result(self, success_count, error_files, selected_folder):
        """🔥 修正：顯示上傳結果並詢問是否刪除原始檔案"""
        result_message = f"上傳完成！\n\n成功上傳 {success_count} 個檔案到：\n{selected_folder}"

        if error_files:
            result_message += f"\n\n失敗的檔案：\n" + "\n".join(error_files[:5])
            if len(error_files) > 5:
                result_message += f"\n... 以及其他 {len(error_files) - 5} 個檔案"

        if success_count > 0:
            # 先顯示上傳成功訊息
            self._show_topmost_message("success", result_message)

            # 🔥 新增：詢問是否刪除原始檔案
            self._ask_delete_original_files(success_count)

            # 呼叫完成回調
            if self.on_upload_complete:
                self.on_upload_complete()

            # 關閉對話框
            self.close()
        else:
            self._show_topmost_message("error", "沒有檔案成功上傳。\n\n" + result_message)

    def _ask_delete_original_files(self, success_count):
        """🔥 新增：詢問是否刪除原始檔案"""
        try:
            # 暫時取消主視窗置頂
            self.window.attributes('-topmost', False)

            # 建立詢問訊息
            if success_count == 1:
                message = "檔案已成功上傳！\n\n是否要刪除原始檔案？"
            else:
                message = f"已成功上傳 {success_count} 個檔案！\n\n是否要刪除這些原始檔案？"

            # 顯示確認對話框
            delete_dialog = UnifiedConfirmDialog(
                self.window,
                title="刪除原始檔案",
                message=message,
                confirm_text="刪除",
                cancel_text="保留"
            )

            # 等待用戶選擇
            delete_dialog.window.wait_window()

            if delete_dialog.result:
                # 用戶選擇刪除，執行刪除操作
                self._delete_original_files()
            else:
                # 用戶選擇保留，不做任何操作
                print("用戶選擇保留原始檔案")

            # 恢復主視窗置頂
            if self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)

        except Exception as e:
            print(f"詢問刪除原始檔案時發生錯誤: {e}")
            # 恢復主視窗置頂
            if self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)

    def _delete_original_files(self):
        """🔥 新增：刪除原始檔案"""
        deleted_count = 0
        failed_files = []

        try:
            for file_path in self.selected_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"已刪除原始檔案: {file_path}")
                    else:
                        print(f"原始檔案不存在: {file_path}")

                except Exception as file_error:
                    failed_files.append(os.path.basename(file_path))
                    print(f"刪除原始檔案失敗: {file_path} - {file_error}")

            # 顯示刪除結果
            self._show_delete_result(deleted_count, failed_files)

        except Exception as e:
            print(f"刪除原始檔案過程發生錯誤: {e}")
            self._show_topmost_message("error", f"刪除原始檔案時發生錯誤：{str(e)}")

    def _show_delete_result(self, deleted_count, failed_files):
        """🔥 新增：顯示刪除結果"""
        if deleted_count > 0 and not failed_files:
            # 全部成功刪除
            if deleted_count == 1:
                message = "原始檔案已成功刪除！"
            else:
                message = f"已成功刪除 {deleted_count} 個原始檔案！"

            self._show_topmost_message("success", message)

        elif deleted_count > 0 and failed_files:
            # 部分成功
            message = f"已成功刪除 {deleted_count} 個原始檔案。\n\n"
            message += f"刪除失敗的檔案：\n" + "\n".join(failed_files[:5])
            if len(failed_files) > 5:
                message += f"\n... 以及其他 {len(failed_files) - 5} 個檔案"

            self._show_topmost_message("warning", message)

        elif not deleted_count and failed_files:
            # 全部失敗
            message = "無法刪除任何原始檔案。\n\n"
            message += f"失敗的檔案：\n" + "\n".join(failed_files[:5])
            if len(failed_files) > 5:
                message += f"\n... 以及其他 {len(failed_files) - 5} 個檔案"

            self._show_topmost_message("error", message)

        else:
            return UnifiedConfirmDialog.ask_file_overwrite(self.window, filename)




    def _restore_topmost_immediately(self):
        """🔥 新增：立即恢復置頂狀態"""
        try:
            if self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
        except Exception as e:
            print(f"恢復視窗置頂失敗: {e}")

    def _show_topmost_message(self, message_type, message):
        """🔥 修正：顯示置頂訊息對話框 - 支援警告類型"""
        try:
            # 暫時取消主視窗置頂
            self.window.attributes('-topmost', False)

            # 顯示訊息對話框
            if message_type == "success":
                dialog = UnifiedMessageDialog(self.window, "成功", message, "success")
            elif message_type == "error":
                dialog = UnifiedMessageDialog(self.window, "錯誤", message, "error")
            elif message_type == "warning":
                dialog = UnifiedMessageDialog(self.window, "警告", message, "warning")
            else:
                dialog = UnifiedMessageDialog(self.window, "訊息", message, "info")

            # 確保對話框置頂並置中
            if hasattr(dialog, 'window') and dialog.window:
                # 設定置頂
                dialog.window.attributes('-topmost', True)

                # 強制置中顯示
                dialog.window.update_idletasks()

                # 取得螢幕尺寸
                screen_width = dialog.window.winfo_screenwidth()
                screen_height = dialog.window.winfo_screenheight()

                # 取得對話框尺寸
                dialog_width = dialog.window.winfo_reqwidth()
                dialog_height = dialog.window.winfo_reqheight()

                # 計算置中位置
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2

                # 設定視窗位置（置中）
                dialog.window.geometry(f"+{x}+{y}")

                # 等待對話框關閉
                dialog.window.wait_window()

            # 🔥 修正：立即恢復主視窗置頂
            if self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()

        except Exception as e:
            print(f"顯示置頂訊息對話框失敗: {e}")
            # 備用方案
            try:
                if message_type == "success":
                    UnifiedMessageDialog.show_success(self.window, message)
                elif message_type == "warning":
                    UnifiedMessageDialog.show_warning(self.window, message)
                else:
                    UnifiedMessageDialog.show_error(self.window, message)
            except:
                print(f"備用訊息顯示也失敗: {message}")

    @staticmethod
    def show_upload_dialog(parent, case_data: CaseData, folder_manager, on_upload_complete: Callable = None):
        """顯示上傳檔案對話框"""
        dialog = UploadFileDialog(parent, case_data, folder_manager, on_upload_complete)
        dialog.window.wait_window()