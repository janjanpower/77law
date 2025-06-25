from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional
import os
from config.settings import AppConfig
from models.case_model import CaseData
from views.dialogs import UnifiedMessageDialog

class CaseOverviewWindow:
    """案件總覽視窗"""
    def __init__(self, parent=None, case_controller=None):
        self.parent = parent
        self.case_controller = case_controller
        self.visible_fields = AppConfig.OVERVIEW_FIELDS.copy()
        self.case_data: List[CaseData] = []
        self.drag_data = {"x": 0, "y": 0}
        self.progress_widgets = {}

        # 新增：初始化搜尋相關變數
        self.filtered_case_data = []
        self.search_var = tk.StringVar()

        # 建立視窗
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self._setup_window()
        self._setup_styles()
        self._create_layout()

        # 載入案件資料
        if self.case_controller:
            self._load_cases()

        # 確保視窗顯示
        self.window.update()
        self.window.deiconify()

    def _setup_window(self):
        """設定視窗基本屬性"""
        self.window.title(AppConfig.WINDOW_TITLES['overview'])
        self.window.geometry("800x600")  # 設定初始大小
        self.window.configure(bg=AppConfig.COLORS['window_bg'])
        self.window.overrideredirect(True)
        self.window.minsize(1000, 700)

        # 確保視窗可見
        self.window.deiconify()
        self.window.lift()

        self._center_window()

    def _center_window(self):
        """將視窗置中顯示"""
        self.window.update_idletasks()
        width = 800
        height = 600
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_styles(self):
        """設定 ttk 樣式"""
        self.style = ttk.Style()

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
        self.main_frame.pack(fill='both', expand=True)

        # 自定義標題列
        self.title_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['title_bg'],
            height=AppConfig.SIZES['title_height']
        )
        self.title_frame.pack(fill='x')
        self.title_frame.pack_propagate(False)

        self.title_label = tk.Label(
            self.title_frame,
            text=AppConfig.WINDOW_TITLES['overview'],
            bg=AppConfig.COLORS['title_bg'],
            fg=AppConfig.COLORS['title_fg'],
            font=AppConfig.FONTS['title']
        )
        self.title_label.pack(side='left', padx=10)

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

        self._setup_drag()

        # 內容區域
        self.content_frame = tk.Frame(
            self.main_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.content_frame.pack(fill='both', expand=True,padx=5,pady=10)

        self._create_overview_layout()
        self._setup_treeview()
        self._create_field_controls()

    def _setup_drag(self):
        """設定視窗拖曳功能"""
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        def on_drag(event):
            x = self.window.winfo_x() + (event.x - self.drag_data["x"])
            y = self.window.winfo_y() + (event.y - self.drag_data["y"])
            self.window.geometry(f"+{x}+{y}")

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

        self._create_toolbar_buttons()

        # 搜尋區域 - 新增
        self.search_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg'],
            height=40
        )
        self.search_frame.pack(fill='x', pady=(0, 10))
        self.search_frame.pack_propagate(False)

        self._create_search_bar()

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
            height=25
        )
        self.field_control_frame.pack(fill='x')
        self.field_control_frame.pack_propagate(False)

    def _create_search_bar(self):
        """建立搜尋條"""
        # 搜尋標籤
        search_label = tk.Label(
            self.search_frame,
            text="搜尋：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        search_label.pack(side='left', padx=(10, 5))

        # 搜尋輸入框
        self.search_entry = tk.Entry(
            self.search_frame,
            textvariable=self.search_var,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text'],
            width=30
        )
        self.search_entry.pack(side='left', padx=5)

        # 綁定搜尋事件
        self.search_var.trace_add('write', self._on_search_changed)
        self.search_entry.bind('<Return>', self._on_search_enter)

        # 搜尋說明
        search_help = tk.Label(
            self.search_frame,
            text="（可搜尋：當事人、案號、案件類型）",
            bg=AppConfig.COLORS['window_bg'],
            fg='#AAAAAA',
            font=('Microsoft JhengHei', 8)
        )
        search_help.pack(side='left', padx=(10, 0))

        # 清除搜尋按鈕
        clear_btn = tk.Button(
            self.search_frame,
            text="清除",
            command=self._clear_search,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['text'],
            width=6
        )
        clear_btn.pack(side='left', padx=(10, 0))

        # 搜尋結果統計
        self.search_result_label = tk.Label(
            self.search_frame,
            text="",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['text']
        )
        self.search_result_label.pack(side='right', padx=(0, 10))

    def _on_search_changed(self, *args):
        """搜尋內容變更時的即時搜尋"""
        # 延遲搜尋以避免過於頻繁的搜尋
        if hasattr(self, '_search_after_id'):
            self.window.after_cancel(self._search_after_id)

        self._search_after_id = self.window.after(300, self._perform_search)

    def _on_search_enter(self, event):
        """按Enter鍵時立即搜尋"""
        if hasattr(self, '_search_after_id'):
            self.window.after_cancel(self._search_after_id)

        self._perform_search()

    def _perform_search(self):
        """執行搜尋"""
        try:
            search_text = self.search_var.get().strip().lower()

            if not search_text:
                # 沒有搜尋文字時顯示所有資料
                self.filtered_case_data = self.case_data.copy()
                self.search_result_label.config(text="")
            else:
                # 執行搜尋
                self.filtered_case_data = []

                for case in self.case_data:
                    # 搜尋當事人
                    if search_text in case.client.lower():
                        self.filtered_case_data.append(case)
                        continue

                    # 搜尋案號
                    case_number = getattr(case, 'case_number', '') or ''
                    if search_text in case_number.lower():
                        self.filtered_case_data.append(case)
                        continue

                    # 搜尋案件類型
                    if search_text in case.case_type.lower():
                        self.filtered_case_data.append(case)
                        continue

                    # 搜尋案件編號
                    if search_text in case.case_id.lower():
                        self.filtered_case_data.append(case)
                        continue

                    # 搜尋委任律師
                    lawyer = getattr(case, 'lawyer', '') or ''
                    if search_text in lawyer.lower():
                        self.filtered_case_data.append(case)
                        continue

                    # 搜尋法務
                    legal_affairs = getattr(case, 'legal_affairs', '') or ''
                    if search_text in legal_affairs.lower():
                        self.filtered_case_data.append(case)
                        continue

                    # 搜尋案由
                    case_reason = getattr(case, 'case_reason', '') or ''
                    if search_text in case_reason.lower():
                        self.filtered_case_data.append(case)
                        continue

                # 更新搜尋結果統計
                total_count = len(self.case_data)
                filtered_count = len(self.filtered_case_data)
                self.search_result_label.config(
                    text=f"找到 {filtered_count} / {total_count} 筆資料"
                )

            # 更新樹狀圖顯示
            self._refresh_filtered_tree_data()

            # 清空進度顯示（因為搜尋後選擇會改變）
            for widget in self.progress_display.winfo_children():
                widget.destroy()
            self.progress_widgets.clear()

        except Exception as e:
            print(f"搜尋失敗: {e}")
            import traceback
            traceback.print_exc()

    def _clear_search(self):
        """清除搜尋"""
        self.search_var.set("")
        self.search_entry.focus()

    def _refresh_filtered_tree_data(self):
        """重新整理樹狀圖資料（使用過濾後的資料）"""
        try:
            # 使用過濾後的資料
            data_to_display = self.filtered_case_data if hasattr(self, 'filtered_case_data') else self.case_data

            print(f"開始重新整理樹狀圖，顯示案件數量: {len(data_to_display)}")

            # 清空現有項目
            for item in self.tree.get_children():
                self.tree.delete(item)

            current_columns = list(self.tree['columns'])
            print(f"當前樹狀圖欄位: {current_columns}")

            # 填入過濾後的資料
            for i, case in enumerate(data_to_display):
                values = []

                for col_id in current_columns:
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

                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                item_id = self.tree.insert('', 'end', values=values, tags=(tag,))

                # 保存原始案件索引以便後續操作
                original_index = self.case_data.index(case)
                existing_tags = self.tree.item(item_id, 'tags')
                new_tags = list(existing_tags) + [f'index_{original_index}']
                self.tree.item(item_id, tags=new_tags)

            print(f"樹狀圖重新整理完成，已載入 {len(data_to_display)} 筆資料")

        except Exception as e:
            print(f"重新整理樹狀圖資料失敗: {e}")
            import traceback
            traceback.print_exc()

    def _create_toolbar_buttons(self):
        """建立工具列按鈕"""
        self.add_case_btn = self.create_button(
            self.toolbar_frame,
            '新增案件',
            self._on_add_case,
            'Function'
        )
        self.add_case_btn.pack(side='left', padx=(10, 5))

        self.upload_btn = self.create_button(
            self.toolbar_frame,
            '上傳資料',
            self._on_upload_data,
            'Function'
        )
        self.upload_btn.pack(side='left', padx=5)

        self.export_btn = self.create_button(
            self.toolbar_frame,
            '匯出案件資訊',
            self._on_export_excel,
            'Function'
        )
        self.export_btn.pack(side='left', padx=5)

    def create_button(self, parent, text, command, style_type='Custom'):
        """建立標準化按鈕"""
        if style_type == 'Function':
            return tk.Button(
                parent,
                text=text,
                command=command,
                bg=AppConfig.COLORS['button_bg'],
                fg=AppConfig.COLORS['button_fg'],
                font=AppConfig.FONTS['button'],
                width=14,
                height=0
            )
        else:
            return tk.Button(
                parent,
                text=text,
                command=command,
                bg=AppConfig.COLORS['button_bg'],
                fg=AppConfig.COLORS['button_fg'],
                font=AppConfig.FONTS['button'],
                width=10
            )

    def _setup_treeview(self):
        """設定樹狀圖控件"""
        tree_container = tk.Frame(self.tree_frame, bg=AppConfig.COLORS['window_bg'])
        tree_container.pack(fill='both', expand=True)

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

        self._setup_tree_style()
        self._update_tree_columns()
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
            font=AppConfig.FONTS['button']
        )

        self.tree.tag_configure('oddrow', background='#F0F0F0')
        self.tree.tag_configure('evenrow', background='white')

    def _update_tree_columns(self):
        """更新樹狀圖欄位"""
        try:
            visible_fields = []
            for field_id, field_info in AppConfig.OVERVIEW_FIELDS.items():
                if field_info['visible']:
                    visible_fields.append(field_id)

            print(f"更新欄位配置: 可見欄位 = {visible_fields}")

            self.tree.configure(columns=visible_fields)
            self.tree['show'] = 'headings'

            for field_id in visible_fields:
                field_info = AppConfig.OVERVIEW_FIELDS[field_id]
                self.tree.heading(field_id, text=field_info['name'], anchor='center')
                self.tree.column(field_id, width=field_info['width'], minwidth=80, anchor='center')

        except Exception as e:
            print(f"更新樹狀圖欄位失敗: {e}")

    def _create_field_controls(self):
        """建立欄位顯示控制"""
        control_title = tk.Label(
            self.field_control_frame,
            text="隱藏欄位：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        )
        control_title.pack(side='left', padx=(10, 10))

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
        is_hidden = self.field_vars[field_id].get()
        if not hasattr(self, 'visible_fields'):
            self.visible_fields = AppConfig.OVERVIEW_FIELDS.copy()

        self.visible_fields[field_id]['visible'] = not is_hidden
        self._update_tree_columns()
        self._refresh_tree_data()

    def _load_cases(self):
        """載入案件資料（修改原有方法）"""
        try:
            print("開始載入案件資料...")

            if self.case_controller:
                self.case_controller.load_cases()
                self.case_data = self.case_controller.get_cases()

                print(f"控制器中的案件數量: {len(self.case_controller.cases)}")
                print(f"視圖中的案件數量: {len(self.case_data)}")

                # 初始化過濾資料
                self.filtered_case_data = self.case_data.copy()

                # 如果有搜尋條件，重新執行搜尋
                if hasattr(self, 'search_var') and self.search_var.get().strip():
                    self._perform_search()
                else:
                    self._refresh_filtered_tree_data()

                print("案件資料載入完成")
            else:
                print("案件控制器未初始化")

        except Exception as e:
            print(f"載入案件資料失敗: {e}")
            UnifiedMessageDialog.show_error(self.window,  f"載入案件資料失敗：{str(e)}")

    def _refresh_tree_data(self):
        """重新整理樹狀圖資料（支援搜尋過濾）"""
        try:
            # 決定要顯示的資料：如果有過濾資料就用過濾資料，否則用全部資料
            data_to_display = getattr(self, 'filtered_case_data', self.case_data)

            print(f"開始重新整理樹狀圖，顯示案件數量: {len(data_to_display)} / 總數: {len(self.case_data)}")

            # 清空現有項目
            for item in self.tree.get_children():
                self.tree.delete(item)

            current_columns = list(self.tree['columns'])
            print(f"當前樹狀圖欄位: {current_columns}")

            # 遍歷要顯示的資料
            for display_index, case in enumerate(data_to_display):
                values = []

                for col_id in current_columns:
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

                tag = 'evenrow' if display_index % 2 == 0 else 'oddrow'
                item_id = self.tree.insert('', 'end', values=values, tags=(tag,))

                # 重要：使用原始案件在完整列表中的索引，而不是顯示索引
                try:
                    original_index = self.case_data.index(case)
                    existing_tags = self.tree.item(item_id, 'tags')
                    new_tags = list(existing_tags) + [f'index_{original_index}']
                    self.tree.item(item_id, tags=new_tags)
                except ValueError:
                    # 如果找不到原始索引，使用顯示索引作為備案
                    print(f"警告：無法找到案件 {case.case_id} 的原始索引")
                    existing_tags = self.tree.item(item_id, 'tags')
                    new_tags = list(existing_tags) + [f'index_{display_index}']
                    self.tree.item(item_id, tags=new_tags)

            print(f"樹狀圖重新整理完成，已載入 {len(data_to_display)} 筆資料")

        except Exception as e:
            print(f"重新整理樹狀圖資料失敗: {e}")
            import traceback
            traceback.print_exc()

    def _setup_progress_visualization(self):
        """設定進度可視化區域"""
        progress_title = tk.Label(
            self.progress_frame,
            text="案件進度",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        progress_title.pack(pady=5)

        self.progress_display = tk.Frame(
            self.progress_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.progress_display.pack(fill='both', expand=True, padx=10)

    def _on_tree_select(self, event):
        """樹狀圖選擇事件"""
        selection = self.tree.selection()
        if selection:
            # 清空進度顯示
            for widget in self.progress_display.winfo_children():
                widget.destroy()
            self.progress_widgets.clear()

            # 取得選中的案件
            item = selection[0]
            try:
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

    def _get_stage_color_by_date(self, stage_date: str, is_current: bool = False) -> tuple:
        """
        根據日期狀態取得階段顏色

        Args:
            stage_date: 階段日期 (格式: YYYY-MM-DD)
            is_current: 是否為當前階段

        Returns:
            tuple: (背景色, 文字色)
        """
        try:
            if not stage_date or stage_date == '未設定日期':
                return ('#2196F3', 'white')  # 預設藍色

            stage_datetime = datetime.strptime(stage_date, '%Y-%m-%d')
            today = datetime.now()
            date_diff = (stage_datetime - today).days

            # 當天日期：白底黑字
            if date_diff == 0:
                return ('white', 'black')

            # 超過日期：綠色
            elif date_diff < 0:
                return ('#4DC751', 'white')

            # 前三天：黃色底黑字
            elif 0 < date_diff <= 3:
                return ('#E3F45F', 'black')

            # 尚未到期：紅色
            else:
                return ('#CE7B7B', 'white')

        except ValueError:
            # 日期格式錯誤時使用預設顏色
            return ('#2196F3', 'white')

    def _display_case_progress(self, case: 'CaseData'):
        """顯示案件進度 - 使用統一的顯示格式"""
        # 清空進度顯示
        for widget in self.progress_display.winfo_children():
            widget.destroy()
        self.progress_widgets.clear()

        # 左側案件資訊
        info_frame = tk.Frame(
            self.progress_display,
            bg=AppConfig.COLORS['window_bg']
        )
        info_frame.pack(side='left', padx=10, anchor='nw')

        # 案件資訊顯示 - 只顯示案號
        case_number = getattr(case, 'case_number', None) or '未設定'
        tk.Label(
            info_frame,
            text=f"案號: {case_number}",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['button'],
            wraplength=280
        ).pack(anchor='w', pady=(0, 4))

        # 其他資訊並排顯示
        row2_frame = tk.Frame(info_frame, bg=AppConfig.COLORS['window_bg'])
        row2_frame.pack(fill='x', pady=(0, 4))

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
        ).pack(side='left', anchor='nw', padx=(10, 0))

        row3_frame = tk.Frame(info_frame, bg=AppConfig.COLORS['window_bg'])
        row3_frame.pack(fill='x', pady=(0, 4))

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
        ).pack(side='left', anchor='nw', padx=(10, 0))

        # 分隔線
        tk.Label(
            info_frame,
            text="－" * 15,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(5, 5))

        # 當前進度顯示
        current_progress = f"目前狀態: {case.progress}"
        if case.progress_date:
            current_progress += f" ({case.progress_date})"

        tk.Label(
            info_frame,
            text=current_progress,
            bg=AppConfig.COLORS['window_bg'],
            fg='#FF9800',
            font=AppConfig.FONTS['button']
        ).pack(anchor='w', pady=(0, 5))

        # 新增階段按鈕
        add_stage_btn = tk.Button(
            info_frame,
            text='新增進度階段',
            command=lambda: self._on_add_progress_stage(case),
            bg='#4CAF50',
            fg='white',
            font=AppConfig.FONTS['button'],  # 使用按鈕字體大小
            width=15,
            height=1
        )
        add_stage_btn.pack(anchor='w', pady=5)

        # 右側進度階段顯示
        progress_bar_frame = tk.Frame(
            self.progress_display,
            bg=AppConfig.COLORS['window_bg']
        )
        progress_bar_frame.pack(side='right', expand=True, fill='x', padx=20)

        # 只顯示實際存在的進度階段
        stages_to_show = list(case.progress_stages.keys()) if case.progress_stages else []

        if not stages_to_show:
            tk.Label(
                progress_bar_frame,
                text="尚無進度記錄",
                bg=AppConfig.COLORS['window_bg'],
                fg=AppConfig.COLORS['text_color'],
                font=AppConfig.FONTS['text']
            ).pack(expand=True)
            return

        # 按日期排序階段
        sorted_stages = sorted(case.progress_stages.items(), key=lambda x: x[1] if x[1] else '9999-12-31')

        for i, (stage, date) in enumerate(sorted_stages):
            # 每個階段的容器
            stage_container = tk.Frame(
                progress_bar_frame,
                bg=AppConfig.COLORS['window_bg']
            )
            stage_container.pack(side='left', expand=True)

            # 階段方框
            circle_frame = tk.Frame(
                stage_container,
                bg=AppConfig.COLORS['window_bg']
            )
            circle_frame.pack()

            # 判斷階段狀態和顏色
            is_current = (stage == case.progress)
            bg_color, fg_color = self._get_stage_color_by_date(date, is_current)

            # 階段文字顯示
            stage_text = stage[:4] if len(stage) > 4 else stage

            if len(stage_text) <= 2:
                box_width = 6
                font_size = 10
            elif len(stage_text) == 3:
                box_width = 8
                font_size = 10
            else:
                box_width = 10
                font_size = 10

            # 建立可點擊的階段標籤
            stage_label = tk.Label(
                circle_frame,
                text=stage_text,
                bg=bg_color,
                fg=fg_color,
                font=('Microsoft JhengHei', font_size, 'bold'),
                width=box_width,
                height=2,
                relief='solid',
                borderwidth=0,
                cursor='hand2'
            )
            stage_label.pack(pady=2)

            # 綁定點擊和右鍵事件
            stage_label.bind('<Button-1>', lambda e, s=stage, c=case: self._on_stage_click(s, c))
            stage_label.bind('<Button-3>', lambda e, s=stage, c=case: self._on_stage_right_click(e, s, c))

            # 儲存小部件參考
            self.progress_widgets[stage] = stage_label

            # 顯示日期
            if date:
                date_label = tk.Label(
                    circle_frame,
                    text=date,
                    bg=AppConfig.COLORS['window_bg'],
                    fg="#FFFFFF",
                    font=('Microsoft JhengHei', 10)
                )
                date_label.pack(pady=(3, 0))

            # 連接線
            if i < len(sorted_stages) - 1:
                line_frame = tk.Frame(
                    progress_bar_frame,
                    bg='#2196F3',
                    height=1,
                    width=25
                )
                line_frame.pack(side='left', pady=5)

    def _on_upload_data(self):
        """上傳資料事件"""
        # 檢查是否選擇了案件
        selection = self.tree.selection()
        if not selection:
            UnifiedMessageDialog.show_warning(self.window,  "請先選擇一個案件")
            return

        if not self.case_controller:
            UnifiedMessageDialog.show_warning(self.window,  "案件控制器未初始化")
            return

        try:
            # 取得選中的案件
            item = selection[0]
            tags = self.tree.item(item, 'tags')
            case_index = None

            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case = self.case_data[case_index]

                # 檢查案件是否有資料夾
                case_folder = self.case_controller.get_case_folder_path(case.case_id)
                if not case_folder or not os.path.exists(case_folder):
                    UnifiedMessageDialog.show_error(self.window,  f"找不到案件 {case.client} 的資料夾，無法上傳檔案")
                    return

                # 顯示上傳對話框
                from views.upload_file_dialog import UploadFileDialog

                def on_upload_complete():
                    """上傳完成後的回調"""
                    print("檔案上傳完成")

                UploadFileDialog.show_upload_dialog(
                    self.window,
                    case,
                    self.case_controller.folder_manager,
                    on_upload_complete
                )
            else:
                print(f"無法取得有效的案件索引：tags={tags}")
                UnifiedMessageDialog.show_error(self.window,  "無法取得選中的案件資訊")

        except Exception as e:
            print(f"開啟上傳對話框失敗: {e}")
            UnifiedMessageDialog.show_error(self.window,  f"無法開啟上傳對話框：{str(e)}")

    def _on_stage_click(self, stage_name: str, case: CaseData):
        """階段點擊事件 - 開啟階段資料夾"""
        try:
            stage_folder_path = self.case_controller.get_case_stage_folder_path(case.case_id, stage_name)
            if stage_folder_path and os.path.exists(stage_folder_path):
                os.startfile(stage_folder_path)  # Windows
                print(f"開啟階段資料夾: {stage_folder_path}")
            else:
                UnifiedMessageDialog.show_warning(self.window,  f"找不到階段「{stage_name}」的資料夾")

        except Exception as e:
            print(f"開啟階段資料夾失敗: {e}")
            UnifiedMessageDialog.show_error(self.window,  "無法開啟階段資料夾")

    def _on_stage_right_click(self, event, stage_name: str, case: CaseData):
        """階段右鍵事件 - 顯示階段操作選單"""
        try:
            # 建立右鍵選單
            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(
                label="編輯階段",
                command=lambda: self._on_edit_progress_stage(case, stage_name)
            )

            # 所有階段都可以移除
            context_menu.add_command(
                label="移除階段",
                command=lambda: self._on_remove_progress_stage(case, stage_name)
            )

            context_menu.add_separator()
            context_menu.add_command(
                label="開啟資料夾",
                command=lambda: self._on_stage_click(stage_name, case)
            )

            # 顯示選單
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

        except Exception as e:
            print(f"顯示階段右鍵選單失敗: {e}")

    def _on_add_progress_stage(self, case: CaseData):
        """新增進度階段"""
        from views.simple_progress_edit_dialog import SimpleProgressEditDialog

        def save_new_stage(result):
            try:
                success = self.case_controller.add_case_progress_stage(
                    case.case_id,
                    result['stage_name'],
                    result['stage_date']
                )
                if success:
                    self._load_cases()  # 重新載入資料
                    # 重新選擇該案件以更新顯示
                    self._reselect_case(case.case_id)
                    UnifiedMessageDialog.show_success(self.window,  f"已新增進度階段「{result['stage_name']}」")
                return success
            except Exception as e:
                UnifiedMessageDialog.show_error(self.window,  f"新增階段失敗：{str(e)}")
                return False

        SimpleProgressEditDialog.show_add_dialog(self.window, case, save_new_stage)

    def _on_edit_progress_stage(self, case: CaseData, stage_name: str):
        """編輯進度階段"""
        from views.simple_progress_edit_dialog import SimpleProgressEditDialog

        stage_date = case.progress_stages.get(stage_name, '')

        def save_edited_stage(result):
            try:
                success = self.case_controller.update_case_progress_stage(
                    case.case_id,
                    result['stage_name'],
                    result['stage_date']
                )
                if success:
                    self._load_cases()
                    self._reselect_case(case.case_id)
                    UnifiedMessageDialog.show_success(self.window,  f"已更新進度階段「{result['stage_name']}」")
                return success
            except Exception as e:
                UnifiedMessageDialog.show_error(self.window,  f"更新階段失敗：{str(e)}")
                return False

        SimpleProgressEditDialog.show_edit_dialog(
            self.window, case, stage_name, stage_date, save_edited_stage
        )

    def _on_remove_progress_stage(self, case: CaseData, stage_name: str):
        """移除進度階段（含刪除確認對話框）"""
        from views.dialogs import ConfirmDialog
        import os
        from tkinter import messagebox

        # 檢查是否有對應的資料夾
        stage_folder_path = self.case_controller.get_case_stage_folder_path(case.case_id, stage_name)
        folder_exists = stage_folder_path and os.path.exists(stage_folder_path)

        # 檢查資料夾是否有檔案
        has_files = False
        if folder_exists:
            try:
                files_in_folder = os.listdir(stage_folder_path)
                has_files = len(files_in_folder) > 0
            except:
                has_files = False

        # 建立確認訊息
        if folder_exists and has_files:
            confirm_message = (
                f"確定要移除階段「{stage_name}」嗎？\n\n"
                f"⚠️ 警告：此操作將同時刪除該階段的資料夾及其內的所有檔案！\n"
                f"資料夾路徑：{stage_folder_path}\n\n"
                f"此操作無法復原，請確認是否繼續？"
            )
        elif folder_exists:
            confirm_message = (
                f"確定要移除階段「{stage_name}」嗎？\n\n"
                f"此操作將同時刪除該階段的空資料夾。"
            )
        else:
            confirm_message = (
                f"確定要移除階段「{stage_name}」嗎？\n"
                f"此操作將移除該階段的記錄。"
            )

        if ConfirmDialog.ask(
            self.window,
            "確認刪除階段",
            confirm_message
        ):
            try:
                success = self.case_controller.remove_case_progress_stage(case.case_id, stage_name)
                if success:
                    self._load_cases()
                    self._reselect_case(case.case_id)

                    if folder_exists:
                        UnifiedMessageDialog.show_success(self.window,  f"已移除進度階段「{stage_name}」\n階段資料夾已同時刪除")
                    else:
                        UnifiedMessageDialog.show_success(self.window,  f"已移除進度階段「{stage_name}」")
                else:
                    UnifiedMessageDialog.show_error(self.window,  "無法移除當前進度階段")
            except Exception as e:
                UnifiedMessageDialog.show_error(self.window,  f"移除階段失敗：{str(e)}")

    def _reselect_case(self, case_id: str):
        """重新選擇指定的案件"""
        try:
            for i, case in enumerate(self.case_data):
                if case.case_id == case_id:
                    # 找到對應的樹狀圖項目
                    for item in self.tree.get_children():
                        tags = self.tree.item(item, 'tags')
                        for tag in tags:
                            if tag == f'index_{i}':
                                self.tree.selection_set(item)
                                self.tree.focus(item)
                                return
                    break
        except Exception as e:
            print(f"重新選擇案件失敗: {e}")

    def _on_add_case(self):
        """新增案件事件"""
        if not self.case_controller:
            UnifiedMessageDialog.show_warning(self.window,  "案件控制器未初始化")
            return

        from views.case_form import CaseFormDialog

        def save_new_case(case_data, mode):
            try:
                print(f"開始新增案件: {case_data.client}")
                case_data.case_id = self.case_controller.generate_case_id()
                print(f"產生案件編號: {case_data.case_id}")

                success = self.case_controller.add_case(case_data)

                if success:
                    print(f"案件新增成功，開始重新載入資料")
                    self.case_controller.load_cases()
                    self._load_cases()
                    print(f"資料重新載入完成，當前案件數量: {len(self.case_data)}")

                    folder_path = self.case_controller.get_case_folder_path(case_data.case_id)

                    # 使用統一的顯示格式
                    case_display_name = AppConfig.format_case_display_name(case_data)

                    if folder_path:
                        message = f"案件 {case_display_name} 新增成功！\n\n已建立資料夾結構：\n{folder_path}"
                    else:
                        message = f"案件 {case_display_name} 新增成功！\n\n注意：資料夾結構建立失敗，請手動建立。"

                    self.window.after(100, lambda: UnifiedMessageDialog.show_success(self.window,  message))
                else:
                    print(f"案件新增失敗")
                    UnifiedMessageDialog.show_error(self.window,  "案件新增失敗！")

                return success

            except Exception as e:
                print(f"新增案件回調發生錯誤: {e}")
                UnifiedMessageDialog.show_error(self.window,  f"新增案件時發生錯誤：{str(e)}")
                return False

        try:
            CaseFormDialog.show_add_dialog(self.window, save_new_case)
        except Exception as e:
            print(f"開啟新增案件對話框失敗: {e}")
            UnifiedMessageDialog.show_error(self.window,  f"無法開啟新增案件對話框：{str(e)}")

    def _on_export_excel(self):
        """匯出Excel事件"""
        if not self.case_controller:
            UnifiedMessageDialog.show_warning(self.window,  "案件控制器未初始化")
            return

        if not self.case_data:
            UnifiedMessageDialog.show_warning(self.window,  "沒有資料可以匯出")
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
                    UnifiedMessageDialog.show_success(self.window,  f"資料已匯出到：\n{file_path}")
                else:
                    UnifiedMessageDialog.show_error(self.window,  "資料匯出失敗！")
            except Exception as e:
                UnifiedMessageDialog.show_error(self.window,  f"匯出過程發生錯誤：{str(e)}")

    def _on_item_double_click(self, event):
        """項目雙擊事件 - 編輯案件"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]
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

                        # 使用統一的顯示格式
                        case_display_name = AppConfig.format_case_display_name(case_data)
                        self.window.after(100, lambda: UnifiedMessageDialog.show_success(self.window,  f"案件 {case_display_name} 更新成功！"))
                    else:
                        UnifiedMessageDialog.show_error(self.window,  "案件更新失敗！")
                    return success

                CaseFormDialog.show_edit_dialog(self.window, case, save_edited_case)
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except (ValueError, IndexError) as e:
            print(f"取得案件索引失敗: {e}")
            UnifiedMessageDialog.show_error(self.window,  "無法開啟案件編輯")

    def _on_item_right_click(self, event):
        """項目右鍵事件 - 顯示案件操作選單"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)

            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(label="編輯案件", command=lambda: self._on_item_double_click(None))
            context_menu.add_command(label="刪除案件", command=self._on_delete_case)
            context_menu.add_separator()
            context_menu.add_command(label="開啟當事人資料夾", command=self._on_open_case_folder)

            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def _on_delete_case(self):
        """刪除案件（含資料夾刪除確認）"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]
            tags = self.tree.item(item, 'tags')
            case_index = None

            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case = self.case_data[case_index]

                # 取得案件資料夾資訊
                folder_info = self.case_controller.get_case_folder_info(case.case_id)

                # 使用統一的顯示格式
                case_display_name = AppConfig.format_case_display_name(case)

                # 建立確認訊息
                confirm_message = f"確定要刪除案件 {case_display_name} 嗎？\n\n"

                if folder_info['exists'] and folder_info['has_files']:
                    confirm_message += (
                        f"此操作無法復原，請確認是否繼續？"
                    )
                elif folder_info['exists']:
                    confirm_message += (
                        f"此操作將同時刪除該案件的空資料夾。\n"
                        f"資料夾路徑：{folder_info['path']}"
                    )
                else:
                    confirm_message += "此操作將移除該案件的記錄。"

                from views.dialogs import ConfirmDialog
                if ConfirmDialog.ask(
                    self.window,
                    "確認刪除案件",
                    confirm_message
                ):
                    try:
                        success = self.case_controller.delete_case(case.case_id, delete_folder=True)
                        if success:
                            self._load_cases()

                            if folder_info['exists']:
                                UnifiedMessageDialog.show_success(self.window,  f"案件 {case_display_name} 已刪除\n案件資料夾已同時刪除")
                            else:
                                UnifiedMessageDialog.show_success(self.window,  f"案件 {case_display_name} 已刪除")
                        else:
                            UnifiedMessageDialog.show_error(self.window,  "案件刪除失敗")
                    except Exception as e:
                        UnifiedMessageDialog.show_error(self.window,  f"刪除案件失敗：{str(e)}")
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except (ValueError, IndexError) as e:
            print(f"刪除案件失敗: {e}")
            UnifiedMessageDialog.show_error(self.window,  "無法刪除案件")

    def _on_open_case_folder(self):
        """開啟案件資料夾"""
        selection = self.tree.selection()
        if not selection:
            return

        try:
            item = selection[0]
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
                    UnifiedMessageDialog.show_warning(self.window,  "找不到案件資料夾")
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except Exception as e:
            print(f"開啟資料夾失敗: {e}")
            UnifiedMessageDialog.show_error(self.window,  "無法開啟案件資料夾")

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
        # 先隱藏視窗
        self.window.withdraw()

        # 通知父視窗
        if self.parent and hasattr(self.parent, 'master'):
            # 如果父視窗是 Tkinter 視窗，直接調用其方法
            parent_window = self.parent.master if hasattr(self.parent, 'master') else self.parent
            if hasattr(parent_window, '_on_overview_close'):
                parent_window._on_overview_close()

        # 銷毀視窗
        self.window.destroy()

    def show(self):
        """顯示視窗"""
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()  # 強制取得焦點
    def hide(self):
        """隱藏視窗"""
        self.window.withdraw()