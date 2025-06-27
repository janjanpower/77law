import tkinter as tk
from typing import List, Dict, Any, Callable, Optional
from config.settings import AppConfig
from utils.date_reminder import DateReminderManager


class DateReminderWidget:
    """簡約浮動式日期提醒控件 - 由下往上滾動，支援持續選取"""

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
        self.expanded_window = None
        self.selected_case_id = None  # 🔥 新增：記住選中的案件ID

        self._create_widget()
        self._update_display()

    def _create_widget(self):
        """建立控件 - 簡約垂直佈局"""
        # 主容器
        self.main_frame = tk.Frame(self.parent_window, bg=AppConfig.COLORS['window_bg'])
        self.main_frame.pack(side='right', fill='y', padx=(10, 0))

        # 天數控制（上方左側靠齊）
        self._create_days_control()

        # 簡約跑馬燈顯示（下方）
        self._create_minimal_display()

    def _create_days_control(self):
        """建立天數控制 - 極簡設計"""
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
            font=('Arial', 10),
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
            font=('SimHei', 10, 'bold'),
            width=2
        )
        self.days_label.pack(side='left')

        # 右箭頭
        right_arrow = tk.Label(
            days_container,
            text="▶",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Arial', 10),
            cursor='hand2'
        )
        right_arrow.pack(side='left', padx=1)
        right_arrow.bind('<Button-1>', lambda e: self._increase_days())

        # 文字說明
        tk.Label(
            days_container,
            text="天内各案件階段",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('SimHei', 10, 'bold')
        ).pack(side='left', padx=(2, 0))

    def _create_minimal_display(self):
        """建立極簡跑馬燈顯示 - 由下往上滾動"""
        # 跑馬燈容器 - 極簡設計
        self.display_container = tk.Frame(
            self.main_frame,
            bg='#383838',
            relief='flat',
            borderwidth=0,
            height=25,
            width=200
        )
        self.display_container.pack(fill='x')
        self.display_container.pack_propagate(False)

        # 添加微妙的邊框
        self.display_container.config(
            relief='solid',
            borderwidth=1,
            highlightbackground='#E0E0E0',
            highlightthickness=0
        )

        # 內容顯示區域 - 支援垂直滾動動畫
        self.content_area = tk.Frame(
            self.display_container,
            bg='#F5F5F5',
            height=25
        )
        self.content_area.pack(fill='both', expand=True)
        self.content_area.pack_propagate(False)

        # 當前顯示的標籤 - 🔥 修改：統一字體大小
        self.current_label = tk.Label(
            self.content_area,
            text="即將到期：無資料",
            bg='#F5F5F5',
            fg='#666666',
            font=('SimHei', 10, 'bold') ,  # 🔥 統一字體大小為10
            anchor='w',
            cursor='hand2'
        )
        self.current_label.bind('<Button-1>', self._on_display_click)

        # 下一個標籤（用於由下往上滾動動畫）- 🔥 修改：統一字體大小
        self.next_label = tk.Label(
            self.content_area,
            text="",
            bg='#F5F5F5',
            fg='#666666',
            font=('SimHei', 10, 'bold'),  # 🔥 統一字體大小為10
            anchor='w'
        )

        # 初始位置：當前標籤正常位置，下一個標籤在下方待命
        self.current_label.place(x=5, y=0, relwidth=0.95, relheight=1.0)
        self.next_label.place(x=5, y=25, relwidth=0.95, relheight=1.0)

    def _decrease_days(self):
        """減少天數 - 🔥 修改：不中斷動畫輪播"""
        if self.days_ahead > 1:
            self.days_ahead -= 1
            self.days_label.config(text=str(self.days_ahead))
            # 🔥 修改：只更新資料，不重置當前索引，不影響動畫
            self._update_data_only_no_interrupt()

    def _increase_days(self):
        """增加天數 - 🔥 修改：不中斷動畫輪播"""
        if self.days_ahead < 7:
            self.days_ahead += 1
            self.days_label.config(text=str(self.days_ahead))
            # 🔥 修改：只更新資料，不重置當前索引，不影響動畫
            self._update_data_only_no_interrupt()

    def _update_data_only_no_interrupt(self):
        """🔥 修正：只更新資料，防止案件跳躍"""
        if not self.case_data:
            self.upcoming_stages = []
            return

        # 記住當前正在顯示的案件
        current_case_id = None
        if self.upcoming_stages and 0 <= self.current_index < len(self.upcoming_stages):
            current_case_id = self.upcoming_stages[self.current_index]['case'].case_id

        # 更新資料
        old_stages_count = len(self.upcoming_stages)
        self.upcoming_stages = DateReminderManager.get_upcoming_stages(
            self.case_data, self.days_ahead
        )
        new_stages_count = len(self.upcoming_stages)

        # 🔥 修正：智慧調整索引，避免跳躍
        if current_case_id and self.upcoming_stages:
            # 優先：在新列表中找到相同案件
            found_same_case = False
            for i, stage_info in enumerate(self.upcoming_stages):
                if stage_info['case'].case_id == current_case_id:
                    self.current_index = i
                    found_same_case = True
                    break

            # 如果找不到相同案件，智慧調整索引
            if not found_same_case:
                if new_stages_count == 0:
                    self.current_index = 0
                elif self.current_index >= new_stages_count:
                    # 🔥 關鍵修正：如果當前索引超出範圍，取模運算而不是直接調整
                    self.current_index = self.current_index % new_stages_count
                # 如果索引在有效範圍內，保持不變
        elif new_stages_count == 0:
            self.current_index = 0
        elif self.current_index >= new_stages_count:
            # 🔥 關鍵修正：使用取模運算避免跳躍
            self.current_index = self.current_index % new_stages_count

        # 只更新當前顯示，不影響滾動狀態
        if self.is_expanded and self.expanded_window:
            self._update_expanded_content()
        else:
            self._update_current_display()

    def _on_display_click(self, event=None):
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
        self.expanded_window.geometry("380x280")
        self.expanded_window.configure(bg='#F8F8F8')
        self.expanded_window.overrideredirect(True)
        self.expanded_window.attributes('-topmost', True)

        # 計算位置（在跑馬燈下方）
        self._position_expanded_window()

        # 創建展開內容
        self._create_expanded_content()

        # 設定點擊外部關閉
        self.expanded_window.bind('<FocusOut>', self._on_focus_out)
        self.expanded_window.focus_set()

        self.is_expanded = True
        self._stop_scroll()

    def _position_expanded_window(self):
        """定位展開視窗"""
        try:
            self.display_container.update_idletasks()
            x = self.display_container.winfo_rootx()
            y = self.display_container.winfo_rooty() + self.display_container.winfo_height() + 5

            # 確保視窗不超出螢幕範圍
            screen_width = self.expanded_window.winfo_screenwidth()
            screen_height = self.expanded_window.winfo_screenheight()

            if x + 380 > screen_width:
                x = screen_width - 380
            if y + 280 > screen_height:
                y = y - 280 - self.display_container.winfo_height() - 10

            self.expanded_window.geometry(f"200x250+{x}+{y}")
        except:
            self.expanded_window.geometry("380x280+100+100")

    def _create_expanded_content(self):
        """創建展開視窗內容 - 極簡設計"""
        # 標題列
        header_frame = tk.Frame(self.expanded_window, bg='#F8F8F8')
        header_frame.pack(fill='x', pady=5, padx=5)

        header_label = tk.Label(
            header_frame,
            text=f"未來 {self.days_ahead} 天内到期",
            bg='#F8F8F8',
            fg='#333333',
            font=('SimHei', 10, 'bold')
        )
        header_label.pack(side='left')

        # 關閉按鈕
        close_btn = tk.Label(
            header_frame,
            text="✕",
            bg='#F8F8F8',
            fg='#666666',
            font=('Arial', 11, 'bold'),
            cursor='hand2'
        )
        close_btn.pack(side='right')
        close_btn.bind('<Button-1>', lambda e: self._close_expanded_window())

        # 列表容器
        list_container = tk.Frame(
            self.expanded_window,
            bg='white',
            relief='solid',
            borderwidth=1
        )
        list_container.pack(fill='both', expand=True, pady=(0, 5), padx=5)

        # 滾動區域
        self.expanded_scroll_frame = tk.Frame(list_container, bg='white')
        self.expanded_scroll_frame.pack(fill='both', expand=True, padx=3, pady=3)

        # 綁定列表容器的點擊事件
        list_container.bind('<Button-1>', lambda e: self._close_expanded_window())

        # 填入案件列表
        self._update_expanded_content()

    def _update_expanded_content(self):
        """更新展開視窗內容 - 簡潔列表"""
        # 清空現有顯示
        for widget in self.expanded_scroll_frame.winfo_children():
            widget.destroy()

        if not self.upcoming_stages:
            no_data_label = tk.Label(
                self.expanded_scroll_frame,
                text=f"未來 {self.days_ahead} 天内沒有到期項目",
                bg='white',
                fg='#999999',
                font=('SimHei', 10, 'bold'),
                justify='center'
            )
            no_data_label.pack(pady=40)
            no_data_label.bind('<Button-1>', lambda e: self._close_expanded_window())
            return

        # 顯示每個項目 - 簡潔設計
        for i, stage_info in enumerate(self.upcoming_stages):
            self._create_simple_item(stage_info, i)

    def _create_simple_item(self, stage_info, index):
        """建立簡潔列表項目"""
        # 項目容器
        item_frame = tk.Frame(
            self.expanded_scroll_frame,
            bg='white',
            relief='flat',
            borderwidth=0,
            cursor='hand2'
        )
        item_frame.pack(fill='x', pady=1, padx=2)

        # 🔥 修改：檢查是否為選中的案件，顯示不同顏色
        is_selected = (stage_info['case'].case_id == self.selected_case_id)
        item_bg_color = '#E3F2FD' if is_selected else 'white'

        item_frame.config(bg=item_bg_color)

        # 狀態指示點
        status_dot = tk.Label(
            item_frame,
            text="●",
            bg=item_bg_color,
            fg='#383838',
            font=('Arial', 10),
            width=2
        )
        status_dot.pack(side='left')

        # 主要內容文字 - 極簡格式
        content_text = self._format_simple_display(stage_info)
        content_label = tk.Label(
            item_frame,
            text=content_text,
            bg=item_bg_color,
            fg='#333333',
            font=('SimHei', 10, 'bold'),
            anchor='w'
        )
        content_label.pack(side='left', fill='x', expand=True, padx=2, pady=3)

        # 綁定點擊事件
        def on_click(event, case=stage_info['case'], idx=index):
            self._on_item_click(case, idx)

        # 為所有組件綁定點擊事件
        for widget in [item_frame, status_dot, content_label]:
            widget.bind('<Button-1>', on_click)

        # 🔥 修改：已選中的項目不需要懸停效果，未選中的才需要
        if not is_selected:
            def on_enter(event):
                item_frame.config(bg='#F0F0F0')
                status_dot.config(bg='#F0F0F0')
                content_label.config(bg='#F0F0F0')

            def on_leave(event):
                item_frame.config(bg='white')
                status_dot.config(bg='white')
                content_label.config(bg='white')

            for widget in [item_frame, status_dot, content_label]:
                widget.bind('<Enter>', on_enter)
                widget.bind('<Leave>', on_leave)

    def _format_simple_display(self, stage_info: Dict[str, Any]) -> str:
        """格式化簡潔顯示文字"""
        date_str = stage_info['stage_date'].strftime('%m/%d')

        # 極簡格式：日期 當事人 階段
        if stage_info['stage_time']:
            display_text = f"{date_str} {stage_info['stage_time']} {stage_info['client'][:6]} {stage_info['stage_name']}"
        else:
            display_text = f"{date_str} {stage_info['client'][:6]} {stage_info['stage_name']}"

        return display_text

    def _on_item_click(self, case, index):
        """項目點擊事件 - 🔥 修改：記住選中的案件ID"""
        self.selected_case_index = index
        self.current_index = index
        self.selected_case_id = case.case_id  # 🔥 記住選中的案件ID

        # 🔥 先更新展開視窗的顯示（如果還開著）
        if self.expanded_window:
            self._update_expanded_content()

        # 延遲關閉展開視窗，讓用戶看到選中效果
        self.parent_window.after(200, self._close_expanded_window)

        # 🔥 修改：使用更穩定的案件選擇方式
        if self.on_case_select:
            # 延遲執行案件選擇，確保視窗狀態穩定
            self.parent_window.after(300, lambda: self._execute_case_selection(case))

    def _execute_case_selection(self, case):
        """🔥 新增：執行案件選擇邏輯"""
        try:
            print(f"日期提醒控件：選擇案件 {case.case_id} - {case.client}")
            self.on_case_select(case)
        except Exception as e:
            print(f"案件選擇回調執行失敗: {e}")

    def _on_focus_out(self, event):
        """失去焦點時關閉展開視窗"""
        if self.expanded_window:
            self.expanded_window.after(100, self._check_and_close)

    def _check_and_close(self):
        """檢查並關閉視窗"""
        try:
            if self.expanded_window and self.expanded_window.winfo_exists():
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
        # 🔥 修改：不重置選中狀態，保持選中的案件
        # if not hasattr(self, '_item_clicked'):
        #     self.selected_case_index = None

        self._start_scroll()

    def update_case_data(self, case_data: List):
        """更新案件資料 - 🔥 修改：保持選中狀態"""
        self.case_data = case_data
        # 🔥 檢查選中的案件是否還存在
        if self.selected_case_id:
            case_still_exists = any(case.case_id == self.selected_case_id for case in case_data)
            if not case_still_exists:
                self.selected_case_id = None
                self.selected_case_index = None

        self._update_display()

    def _update_data_only(self):
        """🔥 新增：只更新資料，不影響當前顯示的案件索引"""
        if not self.case_data:
            self.upcoming_stages = []
        else:
            old_upcoming_stages = self.upcoming_stages.copy()
            self.upcoming_stages = DateReminderManager.get_upcoming_stages(
                self.case_data, self.days_ahead
            )

            # 🔥 智慧保持當前顯示的案件
            if old_upcoming_stages and self.upcoming_stages:
                # 嘗試找到當前顯示案件在新列表中的位置
                if self.current_index < len(old_upcoming_stages):
                    current_case_id = old_upcoming_stages[self.current_index]['case'].case_id

                    # 在新列表中找到相同案件
                    for i, stage_info in enumerate(self.upcoming_stages):
                        if stage_info['case'].case_id == current_case_id:
                            self.current_index = i
                            break
                    else:
                        # 如果當前案件不在新列表中，保持索引但調整範圍
                        self.current_index = min(self.current_index, len(self.upcoming_stages) - 1)
                else:
                    self.current_index = 0
            elif not self.upcoming_stages:
                self.current_index = 0
            else:
                # 確保索引在有效範圍內
                self.current_index = min(self.current_index, len(self.upcoming_stages) - 1)

        # 🔥 更新顯示但不重置滾動狀態
        if self.is_expanded and self.expanded_window:
            self._update_expanded_content()
        else:
            self._update_current_display()
            # 🔥 不重新開始滾動，保持當前滾動狀態

    def set_selected_case(self, case_id: str):
        """🔥 新增：從外部設定選中的案件"""
        self.selected_case_id = case_id
        # 🔥 更新顯示以反映選中狀態
        if self.expanded_window:
            self._update_expanded_content()

    def _update_display(self):
        """更新顯示 - 🔥 修改：智慧保持選中狀態"""
        if not self.case_data:
            self.upcoming_stages = []
        else:
            self.upcoming_stages = DateReminderManager.get_upcoming_stages(
                self.case_data, self.days_ahead
            )

        # 🔥 修改：智慧重置索引邏輯
        if self.selected_case_id and self.upcoming_stages:
            # 嘗試找到選中案件在新列表中的位置
            for i, stage_info in enumerate(self.upcoming_stages):
                if stage_info['case'].case_id == self.selected_case_id:
                    self.current_index = i
                    self.selected_case_index = i
                    break
            else:
                # 如果選中的案件不在當前顯示列表中，重置選擇
                self.current_index = 0
                self.selected_case_index = None
        elif self.selected_case_index is None:
            self.current_index = 0
        else:
            self.current_index = min(self.selected_case_index, len(self.upcoming_stages) - 1)

        if self.is_expanded and self.expanded_window:
            self._update_expanded_content()
        else:
            self._update_current_display()
            self._start_scroll()

    def _update_current_display(self):
        """更新當前顯示 - 極簡風格"""
        if not self.upcoming_stages:
            self.current_label.config(
                text="即將到期：無資料",
                fg='#AAAAAA',
                bg='#F5F5F5'
            )
            self.display_container.config(bg='#F5F5F5')
            self.content_area.config(bg='#F5F5F5')
            return

        # 取得當前要顯示的項目
        stage_info = self.upcoming_stages[self.current_index]

        # 格式化顯示文字
        display_text = self._format_simple_display(stage_info)

        # 設定顏色 - 極簡風格
        bg_color, fg_color = self._get_minimal_colors(stage_info)

        self.current_label.config(
            text=display_text,
            fg=fg_color,
            bg=bg_color
        )
        self.display_container.config(bg=bg_color)
        self.content_area.config(bg=bg_color)

    def _get_minimal_colors(self, stage_info: Dict[str, Any]) -> tuple:
        """取得極簡風格的顏色"""
        if stage_info['is_overdue']:
            return ('white', '#383838')  # 極淺紅背景，深紅文字
        elif stage_info['is_today']:
            return ('white', '#383838')  # 極淺橙背景，深橙文字
        elif stage_info['days_until'] <= 1:
            return ('white', '#383838')  # 極淺黃背景，深黃文字
        else:
            return ('white', '#383838')    # 預設淺灰背景，深灰文字

    def _start_scroll(self):
        """開始滾動效果 - 由下往上 🔥 修改：收合狀態下總是滾動"""
        self._stop_scroll()

        if not self.upcoming_stages or len(self.upcoming_stages) <= 1:
            return

        # 🔥 修改：收合狀態下總是滾動，不管是否有選中案件
        if not self.is_expanded:
            scroll_interval = 5000  # 5秒切換一次
            self.scroll_job = self.current_label.after(scroll_interval, self._on_scroll_timer)

    def _on_scroll_timer(self):
        """滾動計時器回調 - 🔥 修改：移除選中狀態檢查"""
        # 🔥 移除選中狀態檢查，收合狀態下總是滾動
        if not self.is_expanded and self.upcoming_stages and len(self.upcoming_stages) > 1:
            # 更新索引
            self.current_index = (self.current_index + 1) % len(self.upcoming_stages)

            # 執行由下往上滾動動畫
            self._animate_scroll_up()

            # 設定下一次滾動
            scroll_interval = 5000
            self.scroll_job = self.current_label.after(scroll_interval, self._on_scroll_timer)

    def clear_selection(self):
        """🔥 修改：清除選中狀態但不停止滾動"""
        self.selected_case_id = None
        self.selected_case_index = None
        # 🔥 不重置 current_index，保持當前顯示的案件

        # 🔥 移除重新開始滾動的邏輯，因為滾動應該一直進行
        # self._start_scroll()

        # 更新顯示
        if self.expanded_window:
            self._update_expanded_content()

    def _animate_scroll_up(self):
        """執行由下往上的滾動動畫"""
        if not self.upcoming_stages or len(self.upcoming_stages) <= 1:
            return

        # 準備下一個項目
        next_index = (self.current_index + 1) % len(self.upcoming_stages)
        next_stage_info = self.upcoming_stages[next_index]
        next_text = self._format_simple_display(next_stage_info)
        next_bg_color, next_fg_color = self._get_minimal_colors(next_stage_info)

        # 設定下一個標籤
        self.next_label.config(
            text=next_text,
            fg=next_fg_color,
            bg=next_bg_color
        )

        # 開始流暢的由下往上動畫 - 15步，每步約1.7像素
        self._smooth_scroll_up_animation(0, 15, next_bg_color)

    def _smooth_scroll_up_animation(self, step, total_steps, next_bg_color):
        """流暢的由下往上滾動動畫"""
        if step <= total_steps:
            # 計算當前位置（由下往上移動）
            current_y = -(step * 1.7)  # 當前標籤向上移動
            next_y = 25 - (step * 1.7)   # 下一個標籤從下方向上進入

            # 更新位置
            self.current_label.place(x=5, y=current_y, relwidth=0.95, relheight=1.0)
            self.next_label.place(x=5, y=next_y, relwidth=0.95, relheight=1.0)

            # 繼續動畫
            self.current_label.after(20, lambda: self._smooth_scroll_up_animation(step + 1, total_steps, next_bg_color))
        else:
            # 動畫完成，交換標籤
            self._finish_scroll_animation(next_bg_color)

    def _finish_scroll_animation(self, bg_color):
        """完成滾動動畫"""
        # 交換標籤內容
        current_text = self.next_label.cget('text')
        current_fg = self.next_label.cget('fg')
        current_bg = self.next_label.cget('bg')

        self.current_label.config(
            text=current_text,
            fg=current_fg,
            bg=current_bg
        )

        # 重置位置
        self.current_label.place(x=5, y=0, relwidth=0.95, relheight=1.0)
        self.next_label.place(x=5, y=25, relwidth=0.95, relheight=1.0)

        # 更新容器背景
        self.display_container.config(bg=bg_color)
        self.content_area.config(bg=bg_color)

        # 清空下一個標籤
        self.next_label.config(text="", bg='#F5F5F5')

    def _stop_scroll(self):
        """停止滾動效果"""
        if self.scroll_job:
            self.current_label.after_cancel(self.scroll_job)
            self.scroll_job = None

    def destroy(self):
        """銷毀控件時清理資源"""
        self._stop_scroll()
        if self.expanded_window:
            self.expanded_window.destroy()
        if hasattr(self, 'main_frame'):
            self.main_frame.destroy()