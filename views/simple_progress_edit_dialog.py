# views/simple_progress_edit_dialog.py
# 簡單進度編輯對話框 - 徹底修正版本
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from datetime import datetime

try:
    from tkcalendar import DateEntry
except ImportError:
    print("警告：tkcalendar 套件未安裝，請執行：pip install tkcalendar")
    DateEntry = None

from config.settings import AppConfig
from models.case_model import CaseData
from views.base_window import BaseWindow

# 使用安全導入方式
try:
    from views.dialogs import UnifiedMessageDialog, UnifiedConfirmDialog
except ImportError as e:
    print(f"警告：無法導入對話框模組 - {e}")
    import tkinter.messagebox as messagebox

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
        @staticmethod
        def ask_stage_update(parent, stage_name):
            return messagebox.askyesno(
                "確認更新",
                f"階段「{stage_name}」已存在，是否要更新日期和備註？"
            )


class SimpleProgressEditDialog(BaseWindow):
    """簡單進度編輯對話框 - 徹底修正版本"""

    def __init__(self, parent=None, case_data: Optional[CaseData] = None,
                 stage_name: str = None, stage_date: str = None,
                 on_save: Optional[Callable] = None, mode='edit'):
        """
        初始化進度編輯對話框

        Args:
            parent: 父視窗
            case_data: 案件資料
            stage_name: 要編輯的階段名稱
            stage_date: 要編輯的階段日期
            on_save: 儲存回調函數
            mode: 模式 ('edit' 或 'add')
        """
        self.case_data = case_data
        self.stage_name = stage_name
        self.stage_date = stage_date
        self.on_save = on_save
        self.mode = mode
        self.result = None
        self.parent_window = parent
        self.is_destroyed = False  # 🔥 新增：追蹤視窗是否已銷毀

        title_text = "新增進度階段" if mode == 'add' else f"編輯進度階段 - {stage_name}"

        super().__init__(title=title_text, width=400, height=500, resizable=False, parent=parent)

        self._ensure_dialog_topmost()

    def _create_layout(self):
        """覆寫父類別的佈局方法"""
        super()._create_layout()
        self.create_widgets()

    def _ensure_dialog_topmost(self):
        """確保對話框置頂顯示"""
        if self.window and hasattr(self.window, 'winfo_exists'):
            try:
                self.window.attributes('-topmost', True)
                self.window.lift()
                self.window.focus_force()
                self.window.after(100, self._force_topmost_again)
            except tk.TclError:
                pass

    def _force_topmost_again(self):
        """延遲確保置頂"""
        try:
            if not self.is_destroyed and self.window and self.window.winfo_exists():
                self.window.attributes('-topmost', True)
                self.window.lift()
        except tk.TclError:
            pass

    def create_widgets(self):
        """建立對話框控件"""
        # 主要編輯區域
        edit_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg'],
            padx=20,
            pady=20
        )
        edit_frame.pack(fill='both', expand=True)

        # 配置網格權重
        edit_frame.grid_columnconfigure(1, weight=1)

        # 階段名稱
        tk.Label(
            edit_frame,
            text="階段名稱：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=0, column=0, sticky='w', padx=(0, 10), pady=10)

        if self.mode == 'add':
            # 新增模式：可選擇階段
            case_type = self.case_data.case_type if self.case_data else ''
            progress_options = AppConfig.get_progress_options(case_type)

            self.stage_var = tk.StringVar(value=self.stage_name or '')
            self.stage_combo = ttk.Combobox(
                edit_frame,
                textvariable=self.stage_var,
                values=progress_options,
                state='normal',
                width=25,
                font=AppConfig.FONTS['text']
            )
            self.stage_combo.grid(row=0, column=1, sticky='w', pady=10)
        else:
            # 編輯模式：顯示階段名稱
            self.stage_var = tk.StringVar(value=self.stage_name or '')
            stage_label = tk.Label(
                edit_frame,
                textvariable=self.stage_var,
                bg=AppConfig.COLORS['window_bg'],
                fg='#4CAF50',
                font=AppConfig.FONTS['button']
            )
            stage_label.grid(row=0, column=1, sticky='w', pady=10)

        # 日期選擇
        tk.Label(
            edit_frame,
            text="階段日期：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=1, column=0, sticky='w', padx=(0, 10), pady=10)

        # 解析現有日期
        initial_date = datetime.now().date()
        if self.stage_date:
            try:
                initial_date = datetime.strptime(self.stage_date, '%Y-%m-%d').date()
            except:
                pass

        if DateEntry is not None:
            self.date_entry = DateEntry(
                edit_frame,
                width=25,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                locale='zh_TW',
                font=AppConfig.FONTS['text']
            )
            self.date_entry.set_date(initial_date)
            self._setup_date_entry_events()
        else:
            # 回退方案
            self.date_entry = tk.Entry(
                edit_frame,
                width=27,
                bg='white',
                fg='black',
                font=AppConfig.FONTS['text']
            )
            self.date_entry.insert(0, initial_date.strftime('%Y-%m-%d'))

        self.date_entry.grid(row=1, column=1, sticky='w', pady=10)

        # 時間欄位
        tk.Label(
            edit_frame,
            text="時間：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=2, column=0, sticky='w', padx=(0, 10), pady=10)

        # 取得現有時間
        existing_time = ""
        if self.case_data and self.stage_name:
            existing_time = self.case_data.get_stage_time(self.stage_name)

        self.time_entry = tk.Entry(
            edit_frame,
            width=27,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text']
        )
        self.time_entry.grid(row=2, column=1, sticky='w', pady=10)

        # 如果有現有時間，填入
        if existing_time:
            self.time_entry.insert(0, existing_time)

        # 時間格式說明
        time_help = tk.Label(
            edit_frame,
            text="（格式：HH:MM，如 14:30）",
            bg=AppConfig.COLORS['window_bg'],
            fg='#AAAAAA',
            font=('Microsoft JhengHei', 8)
        )
        time_help.grid(row=3, column=1, sticky='w', pady=(0, 5))

        # 備註欄位
        tk.Label(
            edit_frame,
            text="備註：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=4, column=0, sticky='nw', padx=(0, 10), pady=10)

        # 取得現有備註
        existing_note = ""
        if self.case_data and self.stage_name:
            existing_note = self.case_data.get_stage_note(self.stage_name)

        # 多行文字輸入框
        self.note_text = tk.Text(
            edit_frame,
            width=30,
            height=2,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text'],
            wrap=tk.WORD
        )
        self.note_text.grid(row=4, column=1, sticky='w', pady=10)

        # 如果有現有備註，填入
        if existing_note:
            self.note_text.insert('1.0', existing_note)

        # 按鈕區域
        button_frame = tk.Frame(
            edit_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)

        # 儲存按鈕
        save_btn = tk.Button(
            button_frame,
            text="儲存",
            command=self._on_save,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        save_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text="取消",
            command=self.close,
            bg='#757575',
            fg='white',
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        cancel_btn.pack(side='left', padx=5)

        # 設定預設焦點
        save_btn.focus_set()

        # 綁定快捷鍵
        self.window.bind('<Return>', lambda e: self._on_save())
        self.window.bind('<Escape>', lambda e: self.close())

    def _setup_date_entry_events(self):
        """設定日期選擇器事件"""
        if hasattr(self, 'date_entry') and self.date_entry:
            def on_date_selected(event=None):
                # 確保對話框保持置頂
                self.window.after(10, self._force_topmost_again)

            self.date_entry.bind('<<DateEntrySelected>>', on_date_selected)

    def _on_save(self):
        """🔥 統一流程：所有情況都是 驗證 → 銷毀視窗 → 顯示確認/結果"""
        try:
            # 第一步：驗證輸入資料
            validation_result = self._validate_input()
            if not validation_result['valid']:
                # 驗證失敗，顯示錯誤訊息但保持視窗開啟
                UnifiedMessageDialog.show_error(self.window, validation_result['message'])
                return

            # 第二步：準備結果資料
            self.result = validation_result['data']

            # 🔥 關鍵修正：所有情況都先銷毀視窗
            parent_window = self.parent_window
            on_save_callback = self.on_save
            result_data = self.result
            mode = self.mode

            # 立即銷毀編輯視窗
            self.is_destroyed = True
            self.window.destroy()

            # 第三步：根據不同情況處理後續邏輯
            need_confirmation = (
                mode == 'add' and
                self.case_data and
                validation_result['data']['stage_name'] in self.case_data.progress_stages
            )

            if need_confirmation:
                # 🔥 情況1：需要確認覆蓋 → 顯示確認對話框
                stage_name = validation_result['data']['stage_name']
                should_update = UnifiedConfirmDialog.ask_stage_update(parent_window, stage_name)

                if should_update:
                    # 用戶確認更新，執行儲存邏輯
                    if on_save_callback:
                        success = on_save_callback(result_data)
                        if success:
                            # 顯示成功訊息
                            UnifiedMessageDialog.show_success(
                                parent_window,
                                f"已更新進度階段「{stage_name}」"
                            )
                else:
                    # 用戶取消，不執行任何操作
                    print(f"用戶取消更新階段：{stage_name}")

            else:
                # 🔥 情況2：新增新階段或編輯現有階段 → 直接執行並顯示結果
                if on_save_callback:
                    success = on_save_callback(result_data)
                    if success:
                        # 根據模式顯示不同的成功訊息
                        if mode == 'add':
                            message = f"已新增進度階段「{result_data['stage_name']}」"
                        else:
                            message = f"已更新進度階段「{result_data['stage_name']}」"

                        UnifiedMessageDialog.show_success(parent_window, message)
                    else:
                        # 顯示失敗訊息
                        if mode == 'add':
                            error_message = "新增階段失敗，請檢查案件狀態"
                        else:
                            error_message = "更新階段失敗，請檢查案件狀態"

                        UnifiedMessageDialog.show_error(parent_window, error_message)

        except Exception as e:
            print(f"儲存階段時發生錯誤: {e}")
            # 如果發生錯誤，在父視窗顯示錯誤訊息
            if self.parent_window:
                UnifiedMessageDialog.show_error(self.parent_window, f"儲存時發生錯誤：{str(e)}")
            else:
                print(f"無法顯示錯誤訊息：{str(e)}")

    def _handle_stage_exists_confirmation(self, result_data):
        """移除此方法，不再需要"""
        pass

    def _validate_input(self) -> dict:
        """驗證輸入資料"""
        try:
            # 驗證階段名稱
            stage_name = self.stage_var.get().strip()
            if not stage_name:
                return {'valid': False, 'message': "請輸入階段名稱"}

            # 驗證日期
            if DateEntry is not None and hasattr(self.date_entry, 'get_date'):
                stage_date = self.date_entry.get_date().strftime('%Y-%m-%d')
            else:
                stage_date = self.date_entry.get().strip()
                if not stage_date:
                    return {'valid': False, 'message': "請選擇階段日期"}

                # 驗證日期格式
                try:
                    datetime.strptime(stage_date, '%Y-%m-%d')
                except ValueError:
                    return {'valid': False, 'message': "日期格式錯誤，請使用 YYYY-MM-DD 格式"}

            # 驗證時間
            time = self.time_entry.get().strip()
            if time:
                try:
                    time_parts = time.split(':')
                    if len(time_parts) != 2:
                        raise ValueError("時間格式錯誤")
                    hour, minute = int(time_parts[0]), int(time_parts[1])
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("時間範圍錯誤")
                except ValueError:
                    return {'valid': False, 'message': "時間格式錯誤，請使用 HH:MM 格式（如 14:30）"}

            # 取得備註
            note = self.note_text.get('1.0', tk.END).strip()

            # 返回驗證結果
            return {
                'valid': True,
                'data': {
                    'stage_name': stage_name,
                    'stage_date': stage_date,
                    'time': time,
                    'note': note,
                    'original_stage': self.stage_name
                }
            }

        except Exception as e:
            return {'valid': False, 'message': f"資料驗證失敗：{str(e)}"}

    def close(self):
        """🔥 修正：關閉對話框"""
        try:
            self.is_destroyed = True
            if self.window:
                self.window.destroy()
        except:
            pass

    @staticmethod
    def show_edit_dialog(parent, case_data: CaseData, stage_name: str, stage_date: str, on_save: Callable):
        """顯示編輯階段對話框"""
        dialog = SimpleProgressEditDialog(
            parent, case_data, stage_name, stage_date, on_save, mode='edit'
        )
        dialog.window.wait_window()
        return dialog.result

    @staticmethod
    def show_add_dialog(parent, case_data: CaseData, on_save: Callable):
        """顯示新增階段對話框"""
        dialog = SimpleProgressEditDialog(
            parent, case_data, None, None, on_save, mode='add'
        )
        dialog.window.wait_window()
        return dialog.result