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

        # 🔥 修改：調整視窗高度以容納備註欄位
        super().__init__(title=title_text, width=400, height=500, resizable=False, parent=parent)
        if parent:
            self.window.lift()
            self.window.attributes('-topmost', True)
            self.window.after(100, lambda: self.window.attributes('-topmost', False))

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._create_dialog_content()

    def _create_dialog_content(self):
        """建立對話框內容 - 🔥 修改：使用置中佈局"""
        # 🔥 修改：主要內容框架 - 使用置中佈局
        main_content_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_content_frame.pack(expand=True, fill='both')

        # 🔥 修改：表單容器 - 置中顯示
        form_container = tk.Frame(main_content_frame, bg=AppConfig.COLORS['window_bg'])
        form_container.pack(expand=True, anchor='center')

        # 🔥 修改：表單內容 - 減少外距
        form_frame = tk.Frame(form_container, bg=AppConfig.COLORS['window_bg'])
        form_frame.pack(padx=10, pady=10)

        # 案件資訊顯示
        if self.case_data:
            info_frame = tk.Frame(form_frame, bg=AppConfig.COLORS['window_bg'])
            info_frame.pack(fill='x', pady=(0, 10))

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
        edit_frame = tk.Frame(form_frame, bg=AppConfig.COLORS['window_bg'])
        edit_frame.pack(fill='x', pady=10)

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

        # 🔥 新增：時間欄位
        tk.Label(
            edit_frame,
            text="時間：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=2, column=0, sticky='w', padx=(0, 10), pady=10)

        # 🔥 新增：取得現有時間
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

        # 🔥 新增：如果有現有時間，填入
        if existing_time:
            self.time_entry.insert(0, existing_time)

        # 🔥 新增：時間格式說明
        time_help = tk.Label(
            edit_frame,
            text="（格式：HH:MM，如 14:30）",
            bg=AppConfig.COLORS['window_bg'],
            fg='#AAAAAA',
            font=('Microsoft JhengHei', 8)
        )
        time_help.grid(row=3, column=1, sticky='w', pady=(0, 5))

        # 🔥 新增：備註欄位
        tk.Label(
            edit_frame,
            text="備註：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).grid(row=4, column=0, sticky='nw', padx=(0, 10), pady=10)

        # 🔥 新增：取得現有備註
        existing_note = ""
        if self.case_data and self.stage_name:
            existing_note = self.case_data.get_stage_note(self.stage_name)

        # 🔥 新增：多行文字輸入框
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

        # 🔥 新增：如果有現有備註，填入
        if existing_note:
            self.note_text.insert('1.0', existing_note)

        # 🔥 新增：備註說明
        note_help = tk.Label(
            edit_frame,
            text="（選填，若有備註將在進度階段上方顯示便籤圖示）",
            bg=AppConfig.COLORS['window_bg'],
            fg='#AAAAAA',
            font=('Microsoft JhengHei', 8)
        )
        note_help.grid(row=5, column=1, sticky='w', pady=(0, 10))

        # 按鈕區域
        self._create_buttons(form_frame)

    def _setup_date_entry_events(self):
        """設定日期選擇器的事件處理"""
        # 綁定按鈕點擊事件（展開日曆）
        try:
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
        self._release_dialog_control()

    def _release_dialog_control(self):
        """釋放對話框控制權，讓日曆優先"""
        try:
            self.window.grab_release()
            self.window.attributes('-topmost', False)
            self.window.lower()
        except:
            pass

    def _ensure_calendar_topmost(self):
        """確保日曆視窗置頂"""
        try:
            for widget in self.window.winfo_toplevel().winfo_children():
                if isinstance(widget, tk.Toplevel):
                    try:
                        if 'calendar' in widget.winfo_class().lower() or 'date' in str(widget).lower():
                            widget.lift()
                            widget.attributes('-topmost', True)
                            widget.focus_force()
                            break
                    except:
                        continue

            all_windows = self.window.tk.call('wm', 'stackorder', self.window._w)
            if len(all_windows) > 1:
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
        widget_width = self.date_entry.winfo_width()
        click_x = event.x

        if click_x > widget_width - 30:
            self._release_dialog_control()

    def _on_calendar_opened(self, event):
        """日曆展開事件"""
        self._release_dialog_control()
        self.window.after(100, self._ensure_calendar_topmost)

    def _on_calendar_closed(self, event):
        """日曆關閉事件"""
        self.window.after(100, self._restore_dialog_control)

    def _on_date_selected(self, event):
        """日期選擇完成事件"""
        self.window.after(150, self._restore_dialog_control)

    def _restore_dialog_control(self):
        """恢復對話框控制權"""
        try:
            if self.window.winfo_exists():
                self.window.lift()
                self.window.attributes('-topmost', True)
                self.window.focus_force()
                self.window.grab_set()
                self.window.after(200, lambda: self.window.attributes('-topmost', False))
                self._ensure_calendar_closed()
        except:
            pass

    def _ensure_calendar_closed(self):
        """確保日曆視窗已關閉"""
        try:
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

    def _create_buttons(self, parent):
        """建立按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=20)

        # 儲存按鈕
        save_btn = tk.Button(
            button_frame,
            text='確定',  # 🔥 修改：改為"確定"更符合一般習慣
            command=self._on_save,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
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
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        cancel_btn.pack(side='left', padx=5)

    def _on_save(self):
        """儲存按鈕事件 - 🔥 修改：加入備註處理"""
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

            # 🔥 新增：取得時間
            time = self.time_entry.get().strip()

            # 🔥 新增：驗證時間格式（如果有輸入時間）
            if time:
                try:
                    # 簡單驗證時間格式 HH:MM
                    time_parts = time.split(':')
                    if len(time_parts) != 2:
                        raise ValueError("時間格式錯誤")
                    hour, minute = int(time_parts[0]), int(time_parts[1])
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("時間範圍錯誤")
                except ValueError:
                    messagebox.showerror("錯誤", "時間格式錯誤，請使用 HH:MM 格式（如 14:30）")
                    return

            # 🔥 新增：取得備註
            note = self.note_text.get('1.0', tk.END).strip()

            # 新增模式：檢查階段是否已存在
            if self.mode == 'add' and self.case_data:
                if stage_name in self.case_data.progress_stages:
                    if not messagebox.askyesno("確認", f"階段「{stage_name}」已存在，是否要更新日期和備註？"):
                        return

            self.result = {
                'stage_name': stage_name,
                'stage_date': stage_date,
                'time': time,  # 🔥 新增：加入時間
                'note': note,  # 🔥 新增：加入備註
                'original_stage': self.stage_name
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