#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
from typing import Optional, Callable
from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow
from views.dialogs import UnifiedMessageDialog

class CaseTransferDialog(BaseWindow):
    """結案轉移對話框"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 case_controller=None, on_transfer_complete: Optional[Callable] = None):
        """
        初始化結案轉移對話框

        Args:
            parent: 父視窗
            case_data: 選中的案件資料
            case_controller: 案件控制器
            on_transfer_complete: 轉移完成回調函數
        """
        self.case_data = case_data
        self.case_controller = case_controller
        self.on_transfer_complete = on_transfer_complete
        self.transfer_folder = None
        self.transfer_settings = self._load_transfer_settings()

        title = "結案轉移"
        super().__init__(title=title, width=500, height=450, resizable=False, parent=parent)
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

    def _load_transfer_settings(self):
        """載入轉移設定"""
        try:
            import json
            settings_file = os.path.join(os.path.dirname(__file__), "transfer_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"載入轉移設定失敗: {e}")

        return {'default_transfer_folder': None}

    def _save_transfer_settings(self):
        """儲存轉移設定"""
        try:
            import json
            settings_file = os.path.join(os.path.dirname(__file__), "transfer_settings.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.transfer_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存轉移設定失敗: {e}")

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._create_transfer_content()

    def _create_transfer_content(self):
        """建立轉移對話框內容"""
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

        # 案件資訊顯示
        info_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        info_frame.pack(fill='x', pady=(0, 20))

        # 標題
        tk.Label(
            info_frame,
            text="準備轉移已結案案件",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['title']
        ).pack(anchor='w', pady=(0, 10))

        # 案件編號
        tk.Label(
            info_frame,
            text=f"案件編號：{self.case_data.case_id}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=2)

        # 當事人名稱
        tk.Label(
            info_frame,
            text=f"當事人：{self.case_data.client}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=2)

        # 案件類型
        tk.Label(
            info_frame,
            text=f"案件類型：{self.case_data.case_type}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=2)

        # 分隔線
        separator = tk.Frame(main_frame, bg='#555555', height=1)
        separator.pack(fill='x')

        # 轉移資料夾選擇
        folder_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        folder_frame.pack(fill='x',pady=(0,5))

        tk.Label(
            folder_frame,
            text="轉移目標位置：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(5, 5))

        # 資料夾路徑顯示
        path_frame = tk.Frame(folder_frame, bg=AppConfig.COLORS['window_bg'])
        path_frame.pack(fill='x', pady=(0, 0))

        self.folder_path_var = tk.StringVar()
        # 初始設定為之前儲存的路徑（如果有）
        saved_folder = self.transfer_settings.get('default_transfer_folder')
        if saved_folder and os.path.exists(saved_folder):
            self.transfer_folder = saved_folder
            self.folder_path_var.set(saved_folder)
        else:
            self.folder_path_var.set("請選擇轉移目標資料夾...")

        self.folder_path_label = tk.Label(
            path_frame,
            textvariable=self.folder_path_var,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['button'],
            relief='sunken',
            anchor='w',
            wraplength=250,
            height=1
        )
        self.folder_path_label.pack(side='left', fill='x', expand=True, padx=(0, 10))

        # 瀏覽按鈕
        browse_btn = tk.Button(
            path_frame,
            text='瀏覽',
            command=self._select_transfer_folder,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=6,
            height=1
        )
        browse_btn.pack(side='right')

        # 說明文字
        note_text = ("⚠️此操作將會把「該案當事人資料夾」中移動到指定位置。\n"
                    "建議在執行前先備份重要資料。")

        tk.Label(
            main_frame,
            text=note_text,
            bg=AppConfig.COLORS['window_bg'],
            fg='#FF9800',
            font=AppConfig.FONTS['button'],
            justify='left',
            wraplength=450
        ).pack(pady=(5, 5))

        # 按鈕區域
        self._create_transfer_buttons(main_frame)

    def _select_transfer_folder(self):
        """選擇轉移目標資料夾 - 🔥 修正：檔案對話框置頂處理"""
        try:
            # 🔥 新增：暫時取消主視窗置頂，讓檔案對話框正常顯示
            original_topmost = self.window.attributes('-topmost')
            self.window.attributes('-topmost', False)

            folder_path = filedialog.askdirectory(
                title="選擇目標資料夾",
                parent=self.window,  # 🔥 確保指定父視窗
                initialdir=self.transfer_folder or os.path.expanduser('~')
            )

            # 🔥 新增：檔案對話框關閉後立即恢復置頂
            self.window.after(100, lambda: self._restore_topmost_after_folder_dialog(original_topmost))

            if folder_path:
                self.transfer_folder = folder_path
                self.folder_path_var.set(folder_path)

                # 儲存設定
                self.transfer_settings['default_transfer_folder'] = folder_path
                self._save_transfer_settings()

                # 🔥 新增：確保對話框重新置頂
                self.window.lift()
                self.window.focus_force()

        except Exception as e:
            print(f"選擇轉移資料夾時發生錯誤: {e}")
            UnifiedMessageDialog.show_error(self.window, f"選擇資料夾時發生錯誤：{str(e)}")

    def _restore_topmost_after_folder_dialog(self, original_topmost):
        """🔥 新增：檔案對話框關閉後恢復置頂狀態"""
        try:
            if self.window and self.window.winfo_exists():
                # 恢復原本的置頂狀態
                self.window.attributes('-topmost', True)  # 強制置頂
                self.window.lift()
                self.window.focus_force()
                print("結案轉移視窗已恢復置頂")
        except Exception as e:
            print(f"恢復轉移視窗置頂失敗: {e}")

    def _on_transfer(self):
        """執行結案轉移 - 🔥 修正：確認對話框置頂處理"""
        if not self.transfer_folder:
            UnifiedMessageDialog.show_warning(self.window, "請先選擇轉移目標資料夾")
            return

        # 取得案件資料夾路徑
        folder_manager = FolderManager(self.case_controller.base_data_folder)
        source_folder = folder_manager.get_case_folder_path(self.case_data)

        if not source_folder or not os.path.exists(source_folder):
            UnifiedMessageDialog.show_error(self.window, "找不到案件資料夾")
            return

        # 建立目標路徑
        target_folder = os.path.join(self.transfer_folder, os.path.basename(source_folder))

        # 檢查目標位置是否已存在同名資料夾
        if os.path.exists(target_folder):
            overwrite_message = (
                f"目標位置已存在相同名稱的資料夾：\n{target_folder}\n\n"
                f"是否要覆蓋現有資料夾？\n"
                f"⚠️ 警告：此操作將刪除目標位置的所有檔案！"
            )

            # 🔥 修正：使用正確的靜態方法顯示確認對話框
            if not UnifiedConfirmDialog.ask(
                self.window,
                title="目標資料夾已存在",
                message=overwrite_message,
                confirm_text="覆蓋",
                cancel_text="取消"
            ):
                return

            # 刪除現有資料夾
            try:
                shutil.rmtree(target_folder)
            except Exception as e:
                UnifiedMessageDialog.show_error(self.window, f"無法刪除現有資料夾：{str(e)}")
                return

        # 執行轉移
        try:
            shutil.move(source_folder, target_folder)

            # 從案件控制器中刪除案件記錄
            self.case_controller.delete_case(self.case_data.case_id, delete_folder=False)

            success_message = (
                f"結案轉移完成！\n\n"
                f"案件：{AppConfig.format_case_display_name(self.case_data)}\n"
                f"已從：{source_folder}\n"
                f"轉移到：{target_folder}\n\n"
                f"案件記錄已從系統中移除。"
            )

            # 🔥 修正：使用正確的靜態方法顯示成功對話框
            UnifiedMessageDialog.show_success(self.window, success_message)

            # 呼叫完成回調
            if self.on_transfer_complete:
                self.on_transfer_complete()

            # 🔥 修改：延遲關閉並確保焦點正確返回
            self.window.after(100, self._safe_close)

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"轉移過程發生錯誤：{str(e)}")

    def _create_transfer_buttons(self, parent):
        """建立轉移按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=20)

        # 確認轉移按鈕
        confirm_btn = tk.Button(
            button_frame,
            text='確認轉移',
            command=self._start_transfer,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        confirm_btn.pack(side='left', padx=5)

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

    def _start_transfer(self):
        """開始轉移檔案"""
        try:
            # 驗證轉移資料夾
            if not self.transfer_folder:
                UnifiedMessageDialog.show_warning(self.window, "請先選擇轉移目標資料夾位置")
                return

            if not os.path.exists(self.transfer_folder):
                UnifiedMessageDialog.show_error(self.window, "選擇的目標資料夾不存在")
                return

            # 取得來源資料夾路徑
            source_folder = self.case_controller.get_case_folder_path(self.case_data.case_id)
            if not source_folder or not os.path.exists(source_folder):
                UnifiedMessageDialog.show_error(self.window, "找不到案件的當事人資料夾")
                return

            # 建立目標路徑
            folder_name = os.path.basename(source_folder)
            target_folder = os.path.join(self.transfer_folder, folder_name)

            # 檢查目標位置是否已存在同名資料夾
            if os.path.exists(target_folder):
                if not messagebox.askyesno(
                    "資料夾已存在",
                    f"目標位置已存在資料夾「{folder_name}」，是否要覆蓋？\n\n此操作無法復原。"
                ):
                    return

                # 先刪除現有資料夾
                try:
                    shutil.rmtree(target_folder)
                except Exception as e:
                    UnifiedMessageDialog.show_error(self.window, f"無法刪除現有資料夾：{str(e)}")
                    return

            # 執行轉移
            try:
                shutil.move(source_folder, target_folder)

                # 從案件控制器中刪除案件記錄
                self.case_controller.delete_case(self.case_data.case_id, delete_folder=False)

                success_message = (
                    f"結案轉移完成！\n\n"
                    f"轉移到：{target_folder}\n\n"
                )

                UnifiedMessageDialog.show_success(self.window, success_message)

                # 呼叫完成回調
                if self.on_transfer_complete:
                    self.on_transfer_complete()

                # 🔥 修改：延遲關閉並確保焦點正確返回
                self.window.after(100, self._safe_close)

            except Exception as e:
                UnifiedMessageDialog.show_error(self.window, f"轉移過程發生錯誤：{str(e)}")

        except Exception as e:
            print(f"轉移檔案時發生錯誤: {e}")
            UnifiedMessageDialog.show_error(self.window, f"轉移過程發生錯誤：{str(e)}")

    def _safe_close(self):
        """🔥 新增：安全關閉對話框並恢復父視窗焦點"""
        try:
            if self.parent:
                # 先讓父視窗取得焦點
                self.parent.focus_force()
                self.parent.lift()

            # 銷毀對話框
            self.window.destroy()

            # 確保父視窗可以接收事件
            if self.parent:
                self.parent.after(50, lambda: self.parent.focus_set())

        except Exception as e:
            print(f"安全關閉對話框失敗: {e}")
            self.window.destroy()


    def close(self):
        """關閉視窗 - 🔥 修改：確保焦點正確返回"""
        try:
            if self.parent:
                self.parent.focus_force()
                self.parent.lift()

            self.window.destroy()

            if self.parent:
                self.parent.after(50, lambda: self.parent.focus_set())
        except:
            self.window.destroy()

    @staticmethod
    def show_transfer_dialog(parent, case_data: CaseData, case_controller, on_transfer_complete: Callable = None):
        """顯示結案轉移對話框"""
        dialog = CaseTransferDialog(parent, case_data, case_controller, on_transfer_complete)
        dialog.window.wait_window()