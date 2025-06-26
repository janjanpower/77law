import tkinter as tk
from typing import List, Dict, Any, Callable, Optional
from config.settings import AppConfig
from utils.date_reminder import DateReminderManager


class DateReminderWidget:
    """獨立浮動式日期提醒控件"""

    def __init__(self, parent, case_data: List = None, on_case_select: Optional[Callable] = None):
        """
        初始化日期提醒控件

        Args:
            parent: 父視窗（用於相對定位）
            case_data: 案件資料列表
            on_case_select: 案件選擇回調函數
        """
        self.parent_window = parent
        self.case_data = case_data or []
        self.on_case_select = on_case_select
        self.days_ahead = 3  # 預設3天
        self.upcoming_stages = []
        self.current_index = 0
        self.scroll_job = None
        self.is_expanded = False
        self.selected_case_index = None
        self.expanded_window = None  # 展開時的獨立視窗

        self._create_widget()
        self._update_display()

    def _create_widget(self):
        """建立控件 - 垂直佈局，天數控制在上方"""
        # 主容器
        self.main_frame = tk.Frame(self.parent_window, bg=AppConfig.COLORS['window_bg'])
        self.main_frame.pack(side='right', fill='y', padx=(10, 0))

        # 天數控制（上方左側靠齊）
        self._create_days_control()

        # 跑馬燈顯示（下方）
        self._create_single_line_display()

    def _create_days_control(self):
        """建立天數控制 - 上方左側靠齊"""
        control_frame = tk.Frame(self.main_frame, bg=AppConfig.COLORS['window_bg'])
        control_frame.pack(fill='x', pady=(0, 5))

        # 天數控制容器（靠左對齊）
        days_container = tk.Frame(control_frame, bg=AppConfig.COLORS['window_bg'])
        days_container.pack(side='left')

        # 左箭頭
        left_arrow = tk.Label(
            days_container,
            text="◀",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Arial', 8),
            cursor='hand2'
        )
        left_arrow.pack(side='left', padx=1)
        left_arrow.bind('<Button-1>', lambda e: self._decrease_days())

        # 天數顯示
        self.days_label = tk.Label(
            days_container,
            text=str(self.days_ahead),
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Microsoft JhengHei', 9, 'bold'),
            width=2
        )
        self.days_label.pack(side='left')

        # 右箭頭
        right_arrow = tk.Label(
            days_container,
            text="▶",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Arial', 8),
            cursor='hand2'
        )
        right_arrow.pack(side='left', padx=1)
        right_arrow.bind('<Button-1>', lambda e: self._increase_days())

        # 文字說明
        tk.Label(
            days_container,
            text="天提醒",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Microsoft JhengHei', 7)
        ).pack(side='left', padx=(5, 0))

    def _create_single_line_display(self):
        """建立簡約跑馬燈顯示"""
        # 跑馬燈容器 - 簡約設計
        self.single_line_container = tk.Frame(
            self.main_frame,
            bg='white',
            relief='flat',
            borderwidth=0,
            height=30,
            width=280
        )
        self.single_line_container.pack(fill='x')
        self.single_line_container.pack_propagate(False)

        # 添加微妙的邊框
        self.single_line_container.config(
            relief='solid',
            borderwidth=1,
            highlightbackground='#E0E0E0',
            highlightthickness=1
        )

        # 單行標籤容器 - 用於流暢動畫
        self.label_container = tk.Frame(
            self.single_line_container,
            bg='white',
            height=30
        )
        self.label_container.pack(fill='both', expand=True)
        self.label_container.pack_propagate(False)

        # 當前顯示的標籤
        self.single_line_label = tk.Label(
            self.label_container,
            text="即將到期：無資料",
            bg='white',
            fg='#666666',
            font=('Microsoft JhengHei', 9),
            anchor='w',
            cursor='hand2'
        )
        self.single_line_label.bind('<Button-1>', self._on_single_line_click)

        # 下一個標籤（用於動畫效果）
        self.next_label = tk.Label(
            self.label_container,
            text="",
            bg='white',
            fg='#666666',
            font=('Microsoft JhengHei', 9),
            anchor='w'
        )

        # 初始位置
        self.single_line_label.place(x=8, y=0, relwidth=0.95, relheight=1.0)
        self.next_label.place(x=8, y=30, relwidth=0.95, relheight=1.0)  # 在下方待命

    def _decrease_days(self):
        """減少天數"""
        if self.days_ahead > 1:
            self.days_ahead -= 1
            self.days_label.config(text=str(self.days_ahead))
            self._update_display()

    def _increase_days(self):
        """增加天數"""
        if self.days_ahead < 7:
            self.days_ahead += 1
            self.days_label.config(text=str(self.days_ahead))
            self._update_display()

    def _on_single_line_click(self, event=None):
        """單行點擊事件 - 創建獨立展開視窗"""
        if not self.upcoming_stages:
            return

        self._create_expanded_window()

    def _create_expanded_window(self):
        """創建獨立的展開視窗"""
        if self.expanded_window:
            self.expanded_window.destroy()

        # 創建獨立的 Toplevel 視窗
        self.expanded_window = tk.Toplevel(self.parent_window)
        self.expanded_window.title("即將到期案件")
        self.expanded_window.geometry("400x300")
        self.expanded_window.configure(bg='#E0E0E0')
        self.expanded_window.overrideredirect(True)  # 移除標題欄
        self.expanded_window.attributes('-topmost', True)  # 置頂顯示

        # 計算位置（在跑馬燈下方）
        self._position_expanded_window()

        # 設定視窗關閉事件
        self.expanded_window.protocol("WM_DELETE_WINDOW", self._close_expanded_window)

        # 創建展開內容
        self._create_expanded_content()

        # 設定點擊外部關閉（失去焦點時關閉）
        self.expanded_window.bind('<FocusOut>', self._on_focus_out)
        self.expanded_window.focus_set()

        self.is_expanded = True
        self._stop_scroll()  # 停止滾動

    def _position_expanded_window(self):
        """定位展開視窗"""
        try:
            # 取得跑馬燈在螢幕上的位置
            self.single_line_container.update_idletasks()
            x = self.single_line_container.winfo_rootx()
            y = self.single_line_container.winfo_rooty() + self.single_line_container.winfo_height() + 5

            # 確保視窗不超出螢幕範圍
            screen_width = self.expanded_window.winfo_screenwidth()
            screen_height = self.expanded_window.winfo_screenheight()

            if x + 400 > screen_width:
                x = screen_width - 400
            if y + 300 > screen_height:
                y = y - 300 - self.single_line_container.winfo_height() - 10

            self.expanded_window.geometry(f"400x300+{x}+{y}")
        except:
            # 如果定位失敗，使用預設位置
            self.expanded_window.geometry("400x300+100+100")

    def _create_expanded_content(self):
        """創建展開視窗內容"""
        # 標題列
        header_frame = tk.Frame(self.expanded_window, bg='#E0E0E0')
        header_frame.pack(fill='x', pady=5, padx=5)

        header_label = tk.Label(
            header_frame,
            text=f"未來 {self.days_ahead} 天內即將到期的案件",
            bg='#E0E0E0',
            fg='#333333',
            font=AppConfig.FONTS['button']
        )
        header_label.pack(side='left')

        # 關閉按鈕
        close_btn = tk.Label(
            header_frame,
            text="✕",
            bg='#E0E0E0',
            fg='#666666',
            font=('Arial', 12, 'bold'),
            cursor='hand2'
        )
        close_btn.pack(side='right')
        close_btn.bind('<Button-1>', lambda e: self._close_expanded_window())

        # 列表容器
        list_container = tk.Frame(
            self.expanded_window,
            bg='white',
            relief='sunken',
            borderwidth=2
        )
        list_container.pack(fill='both', expand=True, pady=(0, 5), padx=5)

        # 滾動區域
        self.expanded_scroll_frame = tk.Frame(list_container, bg='white')
        self.expanded_scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # 綁定列表容器的點擊事件
        list_container.bind('<Button-1>', lambda e: self._close_expanded_window())

        # 填入案件列表
        self._update_expanded_content()

    def _update_expanded_content(self):
        """更新展開視窗內容"""
        # 清空現有顯示
        for widget in self.expanded_scroll_frame.winfo_children():
            widget.destroy()

        if not self.upcoming_stages:
            # 沒有資料時顯示提示
            no_data_label = tk.Label(
                self.expanded_scroll_frame,
                text=f"未來 {self.days_ahead} 天內沒有即將到期的階段",
                bg='white',
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['text'],
                justify='center'
            )
            no_data_label.pack(pady=50)
            no_data_label.bind('<Button-1>', lambda e: self._close_expanded_window())
            return

        # 顯示每個項目
        for i, stage_info in enumerate(self.upcoming_stages):
            self._create_expanded_item(stage_info, i)

    def _create_expanded_item(self, stage_info, index):
        """建立展開列表項目"""
        # 項目容器
        item_frame = tk.Frame(
            self.expanded_scroll_frame,
            bg='white',
            relief='solid',
            borderwidth=1,
            cursor='hand2'
        )
        item_frame.pack(fill='x', pady=1)

        # 狀態指示器
        status_color = DateReminderManager.get_stage_color(stage_info)
        status_label = tk.Label(
            item_frame,
            text="●",
            bg='white',
            fg=status_color,
            font=('Arial', 8),
            width=2
        )
        status_label.pack(side='left')

        # 主要內容文字
        content_text = DateReminderManager.format_stage_display(stage_info)
        content_label = tk.Label(
            item_frame,
            text=content_text,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text'],
            anchor='w'
        )
        content_label.pack(side='left', fill='x', expand=True, padx=3, pady=2)

        # 綁定點擊事件
        def on_click(event, case=stage_info['case'], idx=index):
            self._on_item_click(case, idx)

        # 為所有組件綁定點擊事件
        for widget in [item_frame, status_label, content_label]:
            widget.bind('<Button-1>', on_click)

        # 滑鼠懸停效果
        def on_enter(event):
            item_frame.config(bg='#F0F0F0')
            content_label.config(bg='#F0F0F0')

        def on_leave(event):
            item_frame.config(bg='white')
            content_label.config(bg='white')

        for widget in [item_frame, status_label, content_label]:
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)

    def _on_item_click(self, case, index):
        """項目點擊事件"""
        # 記住選擇的案件索引
        self.selected_case_index = index
        self.current_index = index

        # 關閉展開視窗
        self._close_expanded_window()

        # 選擇案件
        if self.on_case_select:
            self.on_case_select(case)

    def _on_focus_out(self, event):
        """失去焦點時關閉展開視窗"""
        # 延遲關閉，避免點擊項目時立即關閉
        if self.expanded_window:
            self.expanded_window.after(100, self._check_and_close)

    def _check_and_close(self):
        """檢查並關閉視窗"""
        try:
            if self.expanded_window and self.expanded_window.winfo_exists():
                # 檢查滑鼠是否在視窗內
                x, y = self.expanded_window.winfo_pointerxy()
                wx, wy = self.expanded_window.winfo_rootx(), self.expanded_window.winfo_rooty()
                ww, wh = self.expanded_window.winfo_width(), self.expanded_window.winfo_height()

                if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
                    self._close_expanded_window()
        except:
            pass

    def _close_expanded_window(self):
        """關閉展開視窗"""
        if self.expanded_window:
            self.expanded_window.destroy()
            self.expanded_window = None

        self.is_expanded = False
        # 重置選擇的案件索引（如果不是通過點擊項目關閉的）
        if not hasattr(self, '_item_clicked'):
            self.selected_case_index = None

        self._start_scroll()  # 重新開始滾動

    def update_case_data(self, case_data: List):
        """更新案件資料"""
        self.case_data = case_data
        self._update_display()

    def _update_display(self):
        """更新顯示"""
        if not self.case_data:
            self.upcoming_stages = []
        else:
            self.upcoming_stages = DateReminderManager.get_upcoming_stages(
                self.case_data, self.days_ahead
            )

        # 重置索引（除非有選擇的案件）
        if self.selected_case_index is None:
            self.current_index = 0
        else:
            # 保持在選擇的案件上
            self.current_index = min(self.selected_case_index, len(self.upcoming_stages) - 1)

        if self.is_expanded and self.expanded_window:
            self._update_expanded_content()
        else:
            self._update_single_line()
            self._start_scroll()

    def _update_single_line(self):
        """更新單行顯示 - 簡約風格"""
        if not self.upcoming_stages:
            self.single_line_label.config(
                text="即將到期：無資料",
                fg='#AAAAAA',
                bg='white'
            )
            self.single_line_container.config(bg='white')
            return

        # 取得當前要顯示的項目
        stage_info = self.upcoming_stages[self.current_index]

        # 格式化顯示文字
        display_text = self._format_stage_text(stage_info)

        # 設定顏色 - 簡約風格
        bg_color, fg_color = self._get_simple_stage_colors(stage_info)

        self.single_line_label.config(
            text=display_text,
            fg=fg_color,
            bg=bg_color
        )
        self.single_line_container.config(bg=bg_color)
        self.label_container.config(bg=bg_color)

    def _get_simple_stage_colors(self, stage_info: Dict[str, Any]) -> tuple:
        """取得簡約風格的階段顏色"""
        if stage_info['is_overdue']:
            return '#FFF5F5', '#D32F2F'  # 極淺紅背景，深紅文字
        elif stage_info['is_today']:
            return '#FFFAF0', '#F57C00'  # 極淺橙背景，深橙文字
        elif stage_info['days_until'] <= 1:
            return '#FFFEF7', '#F9A825'  # 極淺黃背景，深黃文字
        elif stage_info['days_until'] <= 3:
            return '#F8FFF8', '#388E3C'  # 極淺綠背景，深綠文字
        else:
            return 'white', '#1976D2'    # 白背景，藍文字

    def _animate_scroll_up(self):
        """執行流暢的向上滾動動畫"""
        if not self.upcoming_stages or len(self.upcoming_stages) <= 1:
            return

        # 準備下一個項目
        next_index = (self.current_index + 1) % len(self.upcoming_stages)
        next_stage_info = self.upcoming_stages[next_index]
        next_text = self._format_stage_text(next_stage_info)
        next_bg_color, next_fg_color = self._get_simple_stage_colors(next_stage_info)

        # 設定下一個標籤
        self.next_label.config(
            text=next_text,
            fg=next_fg_color,
            bg=next_bg_color
        )

        # 開始流暢動畫 - 20步，每步2像素
        self._smooth_scroll_animation(0, 20, next_bg_color)

    def _smooth_scroll_animation(self, step, total_steps, next_bg_color):
        """流暢滾動動畫"""
        if step <= total_steps:
            # 計算當前位置
            current_y = -(step * 1.5)  # 當前標籤向上移動
            next_y = 30 - (step * 1.5)   # 下一個標籤從下方進入

            # 更新位置
            self.single_line_label.place(x=8, y=current_y, relwidth=0.95, relheight=1.0)
            self.next_label.place(x=8, y=next_y, relwidth=0.95, relheight=1.0)

            # 繼續動畫
            self.single_line_label.after(20, lambda: self._smooth_scroll_animation(step + 1, total_steps, next_bg_color))
        else:
            # 動畫完成，交換標籤
            self._finish_scroll_animation(next_bg_color)

    def _finish_scroll_animation(self, bg_color):
        """完成滾動動畫"""
        # 交換標籤內容
        current_text = self.next_label.cget('text')
        current_fg = self.next_label.cget('fg')
        current_bg = self.next_label.cget('bg')

        self.single_line_label.config(
            text=current_text,
            fg=current_fg,
            bg=current_bg
        )

        # 重置位置
        self.single_line_label.place(x=8, y=0, relwidth=0.95, relheight=1.0)
        self.next_label.place(x=8, y=30, relwidth=0.95, relheight=1.0)

        # 更新容器背景
        self.single_line_container.config(bg=bg_color)
        self.label_container.config(bg=bg_color)

        # 清空下一個標籤
        self.next_label.config(text="", bg='white')

    def _stop_scroll(self):
        """停止滾動效果"""
        if self.scroll_job:
            self.single_line_label.after_cancel(self.scroll_job)
            self.scroll_job = None

    def destroy(self):
        """銷毀控件時清理資源"""
        self._stop_scroll()
        if self.expanded_window:
            self.expanded_window.destroy()
        if hasattr(self, 'main_frame'):
            self.main_frame.destroy()

    def _start_scroll(self):
        """開始滾動效果"""
        self._stop_scroll()  # 先停止現有的滾動

        if not self.upcoming_stages or len(self.upcoming_stages) <= 1:
            return

        if not self.is_expanded:  # 只有在非展開狀態下才滾動
            # 設定滾動間隔（毫秒）
            scroll_interval = 3000  # 3秒切換一次
            self.scroll_job = self.single_line_label.after(scroll_interval, self._on_scroll_timer)

    def _on_scroll_timer(self):
        """滾動計時器回調"""
        if not self.is_expanded and self.upcoming_stages and len(self.upcoming_stages) > 1:
            # 更新索引
            self.current_index = (self.current_index + 1) % len(self.upcoming_stages)

            # 執行滾動動畫
            self._animate_scroll_up()

            # 設定下一次滾動
            scroll_interval = 3000  # 3秒間隔
            self.scroll_job = self.single_line_label.after(scroll_interval, self._on_scroll_timer)