#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
views/upload_file_dialog.py
雲端檔案上傳對話框（最小變更版）
- 將原本本機 shutil.copy2() 流程，改為呼叫後端 API 上傳到雲端
- 端點：POST /api/files/upload  (multipart/form-data)
- 自動夾帶 JWT：優先取 start_local.current_user_data['token']；其次取環境變數 API_BEARER_TOKEN
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional, Dict, Any, List

import requests  # ✅ 新增：雲端上傳使用

from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow

# 🔥 使用統一的安全導入方式（對話框）
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

        @staticmethod
        def show_warning(parent, message, title="警告"):
            messagebox.showwarning(title, message)

    class UnifiedConfirmDialog:
        def __init__(self, parent, title="確認", message="", confirm_text="確定", cancel_text="取消"):
            # 簡化版：Yes/No 對話框
            self.result = messagebox.askyesno(title, message)
            self.window = None  # 兼容等待關閉

        @staticmethod
        def ask_file_overwrite(parent, filename):
            # 兼容用，不再使用於雲端上傳
            return messagebox.askyesno(
                "檔案已存在",
                f"檔案「{filename}」已存在於目標資料夾。\n\n是否要覆蓋現有檔案？"
            )


# === 雲端上傳 API 設定 ===
API_BASE_URL = os.getenv("API_BASE_URL", "https://law-controller-4a92b3cfcb5d.herokuapp.com")
UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/files/upload"   # 後端檔案上傳端點

def _get_bearer_token_from_runtime() -> str:
    """
    依序嘗試取得 JWT：
    1) start_local.current_user_data['token']
    2) 環境變數 API_BEARER_TOKEN
    取不到就回空字串（不帶 Authorization）
    """
    # 1) 嘗試從登入流程的 global 取
    try:
        from start_local import current_user_data
        if isinstance(current_user_data, dict):
            tok = (current_user_data.get("token") or "").strip()
            if tok:
                return tok
    except Exception:
        pass

    # 2) 環境變數
    tok = (os.getenv("API_BEARER_TOKEN") or "").strip()
    return tok


class UploadFileDialog(BaseWindow):
    """統一的檔案上傳對話框（雲端版）"""

    def __init__(self, parent, case_data: CaseData, folder_manager, on_upload_complete: Callable = None):
        """
        初始化上傳檔案對話框

        Args:
            parent: 父視窗
            case_data: 選中的案件資料
            folder_manager: 資料夾管理器（僅用於顯示既有案件資料夾/分類）
            on_upload_complete: 上傳完成回調函數
        """
        self.case_data = case_data
        self.folder_manager = folder_manager
        self.on_upload_complete = on_upload_complete
        self.selected_files: List[str] = []

        # 準備顯示用的資料夾選項（仍保留 UI，但不再做本機複製）
        self.folder_options = self._get_unified_folder_options()
        self.folder_var = tk.StringVar()

        super().__init__(title="上傳檔案", width=350, height=450, resizable=False, parent=parent)

        # 🔥 統一的視窗置頂處理
        self._setup_window_topmost()

    # ==================== 視窗置頂 ====================

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

    def _restore_topmost_immediately(self):
        """🔥 立即恢復置頂"""
        try:
            if self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
        except Exception as e:
            print(f"恢復視窗置頂失敗: {e}")

    # ==================== UI 內容 ====================

    def _get_unified_folder_options(self):
        """🔥 統一的資料夾選項取得方法（UI 顯示需求，雖然雲端上傳不再使用本機路徑）"""
        try:
            case_folder = None
            try:
                case_folder = self.folder_manager.get_case_folder_path(self.case_data)
            except Exception:
                case_folder = None

            if not case_folder or not os.path.exists(case_folder):
                return ["（僅供顯示）"]

            sub_folders = []
            for item in os.listdir(case_folder):
                item_path = os.path.join(case_folder, item)
                if os.path.isdir(item_path):
                    sub_folders.append(item)
                    if item == "進度追蹤":
                        try:
                            for progress_item in os.listdir(item_path):
                                progress_path = os.path.join(item_path, progress_item)
                                if os.path.isdir(progress_path):
                                    sub_folders.append(f"進度追蹤/{progress_item}")
                        except Exception as e:
                            print(f"掃描進度追蹤子資料夾失敗: {e}")

            return sorted(sub_folders) if sub_folders else ["（僅供顯示）"]
        except Exception as e:
            print(f"取得資料夾選項失敗: {e}")
            return ["（僅供顯示）"]

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

        # 目標資料夾選擇（僅 UI）
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
            font=AppConfig.FONTS.get('text') or AppConfig.FONTS.get('default')
        ).pack(anchor='w')

    def _create_folder_selection_section(self, parent):
        """建立資料夾選擇區域（僅 UI）"""
        folder_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        folder_frame.pack(fill='x', pady=(10, 10))

        tk.Label(
            folder_frame,
            text="目標分類（顯示用）：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS.get('text') or AppConfig.FONTS.get('default')
        ).pack(anchor='w', pady=(0, 5))

        self.folder_combo = ttk.Combobox(
            folder_frame,
            textvariable=self.folder_var,
            values=self.folder_options,
            state='readonly',
            width=40
        )
        self.folder_combo.pack(fill='x')

        # 預設選擇第一個
        if self.folder_options:
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
            font=AppConfig.FONTS.get('text') or AppConfig.FONTS.get('default')
        ).pack(anchor='w', pady=(0, 5))

        # 檔案列表
        self.file_listbox = tk.Listbox(
            file_frame,
            height=4,
            bg='white',
            fg='black',
            font=AppConfig.FONTS.get('text') or AppConfig.FONTS.get('default')
        )
        self.file_listbox.pack(fill='both', expand=True, pady=(0, 10))

        # 檔案操作按鈕
        self._create_file_operation_buttons(file_frame)

    def _create_file_operation_buttons(self, parent):
        """建立檔案操作按鈕"""
        file_btn_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        file_btn_frame.pack(fill='x')

        # 新增檔案
        add_file_btn = tk.Button(
            file_btn_frame,
            text='選擇檔案',
            command=self._select_files_with_topmost,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS.get('button') or AppConfig.FONTS.get('default'),
            width=10,
            height=1
        )
        add_file_btn.pack(side='left', padx=(0, 5))

        # 移除檔案
        remove_file_btn = tk.Button(
            file_btn_frame,
            text='移除',
            command=self._remove_selected_file,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS.get('button') or AppConfig.FONTS.get('default'),
            width=8,
            height=1
        )
        remove_file_btn.pack(side='left', padx=5)

        # 清空
        clear_files_btn = tk.Button(
            file_btn_frame,
            text='清空',
            command=self._clear_all_files,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS.get('button') or AppConfig.FONTS.get('default'),
            width=8,
            height=1
        )
        clear_files_btn.pack(side='left', padx=5)

    def _create_action_buttons(self, parent):
        """建立操作按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=20)

        # 上傳
        upload_btn = tk.Button(
            button_frame,
            text='開始上傳',
            command=self._start_upload_with_topmost,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS.get('button') or AppConfig.FONTS.get('default'),
            width=10,
            height=1
        )
        upload_btn.pack(side='left', padx=5)

        # 取消
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS.get('button') or AppConfig.FONTS.get('default'),
            width=8,
            height=1
        )
        cancel_btn.pack(side='left', padx=5)

    # ==================== 互動動作 ====================

    def _select_files_with_topmost(self):
        """選擇檔案（暫時取消置頂，選完再恢復）"""
        try:
            self.window.attributes('-topmost', False)
            files = filedialog.askopenfilenames(
                title="選擇要上傳的檔案",
                parent=self.window,
                filetypes=[
                    ("所有檔案", "*.*"),
                    ("圖片", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff"),
                    ("音訊", "*.mp3 *.wav *.flac *.aac *.ogg"),
                    ("影片", "*.mp4 *.avi *.mkv *.mov *.wmv"),
                    ("文件", "*.pdf *.doc *.docx *.txt *.rtf"),
                    ("Excel", "*.xlsx *.xls"),
                    ("壓縮", "*.zip *.rar *.7z")
                ]
            )
            self._restore_topmost_immediately()

            if files:
                for file_path in files:
                    if file_path not in self.selected_files:
                        self.selected_files.append(file_path)
                self._update_file_list_display()

        except Exception as e:
            print(f"選擇檔案時發生錯誤: {e}")
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
            self.file_listbox.insert(tk.END, os.path.basename(file_path))

    def _start_upload_with_topmost(self):
        """開始上傳檔案（雲端）"""
        try:
            if not self.selected_files:
                self._show_topmost_message("error", "請先選擇要上傳的檔案")
                return

            # 這裡 `selected_folder` 只作為 UI 顯示用途（雲端上傳不需要本機目錄）
            selected_folder = self.folder_var.get() or "（未指定）"

            # 執行雲端上傳
            self._execute_file_upload(selected_folder)

        except Exception as e:
            print(f"上傳檔案時發生錯誤: {e}")
            self._show_topmost_message("error", f"上傳過程發生錯誤：{str(e)}")

    # ==================== 雲端上傳核心 ====================

    def _execute_file_upload(self, selected_folder: str):
        """呼叫後端 /api/files/upload 將檔案上傳到雲端資料庫"""
        success_count = 0
        error_files: List[str] = []

        # 從案件資料取 client_id / case_id（大小寫兼容）
        client_id = getattr(self.case_data, "client_id", "") or getattr(self.case_data, "clientId", "") or ""
        case_id   = getattr(self.case_data, "case_id", "") or getattr(self.case_data, "caseId", "") or ""

        if not client_id or not case_id:
            self._show_topmost_message("error", "缺少 client_id 或 case_id，無法上傳。\n請確認案件資料是否完整。")
            return

        # 自動取得 JWT
        token = _get_bearer_token_from_runtime()
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        for file_path in self.selected_files:
            try:
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    files = {"file": (filename, f)}
                    data = {
                            "client_id": client_id,
                            "case_id": case_id,
                            "uploaded_by": os.getenv("UPLOADER_NAME", "desktop-app"),
                            "client_name": getattr(self.case_data, "client_name", None),
                            "case_type": getattr(self.case_data, "case_type", None),
                            "progress": getattr(self.case_data, "progress", None),
                            "court": getattr(self.case_data, "court", None),
                            "division": getattr(self.case_data, "division", None),
                            "metadata": json.dumps({
                                "progress_stages": getattr(self.case_data, "progress_stages", {}) or {},
                                "progress_notes": getattr(self.case_data, "progress_notes", {}) or {},
                                "progress_times": getattr(self.case_data, "progress_times", {}) or {},

                            })
                        }

                    resp = requests.post(
                        UPLOAD_ENDPOINT,
                        data=data,
                        files=files,
                        headers=headers,
                        timeout=60
                    )

                if 200 <= resp.status_code < 300:
                    success_count += 1
                    print(f"檔案上傳成功: {filename} -> {UPLOAD_ENDPOINT}")
                else:
                    error_files.append(f"{filename}: HTTP {resp.status_code} {resp.text}")
                    print(f"檔案上傳失敗: {filename} - {resp.text}")

            except Exception as file_error:
                error_files.append(f"{os.path.basename(file_path)}: {str(file_error)}")
                print(f"檔案上傳例外: {file_path} - {file_error}")

        self._show_upload_result(success_count, error_files, selected_folder)

    # ==================== 結果/訊息 ====================

    def _show_upload_result(self, success_count: int, error_files: List[str], selected_folder: str):
        """顯示上傳結果"""
        if success_count > 0 and not error_files:
            message = f"上傳完成！\n\n成功上傳 {success_count} 個檔案。"
            self._show_topmost_message("success", message)
            if self.on_upload_complete:
                self.on_upload_complete()
            self.close()
            return

        # 有部分或全部失敗
        lines = []
        if success_count:
            lines.append(f"成功 {success_count} 個")
        if error_files:
            lines.append("失敗清單（前5筆）：\n" + "\n".join(error_files[:5]))
            if len(error_files) > 5:
                lines.append(f"... 以及其他 {len(error_files) - 5} 個")

        message = "上傳完成（包含失敗）。\n\n" + "\n\n".join(lines) if lines else "沒有檔案成功上傳。"
        level = "warning" if success_count else "error"
        self._show_topmost_message(level, message)

    def _show_topmost_message(self, message_type: str, message: str):
        """顯示置頂訊息對話框"""
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

            # 確保對話框置頂與置中
            if hasattr(dialog, 'window') and dialog.window:
                dialog.window.attributes('-topmost', True)
                dialog.window.update_idletasks()
                screen_width = dialog.window.winfo_screenwidth()
                screen_height = dialog.window.winfo_screenheight()
                dialog_width = dialog.window.winfo_reqwidth()
                dialog_height = dialog.window.winfo_reqheight()
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2
                dialog.window.geometry(f"+{x}+{y}")
                dialog.window.wait_window()

            # 恢復主視窗置頂
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

    # ==================== 對外 API ====================

    @staticmethod
    def show_upload_dialog(parent, case_data: CaseData, folder_manager, on_upload_complete: Callable = None):
        """顯示上傳檔案對話框"""
        dialog = UploadFileDialog(parent, case_data, folder_manager, on_upload_complete)
        dialog.window.wait_window()
