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
        self.visible_fields = AppConfig.CASE_FIELDS.copy()
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
        self.tree_frame.pack(fill='both', expand=True, pady=(0, 10))

        # 欄位控制區域
        self.field_control_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg'],
            height=60
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
            height=100
        )
        self.progress_frame.pack(side='bottom', fill='x', pady=5)
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
            # 取得當前可見欄位
            visible_fields = []
            for field_id, field_info in self.visible_fields.items():
                if field_info['visible']:
                    visible_fields.append(field_id)

            print(f"更新欄位配置: 可見欄位 = {visible_fields}")

            # 直接使用可見欄位作為樹狀圖欄位
            self.tree.configure(columns=visible_fields)
            self.tree['show'] = 'headings'

            # 配置可見欄位
            for field_id in visible_fields:
                field_info = self.visible_fields[field_id]
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
            font=AppConfig.FONTS['button']  # 使用統一字體
        )
        control_title.pack(side='left', padx=(10, 20))

        # 欄位勾選框
        self.field_vars = {}
        for field_id, field_info in AppConfig.CASE_FIELDS.items():
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
                font=AppConfig.FONTS['text']  # 使用統一字體
            )
            checkbox.pack(side='left', padx=10)

    def _toggle_field(self, field_id: str):
        """切換欄位顯示狀態"""
        # 更新欄位可見性
        is_hidden = self.field_vars[field_id].get()
        self.visible_fields[field_id]['visible'] = not is_hidden

        # 更新樹狀圖
        self._update_tree_columns()
        self._refresh_tree_data()

    def _load_cases(self):
        """載入案件資料"""
        if self.case_controller:
            self.case_data = self.case_controller.get_cases()
            self._refresh_tree_data()

    def _refresh_tree_data(self):
        """重新整理樹狀圖資料"""
        try:
            # 清空現有資料
            for item in self.tree.get_children():
                self.tree.delete(item)

            # 取得當前樹狀圖的欄位配置
            current_columns = list(self.tree['columns'])
            print(f"當前樹狀圖欄位: {current_columns}")

            # 重新載入資料
            for i, case in enumerate(self.case_data):
                # 按照當前欄位順序建立數值列表
                values = []

                for col_id in current_columns:
                    if col_id == 'case_type':
                        values.append(case.case_type)
                    elif col_id == 'client':
                        values.append(case.client)
                    elif col_id == 'lawyer':
                        values.append(case.lawyer or '')
                    elif col_id == 'legal_affairs':
                        values.append(case.legal_affairs or '')
                    else:
                        values.append('')  # 未知欄位預設空值

                # 設定交替行顏色，使用項目ID儲存索引
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                item_id = self.tree.insert('', 'end', values=values, tags=(tag,))

                # 將索引儲存在項目的tags中
                self.tree.set(item_id, '#0', str(i))  # 在隱藏欄位儲存索引

            print(f"已載入 {len(self.case_data)} 筆資料")

        except Exception as e:
            print(f"重新整理樹狀圖資料失敗: {e}")

    def _setup_progress_visualization(self):
        """設定進度可視化區域"""
        # 標題
        progress_title = tk.Label(
            self.progress_frame,
            text="案件進度可視化",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']  # 使用統一字體
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
                # 從項目的隱藏欄位取得索引
                case_index_str = self.tree.set(item, '#0')
                if case_index_str:
                    case_index = int(case_index_str)
                    case = self.case_data[case_index]
                    self._display_case_progress(case)
            except (ValueError, IndexError) as e:
                print(f"取得案件索引失敗: {e}")

    def _display_case_progress(self, case: 'CaseData'):
        """顯示案件進度 - 根據選中資料動態顯示"""
        # 進度階段
        stages = ['待處理', '一審', '二審', '三審', '合議庭', '已結案']
        current_stage = case.progress

        # 左側案件資訊
        info_frame = tk.Frame(
            self.progress_display,
            bg=AppConfig.COLORS['window_bg']
        )
        info_frame.pack(side='left', padx=10, anchor='nw')

        # 顯示可見欄位的資料
        visible_fields = [field_id for field_id, field_info in self.visible_fields.items() if field_info['visible']]

        # 案件編號（固定顯示）
        tk.Label(
            info_frame,
            text=f"案件編號: {case.case_id}",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']  # 使用統一字體
        ).pack(anchor='w')

        # 根據可見欄位動態顯示資訊
        for field_id in visible_fields:
            field_name = self.visible_fields[field_id]['name']
            if field_id == 'case_type':
                value = case.case_type
            elif field_id == 'client':
                value = case.client
            elif field_id == 'lawyer':
                value = case.lawyer or '未指派'
            elif field_id == 'legal_affairs':
                value = case.legal_affairs or '未指派'
            else:
                continue

            tk.Label(
                info_frame,
                text=f"{field_name}: {value}",
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['text']  # 使用統一字體
            ).pack(anchor='w')

        # 當前進度狀態
        tk.Label(
            info_frame,
            text=f"目前狀態: {current_stage}",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['text']  # 使用統一字體
        ).pack(anchor='w', pady=(5, 0))

        # 右側進度條
        progress_bar_frame = tk.Frame(
            self.progress_display,
            bg=AppConfig.COLORS['window_bg']
        )
        progress_bar_frame.pack(side='right', expand=True, fill='x', padx=20)

        for i, stage in enumerate(stages):
            # 進度圓圈容器
            circle_frame = tk.Frame(
                progress_bar_frame,
                bg=AppConfig.COLORS['window_bg']
            )
            circle_frame.pack(side='left', expand=True)

            # 判斷狀態
            if stage == current_stage:
                bg_color = '#4CAF50'  # 綠色 - 當前階段
                fg_color = 'white'
            elif stages.index(current_stage) > i:
                bg_color = '#2196F3'  # 藍色 - 已完成
                fg_color = 'white'
            else:
                bg_color = '#E0E0E0'  # 灰色 - 未開始
                fg_color = 'black'

            # 圓圈
            circle = tk.Label(
                circle_frame,
                text=str(i+1),
                bg=bg_color,
                fg=fg_color,
                font=AppConfig.FONTS['text'],  # 使用統一字體
                width=3,
                height=1
            )
            circle.pack()

            # 階段名稱
            tk.Label(
                circle_frame,
                text=stage,
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=('Microsoft JhengHei', 8)
            ).pack()

            # 連接線 (除了最後一個)
            if i < len(stages) - 1:
                line_color = '#2196F3' if stages.index(current_stage) > i else '#E0E0E0'
                tk.Frame(
                    progress_bar_frame,
                    bg=line_color,
                    height=2,
                    width=30
                ).pack(side='left', pady=15)

    # 事件處理方法
    def _on_add_case(self):
        """新增案件事件"""
        if self.case_controller:
            # 此處可以開啟新增案件對話框
            print("開啟新增案件對話框")
        else:
            messagebox.showwarning("提醒", "案件控制器未初始化")

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
        self._load_cases()

    def _on_item_double_click(self, event):
        """項目雙擊事件"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            try:
                case_index_str = self.tree.set(item, '#0')
                if case_index_str:
                    case_index = int(case_index_str)
                    case = self.case_data[case_index]
                    print(f"雙擊案件: 索引={case_index}, 類型={case.case_type}, 當事人={case.client}")
            except (ValueError, IndexError) as e:
                print(f"取得案件索引失敗: {e}")

    def _on_item_right_click(self, event):
        """項目右鍵事件"""
        print("右鍵選單功能待實作")

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