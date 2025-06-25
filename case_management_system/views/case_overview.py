import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional
from config.settings import AppConfig
from models.case_model import CaseData

class CaseOverviewWindow:
    """案件總覽視窗"""

    def __init__(self, parent=None, case_controller=None):
        self.parent = parent
        self.case_controller = case_controller
        # 🔥 修正：使用 OVERVIEW_FIELDS
        self.visible_fields = AppConfig.OVERVIEW_FIELDS.copy()
        self.case_data: List[CaseData] = []
        self.drag_data = {"x": 0, "y": 0}

        # 建立視窗
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self._setup_window()
        self._setup_styles()
        self._create_layout()

        # 載入案件資料
        if self.case_controller:
            self._load_cases()

    def _setup_window(self):
        """設定視窗基本屬性"""
        # 使用統一的標題
        self.window.title(AppConfig.WINDOW_TITLES['overview'])
        self.window.geometry("1200x800")  # 增大總覽視窗尺寸
        self.window.configure(bg=AppConfig.COLORS['window_bg'])

        # 移除系統標題欄
        self.window.overrideredirect(True)

        # 設定最小尺寸
        self.window.minsize(1000, 700)

        # 置中顯示
        self._center_window()

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        width = 1200
        height = 800
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_styles(self):
        """設定 ttk 樣式"""
        self.style = ttk.Style()

        # 按鈕樣式
        self.style.configure(
            'Custom.TButton',
            background=AppConfig.COLORS['button_bg'],
            foreground=AppConfig.COLORS['button_fg'],
            borderwidth=1,
            focuscolor='none'
        )

        self.style.map(
            'Custom.TButton',
            background=[('active', AppConfig.COLORS['button_hover'])]
        )

        # 功能按鈕樣式
        self.style.configure(
            'Function.TButton',
            background=AppConfig.COLORS['button_bg'],
            foreground=AppConfig.COLORS['button_fg'],
            width=15
        )

    def _create_layout(self):
        """建立總覽視窗佈局"""
        # 主容器
        self.main_frame = tk.Frame(
            self.window,
            bg=AppConfig.COLORS['window_bg']
        )
        self.main_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # 自定義標題列
        self.title_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        self.title_frame.pack(fill='x', pady=(0, 5))
        self.title_frame.pack_propagate(False)

        # 標題標籤 - 使用統一字體和標題
        self.title_label = tk.Label(
            self.title_frame,
            text=AppConfig.WINDOW_TITLES['overview'],
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']  # 使用統一字體設定
        )
        self.title_label.pack(side='left', padx=10)

        # 關閉按鈕
        self.close_btn = tk.Button(
            self.title_frame,
            text="✕",
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=('Arial', 12, 'bold'),
            bd=0,
            width=3,
            command=self.close
        )
        self.close_btn.pack(side='right', padx=5)

        # 設定拖曳功能
        self._setup_drag()

        # 內容區域
        self.content_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.content_frame.pack(fill='both', expand=True)

        # 建立具體內容
        self._create_overview_layout()
        self._setup_treeview()
        self._create_field_controls()

    def create_button(self, parent, text, command, style_type='Custom'):
        """建立標準化按鈕"""
        if style_type == 'Function':
            return tk.Button(
                parent,
                text=text,
                command=command,
                bg=AppConfig.COLORS['button_bg'],
                fg=AppConfig.COLORS['button_fg'],
                font=AppConfig.FONTS['button'],  # 使用統一字體
                width=15,
                height=2
            )
        else:
            return tk.Button(
                parent,
                text=text,
                command=command,
                bg=AppConfig.COLORS['button_bg'],
                fg=AppConfig.COLORS['button_fg'],
                font=AppConfig.FONTS['button'],  # 使用統一字體
                width=10
            )

    def _setup_drag(self):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

        # 綁定標題列拖曳事件
        self.title_frame.bind("<Button-1>", start_drag)
        self.title_frame.bind("<B1-Motion>", on_drag)
        self.title_label.bind("<Button-1>", start_drag)
        self.title_label.bind("<B1-Motion>", on_drag)

    def _create_overview_layout(self):
        """建立總覽視窗佈局"""
        # 工具列區域
        self.toolbar_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg'],
            height=50
        )
        self.toolbar_frame.pack(fill='x', pady=(0, 10))
        self.toolbar_frame.pack_propagate(False)

        # 功能按鈕
        self._create_toolbar_buttons()

        # 樹狀圖區域
        self.tree_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.tree_frame.pack(fill='both', expand=True, pady=(0, 5))

        # 欄位控制區域
        self.field_control_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg'],
            height=100
        )
        self.field_control_frame.pack(fill='x')
        self.field_control_frame.pack_propagate(False)

    def _create_toolbar_buttons(self):
        """建立工具列按鈕"""
        # 新增案件按鈕
        self.add_case_btn = self.create_button(
            self.toolbar_frame,
            '新增案件',
            self._on_add_case,
            'Function'
        )
        self.add_case_btn.pack(side='left', padx=(10, 5))

        # 上傳資料按鈕
        self.upload_btn = self.create_button(
            self.toolbar_frame,
            '匯入Excel',
            self._on_import_excel,
            'Function'
        )
        self.upload_btn.pack(side='left', padx=5)

        # 匯出Excel按鈕
        self.export_btn = self.create_button(
            self.toolbar_frame,
            '匯出Excel',
            self._on_export_excel,
            'Function'
        )
        self.export_btn.pack(side='left', padx=5)

        # 重新整理按鈕
        self.refresh_btn = self.create_button(
            self.toolbar_frame,
            '重新整理',
            self._on_refresh,
            'Custom'
        )
        self.refresh_btn.pack(side='right', padx=(5, 10))

    def _setup_treeview(self):
        """設定樹狀圖控件"""
        # 建立樹狀圖容器
        tree_container = tk.Frame(self.tree_frame, bg=AppConfig.COLORS['window_bg'])
        tree_container.pack(fill='both', expand=True)

        # 樹狀圖 - 移除滾動軸
        self.tree = ttk.Treeview(
            tree_container,
            selectmode='extended'
        )
        self.tree.pack(fill='both', expand=True)

        # 進度追蹤可視化區域
        self.progress_frame = tk.Frame(
            tree_container,
            bg=AppConfig.COLORS['window_bg'],
            height=200
        )
        self.progress_frame.pack(side='bottom', fill='x', pady=2)
        self.progress_frame.pack_propagate(False)

        # 設定樹狀圖樣式
        self._setup_tree_style()

        # 設定欄位
        self._update_tree_columns()

        # 設定進度可視化
        self._setup_progress_visualization()

        # 綁定事件
        self.tree.bind('<Double-1>', self._on_item_double_click)
        self.tree.bind('<Button-3>', self._on_item_right_click)
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

    def _setup_tree_style(self):
        """設定樹狀圖樣式"""
        self.style.configure(
            'Treeview',
            background='white',
            foreground='black',
            rowheight=25,
            fieldbackground='white'
        )

        self.style.configure(
            'Treeview.Heading',
            background=AppConfig.COLORS['title_bg'],
            foreground='black',
            font=AppConfig.FONTS['button']  # 使用統一字體
        )

        # 交替行顏色
        self.tree.tag_configure('oddrow', background='#F0F0F0')
        self.tree.tag_configure('evenrow', background='white')

    def _update_tree_columns(self):
        """更新樹狀圖欄位"""
        try:
            # 🔥 修正：使用 OVERVIEW_FIELDS 而不是 CASE_FIELDS
            visible_fields = []
            for field_id, field_info in AppConfig.OVERVIEW_FIELDS.items():
                if field_info['visible']:
                    visible_fields.append(field_id)

            print(f"更新欄位配置: 可見欄位 = {visible_fields}")

            # 直接使用可見欄位作為樹狀圖欄位
            self.tree.configure(columns=visible_fields)
            self.tree['show'] = 'headings'

            # 配置可見欄位
            for field_id in visible_fields:
                field_info = AppConfig.OVERVIEW_FIELDS[field_id]
                self.tree.heading(field_id, text=field_info['name'], anchor='center')
                self.tree.column(field_id, width=field_info['width'], minwidth=80, anchor='center')

        except Exception as e:
            print(f"更新樹狀圖欄位失敗: {e}")

    def _create_field_controls(self):
        """建立欄位顯示控制"""
        # 控制標題
        control_title = tk.Label(
            self.field_control_frame,
            text="隱藏欄位：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        control_title.pack(side='left', padx=(10, 20))

        # 🔥 修正：使用 OVERVIEW_FIELDS
        self.field_vars = {}
        for field_id, field_info in AppConfig.OVERVIEW_FIELDS.items():
            var = tk.BooleanVar(value=not field_info['visible'])
            self.field_vars[field_id] = var

            checkbox = tk.Checkbutton(
                self.field_control_frame,
                text=field_info['name'],
                variable=var,
                command=lambda fid=field_id: self._toggle_field(fid),
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                selectcolor=AppConfig.COLORS['button_bg'],
                activebackground=AppConfig.COLORS['window_bg'],
                activeforeground=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['text']
            )
            checkbox.pack(side='left', padx=10)

    def _toggle_field(self, field_id: str):
        """切換欄位顯示狀態"""
        # 🔥 修正：使用 OVERVIEW_FIELDS
        is_hidden = self.field_vars[field_id].get()
        # 修改實例變數而不是類別常數
        if not hasattr(self, 'visible_fields'):
            self.visible_fields = AppConfig.OVERVIEW_FIELDS.copy()

        self.visible_fields[field_id]['visible'] = not is_hidden

        # 更新樹狀圖
        self._update_tree_columns()
        self._refresh_tree_data()

    def _load_cases(self):
        """載入案件資料"""
        try:
            print("開始載入案件資料...")

            if self.case_controller:
                # 🔥 修正：確保控制器資料是最新的
                self.case_controller.load_cases()
                self.case_data = self.case_controller.get_cases()

                print(f"控制器中的案件數量: {len(self.case_controller.cases)}")
                print(f"視圖中的案件數量: {len(self.case_data)}")

                # 重新整理樹狀圖
                self._refresh_tree_data()

                print("案件資料載入完成")
            else:
                print("案件控制器未初始化")

        except Exception as e:
            print(f"載入案件資料失敗: {e}")
            messagebox.showerror("錯誤", f"載入案件資料失敗：{str(e)}")


    def _refresh_tree_data(self):
        """重新整理樹狀圖資料"""
        try:
            print(f"開始重新整理樹狀圖，案件數量: {len(self.case_data)}")

            # 清空現有資料
            for item in self.tree.get_children():
                self.tree.delete(item)

            # 取得當前樹狀圖的欄位配置
            current_columns = list(self.tree['columns'])
            print(f"當前樹狀圖欄位: {current_columns}")

            # 重新載入資料
            for i, case in enumerate(self.case_data):
                values = []

                for col_id in current_columns:
                    # 使用 getattr 安全存取屬性，避免 KeyError
                    if col_id == 'case_type':
                        values.append(getattr(case, 'case_type', ''))
                    elif col_id == 'client':
                        values.append(getattr(case, 'client', ''))
                    elif col_id == 'lawyer':
                        values.append(getattr(case, 'lawyer', '') or '')
                    elif col_id == 'legal_affairs':
                        values.append(getattr(case, 'legal_affairs', '') or '')
                    elif col_id == 'case_reason':
                        values.append(getattr(case, 'case_reason', '') or '')
                    elif col_id == 'case_number':
                        values.append(getattr(case, 'case_number', '') or '')
                    elif col_id == 'opposing_party':
                        values.append(getattr(case, 'opposing_party', '') or '')
                    elif col_id == 'court':
                        values.append(getattr(case, 'court', '') or '')
                    elif col_id == 'division':
                        values.append(getattr(case, 'division', '') or '')
                    else:
                        values.append('')

                # 設定交替行顏色
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                item_id = self.tree.insert('', 'end', values=values, tags=(tag,))

                # 🔥 修正：使用 item 的 tag 來儲存索引，而不是設定隱藏欄位
                # 原本錯誤的寫法：self.tree.set(item_id, '#0', str(i))
                # 新的正確寫法：在 tags 中加入索引資訊
                existing_tags = self.tree.item(item_id, 'tags')
                new_tags = list(existing_tags) + [f'index_{i}']
                self.tree.item(item_id, tags=new_tags)

            print(f"樹狀圖重新整理完成，已載入 {len(self.case_data)} 筆資料")

        except Exception as e:
            print(f"重新整理樹狀圖資料失敗: {e}")
            import traceback
            traceback.print_exc()

    def _setup_progress_visualization(self):
        """設定進度可視化區域"""
        # 標題
        progress_title = tk.Label(
            self.progress_frame,
            text="案件追蹤進度",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        progress_title.pack(pady=5)

        # 進度顯示區域
        self.progress_display = tk.Frame(
            self.progress_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.progress_display.pack(fill='both', expand=True, padx=20)

    def _on_tree_select(self, event):
        """樹狀圖選擇事件"""
        selection = self.tree.selection()
        if selection:
            # 清空進度顯示
            for widget in self.progress_display.winfo_children():
                widget.destroy()

            # 取得選中的案件
            item = selection[0]
            try:
                # 🔥 修正：從 tags 中取得索引
                tags = self.tree.item(item, 'tags')
                case_index = None

                for tag in tags:
                    if tag.startswith('index_'):
                        case_index = int(tag.replace('index_', ''))
                        break

                if case_index is not None and case_index < len(self.case_data):
                    case = self.case_data[case_index]
                    self._display_case_progress(case)
                else:
                    print(f"無法取得有效的案件索引：tags={tags}")

            except (ValueError, IndexError) as e:
                print(f"取得案件索引失敗: {e}")

    # 修正 views/case_overview.py 中的 _display_case_progress 方法

    def _display_case_progress(self, case: 'CaseData'):
        """顯示案件進度 - 根據選中資料動態顯示，包含日期資訊"""
        # 清空進度顯示
        for widget in self.progress_display.winfo_children():
            widget.destroy()

        # 左側案件資訊
        info_frame = tk.Frame(
            self.progress_display,
            bg=AppConfig.COLORS['window_bg']
        )
        info_frame.pack(side='left', padx=10, anchor='nw')

        # 第一排：案號（單獨一排，突出顯示）
        case_number = getattr(case, 'case_number', None) or '未設定'
        tk.Label(
            info_frame,
            text=f"案號: {case_number}",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',  # 綠色突出顯示
            font=AppConfig.FONTS['button'],  # 較大字體
            wraplength=280
        ).pack(anchor='w', pady=(0, 8))

        # 第二排：案由、對造（並排顯示）
        row2_frame = tk.Frame(info_frame, bg=AppConfig.COLORS['window_bg'])
        row2_frame.pack(fill='x', pady=(0, 5))

        case_reason = getattr(case, 'case_reason', None) or '未設定'
        opposing_party = getattr(case, 'opposing_party', None) or '未設定'

        tk.Label(
            row2_frame,
            text=f"案由: {case_reason}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=140
        ).pack(side='left', anchor='nw')

        tk.Label(
            row2_frame,
            text=f"對造: {opposing_party}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=140
        ).pack(side='left', anchor='nw', padx=(20, 0))

        # 第三排：負責法院、負責股別（並排顯示）
        row3_frame = tk.Frame(info_frame, bg=AppConfig.COLORS['window_bg'])
        row3_frame.pack(fill='x', pady=(0, 8))

        court = getattr(case, 'court', None) or '未設定'
        division = getattr(case, 'division', None) or '未設定'

        tk.Label(
            row3_frame,
            text=f"負責法院: {court}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=140
        ).pack(side='left', anchor='nw')

        tk.Label(
            row3_frame,
            text=f"負責股別: {division}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=140
        ).pack(side='left', anchor='nw', padx=(20, 0))

        # 分隔線
        tk.Label(
            info_frame,
            text="─" * 25,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(5, 5))

        # 🔥 修改：當前進度狀態和日期
        current_stage = getattr(case, 'progress', '待處理')
        current_date = getattr(case, 'progress_date', None)

        progress_text = f"目前狀態: {current_stage}"
        if current_date:
            progress_text += f" ({current_date})"

        tk.Label(
            info_frame,
            text=progress_text,
            bg=AppConfig.COLORS['window_bg'],
            fg='#FF9800',  # 橙色
            font=AppConfig.FONTS['button']
        ).pack(anchor='w', pady=(0, 10))

        # 🔥 新增：進度歷史顯示
        progress_history = getattr(case, 'progress_history', {})
        if progress_history:
            tk.Label(
                info_frame,
                text="進度歷史:",
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['button']
            ).pack(anchor='w', pady=(5, 5))

            # 顯示進度歷史（限制顯示最近5個）
            history_items = list(progress_history.items())[-5:]  # 只顯示最近5個
            for progress_stage, date in history_items:
                tk.Label(
                    info_frame,
                    text=f"  • {progress_stage}: {date}",
                    bg=AppConfig.COLORS['window_bg'],
                    fg='#B0B0B0',  # 淺灰色
                    font=AppConfig.FONTS['text']
                ).pack(anchor='w')

        # 🔥 修改：右側進度條 - 包含日期資訊
        progress_bar_frame = tk.Frame(
            self.progress_display,
            bg=AppConfig.COLORS['window_bg']
        )
        progress_bar_frame.pack(side='right', expand=True, fill='x', padx=20)

        # 根據案件類型取得對應的進度階段
        case_type = getattr(case, 'case_type', '')
        stages = AppConfig.get_progress_options(case_type)
        progress_history = getattr(case, 'progress_history', {})

        for i, stage in enumerate(stages):
            # 每個階段的容器
            stage_container = tk.Frame(
                progress_bar_frame,
                bg=AppConfig.COLORS['window_bg']
            )
            stage_container.pack(side='left', expand=True)

            # 圓圈框架
            circle_frame = tk.Frame(
                stage_container,
                bg=AppConfig.COLORS['window_bg']
            )
            circle_frame.pack()

            # 判斷階段狀態
            if stage == current_stage:
                bg_color = '#4CAF50'  # 綠色 - 當前階段
                fg_color = 'white'
            elif current_stage in stages and stages.index(current_stage) > i:
                bg_color = '#2196F3'  # 藍色 - 已完成
                fg_color = 'white'
            else:
                bg_color = '#E0E0E0'  # 灰色 - 未開始
                fg_color = 'black'

            # 進度圓圈
            circle = tk.Label(
                circle_frame,
                text=str(i+1),
                bg=bg_color,
                fg=fg_color,
                font=AppConfig.FONTS['text'],
                width=3,
                height=1
            )
            circle.pack()

            # 階段名稱
            stage_label = tk.Label(
                circle_frame,
                text=stage,
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=('Microsoft JhengHei', 8)
            )
            stage_label.pack()

            # 🔥 新增：顯示該階段的日期（如果有的話）
            stage_date = progress_history.get(stage)
            if stage_date:
                date_label = tk.Label(
                    circle_frame,
                    text=stage_date,
                    bg=AppConfig.COLORS['window_bg'],
                    fg='#888888',  # 深灰色
                    font=('Microsoft JhengHei', 7)
                )
                date_label.pack()

            # 連接線（除了最後一個階段）
            if i < len(stages) - 1:
                line_color = '#2196F3' if current_stage in stages and stages.index(current_stage) > i else '#E0E0E0'
                line_frame = tk.Frame(
                    progress_bar_frame,
                    bg=line_color,
                    height=2,
                    width=30
                )
                line_frame.pack(side='left', pady=15)

    # 事件處理方法
    def _on_add_case(self):
        """新增案件事件"""
        if not self.case_controller:
            messagebox.showwarning("提醒", "案件控制器未初始化")
            return

        from views.case_form import CaseFormDialog

        def save_new_case(case_data, mode):
            """新增案件的回調函數"""
            try:
                print(f"開始新增案件: {case_data.client}")

                # 產生新的案件編號
                case_data.case_id = self.case_controller.generate_case_id()
                print(f"產生案件編號: {case_data.case_id}")

                # 儲存案件並建立資料夾結構
                success = self.case_controller.add_case(case_data)

                if success:
                    print(f"案件新增成功，開始重新載入資料")

                    # 🔥 修正：強制重新載入案件資料
                    self.case_controller.load_cases()  # 重新載入控制器資料
                    self._load_cases()  # 重新載入視圖資料

                    print(f"資料重新載入完成，當前案件數量: {len(self.case_data)}")

                    # 取得建立的資料夾路徑
                    folder_path = self.case_controller.get_case_folder_path(case_data.case_id)

                    if folder_path:
                        message = f"案件 {case_data.case_id} 新增成功！\n\n已建立資料夾結構：\n{folder_path}"
                    else:
                        message = f"案件 {case_data.case_id} 新增成功！\n\n注意：資料夾結構建立失敗，請手動建立。"

                    # 🔥 修正：使用 after 方法延遲顯示訊息，確保對話框先關閉
                    self.window.after(100, lambda: messagebox.showinfo("成功", message))

                else:
                    print(f"案件新增失敗")
                    messagebox.showerror("錯誤", "案件新增失敗！")

                return success

            except Exception as e:
                print(f"新增案件回調發生錯誤: {e}")
                messagebox.showerror("錯誤", f"新增案件時發生錯誤：{str(e)}")
                return False

        # 顯示新增案件對話框
        try:
            CaseFormDialog.show_add_dialog(self.window, save_new_case)
        except Exception as e:
            print(f"開啟新增案件對話框失敗: {e}")
            messagebox.showerror("錯誤", f"無法開啟新增案件對話框：{str(e)}")

    def _on_import_excel(self):
        """匯入Excel事件"""
        if not self.case_controller:
            messagebox.showwarning("提醒", "案件控制器未初始化")
            return

        file_path = filedialog.askopenfilename(
            title="選擇要匯入的Excel檔案",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )

        if file_path:
            try:
                success = self.case_controller.import_from_excel(file_path)
                if success:
                    self._load_cases()
                    messagebox.showinfo("成功", "Excel資料匯入成功！")
                else:
                    messagebox.showerror("錯誤", "Excel資料匯入失敗！")
            except Exception as e:
                messagebox.showerror("錯誤", f"匯入過程發生錯誤：{str(e)}")

    def _on_export_excel(self):
        """匯出Excel事件"""
        if not self.case_controller:
            messagebox.showwarning("提醒", "案件控制器未初始化")
            return

        if not self.case_data:
            messagebox.showwarning("提醒", "沒有資料可以匯出")
            return

        file_path = filedialog.asksaveasfilename(
            title="儲存Excel檔案",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if file_path:
            try:
                success = self.case_controller.export_to_excel(file_path)
                if success:
                    messagebox.showinfo("成功", f"資料已匯出到：\n{file_path}")
                else:
                    messagebox.showerror("錯誤", "資料匯出失敗！")
            except Exception as e:
                messagebox.showerror("錯誤", f"匯出過程發生錯誤：{str(e)}")

    def _on_refresh(self):
        """重新整理事件"""
        try:
            print("手動重新整理...")
            self._load_cases()
            print("手動重新整理完成")
        except Exception as e:
            print(f"手動重新整理失敗: {e}")
            messagebox.showerror("錯誤", f"重新整理失敗：{str(e)}")

    def _on_item_double_click(self, event):
        """項目雙擊事件 - 編輯案件"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]

            # 🔥 修正：從 tags 中取得索引
            tags = self.tree.item(item, 'tags')
            case_index = None

            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case = self.case_data[case_index]

                from views.case_form import CaseFormDialog

                def save_edited_case(case_data, mode):
                    success = self.case_controller.update_case(case.case_id, case_data)
                    if success:
                        self._load_cases()
                        # 使用 after 延遲顯示訊息
                        self.window.after(100, lambda: messagebox.showinfo("成功", f"案件 {case_data.case_id} 更新成功！"))
                    else:
                        messagebox.showerror("錯誤", "案件更新失敗！")
                    return success

                CaseFormDialog.show_edit_dialog(self.window, case, save_edited_case)
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except (ValueError, IndexError) as e:
            print(f"取得案件索引失敗: {e}")
            messagebox.showerror("錯誤", "無法開啟案件編輯")

    def _on_item_right_click(self, event):
        """項目右鍵事件 - 顯示案件操作選單"""
        # 選取點擊的項目
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)

            # 建立右鍵選單
            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(label="編輯案件", command=lambda: self._on_item_double_click(None))
            context_menu.add_command(label="進度歷史管理", command=self._on_manage_progress_history)  # 🔥 新增
            context_menu.add_separator()
            context_menu.add_command(label="刪除案件", command=self._on_delete_case)
            context_menu.add_separator()
            context_menu.add_command(label="開啟案件資料夾", command=self._on_open_case_folder)
            context_menu.add_command(label="更新Excel檔案", command=self._on_update_case_excel)

            # 顯示選單
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def _on_manage_progress_history(self):
        """🔥 新增：管理進度歷史"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]

            # 從 tags 中取得索引
            tags = self.tree.item(item, 'tags')
            case_index = None

            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case = self.case_data[case_index]

                from views.progress_history_dialog import ProgressHistoryDialog

                def update_case_progress_history(case_data):
                    """更新案件進度歷史的回調函數"""
                    success = self.case_controller.update_case(case.case_id, case_data)
                    if success:
                        self._load_cases()  # 重新載入資料
                    return success

                ProgressHistoryDialog.show_dialog(self.window, case, update_case_progress_history)
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except (ValueError, IndexError) as e:
            print(f"管理進度歷史失敗: {e}")
            messagebox.showerror("錯誤", "無法開啟進度歷史管理")

    def _on_delete_case(self):
        """刪除案件"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]

            # 🔥 修正：從 tags 中取得索引
            tags = self.tree.item(item, 'tags')
            case_index = None

            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case = self.case_data[case_index]

                from views.dialogs import ConfirmDialog
                if ConfirmDialog.ask(self.window, "確認刪除", f"確定要刪除案件 {case.case_id} - {case.client} 嗎？"):
                    success = self.case_controller.delete_case(case.case_id)
                    if success:
                        self._load_cases()
                        messagebox.showinfo("成功", f"案件 {case.case_id} 已刪除")
                    else:
                        messagebox.showerror("錯誤", "案件刪除失敗")
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except (ValueError, IndexError) as e:
            print(f"刪除案件失敗: {e}")
            messagebox.showerror("錯誤", "無法刪除案件")

    def _on_open_case_folder(self):
        """開啟案件資料夾"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]

            # 🔥 修正：從 tags 中取得索引
            tags = self.tree.item(item, 'tags')
            case_index = None

            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case = self.case_data[case_index]

                folder_path = self.case_controller.get_case_folder_path(case.case_id)
                if folder_path and os.path.exists(folder_path):
                    os.startfile(folder_path)  # Windows
                else:
                    messagebox.showwarning("提醒", "找不到案件資料夾")
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except Exception as e:
            print(f"開啟資料夾失敗: {e}")
            messagebox.showerror("錯誤", "無法開啟案件資料夾")

    def _on_update_case_excel(self):
        """更新案件Excel檔案"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]

            # 🔥 修正：從 tags 中取得索引
            tags = self.tree.item(item, 'tags')
            case_index = None

            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case = self.case_data[case_index]

                success = self.case_controller.folder_manager.update_case_info_excel(case)
                if success:
                    messagebox.showinfo("成功", f"案件 {case.case_id} 的Excel檔案已更新")
                else:
                    messagebox.showerror("錯誤", "Excel檔案更新失敗")
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except Exception as e:
            print(f"更新Excel檔案失敗: {e}")
            messagebox.showerror("錯誤", "無法更新Excel檔案")


    def add_case_data(self, case: CaseData):
        """新增案件資料"""
        if self.case_controller:
            success = self.case_controller.add_case(case)
            if success:
                self._load_cases()
                return True
        return False

    def update_case_data(self, cases: List[CaseData]):
        """更新所有案件資料"""
        self.case_data = cases
        self._refresh_tree_data()

    def close(self):
        """關閉視窗"""
        self.window.destroy()

    def show(self):
        """顯示視窗"""
        self.window.deiconify()

    def hide(self):
        """隱藏視窗"""
        self.window.withdraw()