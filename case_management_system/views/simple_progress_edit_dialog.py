import tkinter as tk
from tkinter import ttk, messagebox
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

class SimpleProgressEditDialog(BaseWindow):
    """簡單進度編輯對話框"""

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

        title_text = "新增進度階段" if mode == 'add' else f"編輯進度階段 - {stage_name}"
        super().__init__(title=title_text, width=450, height=250, resizable=False, parent=parent)
        if parent:
            self.window.lift()  # 確保視窗置頂
            self.window.attributes('-topmost', True)  # 暫時設為最頂層
            self.window.after(100, lambda: self.window.attributes('-topmost', False))  # 100ms後取消最頂層
    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._create_dialog_content()

    def _create_dialog_content(self):
        """建立對話框內容"""
        # 案件資訊顯示
        if self.case_data:
            info_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
            info_frame.pack(fill='x', padx=20, pady=(20, 10))

            # 使用統一的案件顯示格式
            case_display_name = AppConfig.format_case_display_name(self.case_data)
            case_type = self.case_data.case_type

            info_text = f"案件：{case_display_name} ({case_type})"
            tk.Label(
                info_frame,
                text=info_text,
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['text']
            ).pack(anchor='w')

        # 編輯區域
        edit_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        edit_frame.pack(fill='x', padx=20, pady=10)

        # 階段名稱
        tk.Label(
            edit_frame,
            text="進度階段：",
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
                state='normal',  # 允許輸入自訂階段
                width=25,
                font=AppConfig.FONTS['text']  # 使用統一字體
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
                font=AppConfig.FONTS['button']  # 使用按鈕字體大小
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

            # 重要：綁定 DateEntry 的特殊事件
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

        # 按鈕區域
        self._create_buttons()

    def _setup_date_entry_events(self):
        """設定日期選擇器的事件處理"""
        # 綁定按鈕點擊事件（展開日曆）
        try:
            # DateEntry 內部有一個按鈕用於展開日曆
            for child in self.date_entry.winfo_children():
                if isinstance(child, tk.Button):
                    child.bind('<Button-1>', self._on_calendar_button_click, add='+')
                    break
        except:
            pass

        # 綁定其他相關事件
        self.date_entry.bind('<Button-1>', self._on_date_entry_click, add='+')
        self.date_entry.bind('<<DateEntrySelected>>', self._on_date_selected, add='+')
        self.date_entry.bind('<<CalendarOpened>>', self._on_calendar_opened, add='+')
        self.date_entry.bind('<<CalendarClosed>>', self._on_calendar_closed, add='+')

    def _on_calendar_button_click(self, event):
        """日曆按鈕點擊事件"""
        # 完全釋放對話框的控制權，讓日曆優先
        self._release_dialog_control()

    def _release_dialog_control(self):
        """釋放對話框控制權，讓日曆優先"""
        try:
            # 釋放 grab
            self.window.grab_release()
            # 取消置頂
            self.window.attributes('-topmost', False)
            # 降低對話框層級
            self.window.lower()
        except:
            pass

    def _ensure_calendar_topmost(self):
        """確保日曆視窗置頂"""
        try:
            # 嘗試找到所有的 Toplevel 視窗
            for widget in self.window.winfo_toplevel().winfo_children():
                if isinstance(widget, tk.Toplevel):
                    # 檢查是否是日曆視窗（通常會有特定的類名或標題）
                    try:
                        if 'calendar' in widget.winfo_class().lower() or 'date' in str(widget).lower():
                            widget.lift()
                            widget.attributes('-topmost', True)
                            widget.focus_force()
                            break
                    except:
                        continue

            # 通用方法：將所有新的 Toplevel 視窗置頂
            all_windows = self.window.tk.call('wm', 'stackorder', self.window._w)
            if len(all_windows) > 1:
                # 假設最新的視窗是日曆
                latest_window = all_windows[-1]
                try:
                    latest_window_obj = self.window.nametowidget(latest_window)
                    if latest_window_obj != self.window:
                        latest_window_obj.lift()
                        latest_window_obj.attributes('-topmost', True)
                        latest_window_obj.focus_force()
                except:
                    pass

        except Exception as e:
            print(f"確保日曆置頂失敗: {e}")

    def _on_date_entry_click(self, event):
        """日期輸入框點擊事件"""
        # 檢查是否點擊了下拉按鈕區域
        widget_width = self.date_entry.winfo_width()
        click_x = event.x

        # 如果點擊在右側按鈕區域（通常是最右邊的20-30像素）
        if click_x > widget_width - 30:
            self._release_dialog_control()

    def _on_calendar_opened(self, event):
        """日曆展開事件"""
        self._release_dialog_control()
        # 嘗試找到日曆視窗並置頂
        self.window.after(100, self._ensure_calendar_topmost)

    def _on_calendar_closed(self, event):
        """日曆關閉事件"""
        # 日曆關閉後恢復對話框控制
        self.window.after(100, self._restore_dialog_control)

    def _on_date_selected(self, event):
        """日期選擇完成事件"""
        # 日期選擇完成後，恢復對話框控制
        self.window.after(150, self._restore_dialog_control)

    def _restore_dialog_control(self):
        """恢復對話框控制權"""
        try:
            if self.window.winfo_exists():
                # 重新設定對話框置頂
                self.window.lift()
                self.window.attributes('-topmost', True)
                self.window.focus_force()
                self.window.grab_set()

                # 短暫置頂後取消，避免永遠置頂
                self.window.after(200, lambda: self.window.attributes('-topmost', False))

                # 確保日曆視窗已關閉
                self._ensure_calendar_closed()
        except:
            pass

    def _ensure_calendar_closed(self):
        """確保日曆視窗已關閉"""
        try:
            # 移除任何殘留的置頂日曆視窗
            all_windows = self.window.tk.call('wm', 'stackorder', self.window._w)
            for window_name in all_windows:
                try:
                    window_obj = self.window.nametowidget(window_name)
                    if (window_obj != self.window and
                        isinstance(window_obj, tk.Toplevel) and
                        ('calendar' in str(window_obj).lower() or 'date' in str(window_obj).lower())):
                        window_obj.attributes('-topmost', False)
                except:
                    continue
        except:
            pass

    def _restore_grab_after_calendar(self):
        """日曆操作後恢復對話框控制"""
        try:
            if self.window.winfo_exists():
                self.window.lift()
                self.window.focus_force()
                self.window.grab_set()
                # 確保對話框在最前面
                self.window.attributes('-topmost', True)
                self.window.after(100, lambda: self.window.attributes('-topmost', False))
        except:
            pass

    def _on_date_selected(self, event):
        """日期選擇完成事件"""
        # 重新設定焦點和grab
        self.window.after(50, self._restore_grab)

    def _restore_grab(self):
        """恢復對話框的焦點控制"""
        try:
            self.window.lift()
            self.window.focus_force()
            self.window.grab_set()
        except:
            # 如果視窗已經關閉，忽略錯誤
            pass

    def _create_buttons(self):
        """建立按鈕"""
        button_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom', pady=20)

        # 儲存按鈕
        save_btn = tk.Button(
            button_frame,
            text='儲存',
            command=self._on_save,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用按鈕字體大小
            width=8,
            height=1
        )
        save_btn.pack(side='left', padx=5)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],  # 使用按鈕字體大小
            width=8,
            height=1
        )
        cancel_btn.pack(side='left', padx=5)

    def _on_save(self):
        """儲存按鈕事件"""
        try:
            # 取得階段名稱
            stage_name = self.stage_var.get().strip()
            if not stage_name:
                messagebox.showerror("錯誤", "請輸入或選擇進度階段")
                return

            # 取得日期
            if DateEntry is not None and hasattr(self.date_entry, 'get_date'):
                stage_date = self.date_entry.get_date().strftime('%Y-%m-%d')
            else:
                date_str = self.date_entry.get().strip()
                try:
                    datetime.strptime(date_str, '%Y-%m-%d')
                    stage_date = date_str
                except ValueError:
                    messagebox.showerror("錯誤", "日期格式錯誤，請使用 YYYY-MM-DD 格式")
                    return

            # 新增模式：檢查階段是否已存在
            if self.mode == 'add' and self.case_data:
                if stage_name in self.case_data.progress_stages:
                    if not messagebox.askyesno("確認", f"階段「{stage_name}」已存在，是否要更新日期？"):
                        return

            self.result = {
                'stage_name': stage_name,
                'stage_date': stage_date,
                'original_stage': self.stage_name  # 原始階段名稱（編輯模式用）
            }

            # 呼叫回調函數
            if self.on_save:
                success = self.on_save(self.result)
                if success:
                    self.close()
            else:
                self.close()

        except Exception as e:
            messagebox.showerror("錯誤", f"儲存時發生錯誤：{str(e)}")

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