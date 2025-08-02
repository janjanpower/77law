#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import List

from config.settings import AppConfig
from models.case_model import CaseData
from views.import_data_dialog import ImportDataDialog
from views.date_reminder_widget import DateReminderWidget
from views.case_transfer_dialog import CaseTransferDialog
from utils.event_manager import event_manager, EventType

# 🔥 使用安全導入方式，避免導入錯誤
try:
    from views.dialogs import UnifiedMessageDialog, ConfirmDialog, UnifiedConfirmDialog
except ImportError as e:
    print(f"警告：無法導入對話框模組 - {e}")
    # 使用標準 messagebox 作為備用
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

    class ConfirmDialog:
        @staticmethod
        def ask(parent, title="確認", message="確定要執行此操作嗎？"):
            return messagebox.askyesno(title, message)

    class UnifiedConfirmDialog:
        @staticmethod
        def ask_stage_update(parent, stage_name):
            return messagebox.askyesno(
                "確認更新",
                f"階段「{stage_name}」已存在，是否要更新日期和備註？"
            )

class CaseOverviewWindow:
    """案件總覽視窗"""
    def __init__(self, parent=None, case_controller=None):
        """初始化案件總覽視窗 - 🔥 確保完整的初始化順序"""
        try:
            self.parent = parent
            self.case_controller = case_controller
            self.visible_fields = AppConfig.OVERVIEW_FIELDS.copy()
            self.case_data: List[CaseData] = []
            self.filtered_case_data = []  # 🔥 確保初始化
            self.drag_data = {"x": 0, "y": 0}
            self.progress_widgets = {}

            # 初始化搜尋相關變數
            self.search_var = tk.StringVar()
            self.placeholder_active = True
            self.placeholder_text = "搜尋案件..."

            # 建立視窗
            self.window = tk.Toplevel(parent) if parent else tk.Tk()
            self._setup_window()
            self._setup_styles()
            self._create_layout()

            # 🔥 重要：確保所有 UI 組件都已創建後再載入資料
            if self.case_controller:
                # 延遲載入以確保 UI 完全初始化
                self.window.after(100, self._load_cases)

            # 🔥 確保日期提醒控件已正確初始化
            if not hasattr(self, 'date_reminder_widget'):
                self.date_reminder_widget = None

            # 追蹤當前選中的案件
            self.current_selected_case_id = None
            self.current_selected_item = None

            # 訂閱案件事件
            self._subscribe_to_events()

            # 確保視窗顯示
            self.window.update()
            self.window.deiconify()

            # 關閉狀態標記
            self._is_closing = False
            self._is_destroyed = False

            print("CaseOverviewWindow 初始化完成")

        except Exception as e:
            print(f"CaseOverviewWindow 初始化失敗: {e}")
            import traceback
            traceback.print_exc()


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

        # 🔥 修改：搜尋區域 - 調整高度以容納日期提醒控件
        self.search_frame = tk.Frame(
            self.content_frame,
            bg=AppConfig.COLORS['window_bg'],
            height=60  # 增加高度
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
            height=50
        )
        self.field_control_frame.pack(fill='x')
        self.field_control_frame.pack_propagate(False)

    def _subscribe_to_events(self):
        """訂閱案件事件 - 🔥 修正：確保跑馬燈更新邏輯正確"""
        try:
            # 訂閱案件相關事件
            event_manager.subscribe(EventType.CASE_ADDED, self._on_case_data_changed)
            event_manager.subscribe(EventType.CASE_UPDATED, self._on_case_data_changed)
            event_manager.subscribe(EventType.CASE_DELETED, self._on_case_data_changed)
            event_manager.subscribe(EventType.CASES_RELOADED, self._on_cases_reloaded)

            print("案件總覽視窗已訂閱案件事件")

        except Exception as e:
            print(f"訂閱案件事件失敗: {e}")

    def _on_case_data_changed(self, event_data):
        """案件資料變更事件處理 - 🔥 修正：只更新必要的UI元素"""
        try:
            print("案件資料發生變更，重新載入...")

            # 重新載入案件資料
            self._load_cases()

            # 🔥 重要：日期提醒控件會透過自己的事件訂閱機制自動更新
            # 不需要在這裡手動更新

        except Exception as e:
            print(f"處理案件資料變更事件失敗: {e}")

    def _on_cases_reloaded(self, event_data):
        """案件重新載入事件處理 - 🔥 修正：保持搜尋狀態"""
        try:
            print("收到案件重新載入事件")

            # 保存當前搜尋狀態
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            was_placeholder_active = getattr(self, 'placeholder_active', True)

            # 重新載入案件資料
            self._load_cases()

            # 恢復搜尋狀態
            if current_search and not was_placeholder_active:
                self.search_var.set(current_search)
                self.placeholder_active = False
                self._perform_search()
            else:
                self._set_placeholder()

            # 🔥 重要：日期提醒控件已透過自己的事件處理機制更新

        except Exception as e:
            print(f"處理案件重新載入事件失敗: {e}")

    def _on_case_updated_event(self, event_data):
        """🔥 修正：處理案件更新事件 - 增加關閉狀態檢查"""
        if self._is_closing or self._is_destroyed:
            return

        try:
            if not event_data:
                return

            case_id = event_data.get('case_id')
            print(f"CaseOverview 收到案件更新事件: {case_id}")

            # 檢查視窗是否仍然存在
            if not hasattr(self, 'window') or not self.window or not self.window.winfo_exists():
                return

            # 重新選擇當前案件以刷新顯示
            if hasattr(self, 'current_selected_case_id') and self.current_selected_case_id == case_id:
                self._reselect_case(case_id)

        except Exception as e:
            print(f"處理案件更新事件失敗: {e}")

    def _on_stage_updated_event(self, event_data):
        """🔥 修正：處理階段更新事件 - 增加關閉狀態檢查"""
        if self._is_closing or self._is_destroyed:
            return

        try:
            if not event_data:
                return

            case_id = event_data.get('case_id')
            print(f"CaseOverview 收到階段更新事件: {case_id}")

            # 檢查視窗是否仍然存在
            if not hasattr(self, 'window') or not self.window or not self.window.winfo_exists():
                return

            # 如果是當前選中的案件，刷新進度顯示
            if hasattr(self, 'current_selected_case_id') and self.current_selected_case_id == case_id:
                self._reselect_case(case_id)

        except Exception as e:
            print(f"處理階段更新事件失敗: {e}")

    def _create_search_bar(self):
        """建立搜尋條 - 包含跑馬燈式日期提醒和 placeholder 功能"""
        # 左側搜尋區域
        left_search_frame = tk.Frame(self.search_frame, bg=AppConfig.COLORS['window_bg'])
        left_search_frame.pack(side='left', fill='x', expand=True)

        # 搜尋標籤
        search_label = tk.Label(
            left_search_frame,
            text="搜尋：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        search_label.pack(side='left', padx=(10, 0))

        # 🔥 修改：搜尋輸入框 - 添加 placeholder 功能
        self.search_entry = tk.Entry(
            left_search_frame,
            textvariable=self.search_var,
            bg='white',
            fg='black',
            font=AppConfig.FONTS['text'],
            width=20,
        )
        self.search_entry.pack(side='left', padx=0)

        # 🔥 新增：placeholder 相關設定
        self.placeholder_text = "搜尋案件欄位資料"
        self.placeholder_active = True

        # 設定初始 placeholder
        self._set_placeholder()

        # 🔥 修改：綁定搜尋事件 - 處理 placeholder
        self.search_var.trace_add('write', self._on_search_changed_with_placeholder)
        self.search_entry.bind('<FocusIn>', self._on_search_focus_in)
        self.search_entry.bind('<FocusOut>', self._on_search_focus_out)
        self.search_entry.bind('<Return>', self._on_search_enter)

        # 清除搜尋按鈕
        clear_btn = tk.Button(
            left_search_frame,
            text="清除",
            command=self._clear_search,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['text'],
            width=7
        )
        clear_btn.pack(side='left', padx=(10, 0))

        # 搜尋結果統計
        self.search_result_label = tk.Label(
            left_search_frame,
            text="",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['text']
        )
        self.search_result_label.pack(side='left', padx=(10, 0))

        # 右側跑馬燈式日期提醒控件 - 🔥 修正版本
        try:
            from views.date_reminder_widget import DateReminderWidget

            # 創建日期提醒控件
            self.date_reminder_widget = DateReminderWidget(
                self.search_frame,
                case_data=self.case_data,
                on_case_select=self._on_reminder_case_select
            )

            # 🔥 重要：設定案件控制器引用
            if hasattr(self, 'case_controller') and self.case_controller:
                self.date_reminder_widget.set_case_controller(self.case_controller)

            print("日期提醒控件已成功創建並設定")

        except ImportError as e:
            print(f"無法載入日期提醒控件: {e}")
            self.date_reminder_widget = None
        except Exception as e:
            print(f"創建日期提醒控件失敗: {e}")
            self.date_reminder_widget = None

    def _set_placeholder(self):
        """設定 placeholder"""
        if self.placeholder_active:
            self.search_entry.config(fg="#414141")
            self.search_var.set(self.placeholder_text)

    def _clear_placeholder(self):
        """清除 placeholder"""
        if self.placeholder_active:
            self.placeholder_active = False
            self.search_var.set("")
            self.search_entry.config(fg='black')

    def _restore_placeholder(self):
        """恢復 placeholder"""
        if not self.search_var.get().strip():
            self.placeholder_active = True
            self._set_placeholder()

    def _on_search_focus_in(self, event):
        """搜尋框獲得焦點時"""
        self._clear_placeholder()

    def _on_search_focus_out(self, event):
        """搜尋框失去焦點時"""
        self._restore_placeholder()

    def _on_search_changed_with_placeholder(self, *args):
        """搜尋內容變更時的處理（包含 placeholder 邏輯）"""
        # 如果是 placeholder 狀態，不執行搜尋
        if self.placeholder_active:
            return

        # 執行原有的搜尋邏輯
        if hasattr(self, '_search_after_id'):
            self.window.after_cancel(self._search_after_id)

        self._search_after_id = self.window.after(300, self._perform_search)


    def _on_reminder_case_select(self, case):
        """日期提醒控件的案件選擇回調 - 🔥 修正：處理搜尋狀態下的案件選擇"""
        try:
            print(f"日期提醒回調：選擇案件 {case.case_id} - {case.client}")

            # 🔥 修改：先檢查該案件是否在當前過濾結果中
            case_in_filtered_results = any(c.case_id == case.case_id for c in self.filtered_case_data)

            if not case_in_filtered_results:
                # 🔥 如果選中的案件不在當前搜尋結果中，自動清除搜尋
                print(f"選中案件 {case.case_id} 不在當前搜尋結果中，自動清除搜尋")
                self._clear_search()

            # 通知日期提醒控件記住這個選擇
            if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                self.date_reminder_widget.set_selected_case(case.case_id)

            # 重新整理樹狀圖（確保包含選中的案件）
            self._refresh_filtered_tree_data()

            # 找到並選擇對應的案件
            case_index = None
            for i, current_case in enumerate(self.case_data):
                if current_case.case_id == case.case_id:
                    case_index = i
                    break

            if case_index is not None:
                # 在樹狀圖中找到並選擇對應項目
                for item in self.tree.get_children():
                    tags = self.tree.item(item, 'tags')
                    for tag in tags:
                        if tag == f'index_{case_index}':
                            self.tree.selection_set(item)
                            self.tree.focus(item)
                            self.tree.see(item)

                            # 記住當前選中的案件
                            self.current_selected_case_id = case.case_id
                            self.current_selected_item = item

                            print(f"已在樹狀圖中選中案件: {case.case_id}")
                            return

            print(f"警告：無法在樹狀圖中找到案件 {case.case_id}")

        except Exception as e:
            print(f"處理日期提醒案件選擇失敗: {e}")
            import traceback
            traceback.print_exc()

    def _select_and_maintain_case_selection(self, case_index, case_id):
        """🔥 新增：選擇案件並維持選擇狀態"""
        try:
            # 在樹狀圖中找到對應項目並選擇
            selected = False
            for item in self.tree.get_children():
                tags = self.tree.item(item, 'tags')
                for tag in tags:
                    if tag == f'index_{case_index}':
                        # 清除現有選擇
                        self.tree.selection_remove(self.tree.selection())

                        # 選擇並聚焦到該項目
                        self.tree.selection_set(item)
                        self.tree.focus(item)
                        self.tree.see(item)  # 確保項目可見

                        # 🔥 重要：強制觸發選擇事件以更新進度顯示
                        self.tree.event_generate('<<TreeviewSelect>>')

                        # 🔥 新增：記住當前選中的案件，用於維持選擇
                        self.current_selected_case_id = case_id
                        self.current_selected_item = item

                        print(f"已選擇並維持案件索引: {case_index}, ID: {case_id}")
                        selected = True
                        break
                if selected:
                    break

            if not selected:
                print(f"在樹狀圖中未找到案件索引: {case_index}")

        except Exception as e:
            print(f"選擇並維持案件選擇失敗: {e}")

    def _select_case_in_tree(self, case_index):
        """在樹狀圖中選擇案件"""
        try:
            # 在樹狀圖中找到對應項目並選擇
            for item in self.tree.get_children():
                tags = self.tree.item(item, 'tags')
                for tag in tags:
                    if tag == f'index_{case_index}':
                        # 清除現有選擇
                        self.tree.selection_remove(self.tree.selection())

                        # 選擇並聚焦到該項目
                        self.tree.selection_set(item)
                        self.tree.focus(item)
                        self.tree.see(item)  # 確保項目可見

                        # 🔥 修正：強制觸發選擇事件
                        self.tree.event_generate('<<TreeviewSelect>>')

                        print(f"已選擇案件索引: {case_index}")
                        return

            print(f"在樹狀圖中未找到案件索引: {case_index}")

        except Exception as e:
            print(f"在樹狀圖中選擇案件失敗: {e}")

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
        """執行搜尋 - 🔥 修正：安全更新日期提醒控件"""
        try:
            search_text = self.search_var.get().strip()

            if not search_text or self.placeholder_active:
                # 沒有搜尋條件，顯示所有案件
                self.filtered_case_data = self.case_data.copy()
                self.search_result_label.config(text="")
            else:
                # 執行搜尋
                self.filtered_case_data = []
                search_text_lower = search_text.lower()

                for case in self.case_data:
                    # 搜尋案件編號
                    if search_text in case.case_id.lower():
                        self.filtered_case_data.append(case)
                        continue

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

                if self._case_matches_search(case, search_text_lower):
                        self.filtered_case_data.append(case)

            # 更新搜尋結果顯示
            found_count = len(self.filtered_case_data)
            total_count = len(self.case_data)
            self.search_result_label.config(text=f"找到 {found_count}/{total_count} 個案件")


            # 更新樹狀圖
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
        """清除搜尋 - 🔥 修正：正確重置搜尋狀態"""
        try:
            # 重置搜尋輸入框
            self.placeholder_active = False
            self.search_var.set("")
            self.search_entry.config(fg='black')
            self.search_entry.focus()

            # 重置過濾資料為所有案件
            self.filtered_case_data = self.case_data.copy()

            # 🔥 修正：清空搜尋結果顯示
            self.search_result_label.config(text="")

            # 重新整理樹狀圖
            self._refresh_filtered_tree_data()

        except Exception as e:
            print(f"清除搜尋失敗: {e}")


    def _case_matches_search(self, case, search_text_lower):
        """檢查案件是否符合搜尋條件 - 🔥 修正：移除 notes 欄位搜尋"""
        try:
            # 在當事人、案件類型、進度等欄位中搜尋
            searchable_fields = [
                case.client.lower(),
                case.case_type.lower(),
                case.progress.lower(),
                case.case_id.lower()
            ]

            # 安全處理可選欄位
            optional_fields = [
                ('lawyer', case.lawyer),
                ('legal_affairs', case.legal_affairs),
                ('case_reason', case.case_reason),
                ('case_number', case.case_number),
                ('opposing_party', case.opposing_party),
                ('court', case.court),
                ('division', case.division)
            ]

            for field_name, field_value in optional_fields:
                if field_value:
                    searchable_fields.append(field_value.lower())

            # 🔥 新增：搜尋進度備註（如果需要的話）
            if hasattr(case, 'progress_notes') and case.progress_notes:
                for note in case.progress_notes.values():
                    if note:
                        searchable_fields.append(note.lower())

            # 🔥 移除：case.notes.lower() if case.notes else "" - 這個屬性不存在

            return any(search_text_lower in field for field in searchable_fields)

        except Exception as e:
            print(f"搜尋案件失敗: {case.case_id}, error: {e}")
            return False


    def _refresh_filtered_tree_data(self):
        """重新整理樹狀圖資料（使用過濾後的資料）- 🔥 修正：保持選擇狀態"""
        try:
            # 使用過濾後的資料
            data_to_display = self.filtered_case_data if hasattr(self, 'filtered_case_data') else self.case_data

            print(f"開始重新整理樹狀圖，顯示案件數量: {len(data_to_display)}")

            # 🔥 記住當前選中的案件ID（如果有的話）
            previous_selected_case_id = getattr(self, 'current_selected_case_id', None)

            # 清空現有項目
            for item in self.tree.get_children():
                self.tree.delete(item)

            # 取得當前顯示的欄位（按順序）
            current_columns = list(self.tree['columns'])
            print(f"當前樹狀圖欄位: {current_columns}")

            # 填入過濾後的資料
            item_to_select = None
            for display_index, case in enumerate(data_to_display):
                values = []

                # 重要：使用統一的欄位值獲取方法
                for col_id in current_columns:
                    value = self._get_case_field_value(case, col_id)
                    values.append(value)

                tag = 'evenrow' if display_index % 2 == 0 else 'oddrow'
                item_id = self.tree.insert('', 'end', values=values, tags=(tag,))

                # 保存原始案件索引以便後續操作
                try:
                    original_index = self.case_data.index(case)
                    existing_tags = self.tree.item(item_id, 'tags')
                    new_tags = list(existing_tags) + [f'index_{original_index}']
                    self.tree.item(item_id, tags=new_tags)

                    # 🔥 檢查是否為之前選中的案件
                    if previous_selected_case_id and case.case_id == previous_selected_case_id:
                        item_to_select = item_id

                except ValueError:
                    print(f"警告：無法找到案件 {case.case_id} 的原始索引")
                    existing_tags = self.tree.item(item_id, 'tags')
                    new_tags = list(existing_tags) + [f'index_{display_index}']
                    self.tree.item(item_id, tags=new_tags)

            # 🔥 重新選擇之前選中的案件（如果存在）
            if item_to_select:
                try:
                    self.tree.selection_set(item_to_select)
                    self.tree.focus(item_to_select)
                    self.tree.see(item_to_select)
                    print(f"已重新選擇案件: {previous_selected_case_id}")
                except Exception as e:
                    print(f"重新選擇案件失敗: {e}")

            print(f"樹狀圖重新整理完成，已載入 {len(data_to_display)} 筆資料")

        except Exception as e:
            print(f"重新整理過濾樹狀圖資料失敗: {e}")
            import traceback
            traceback.print_exc()

    def _restore_selection(self, item_to_select, case_id):
        """🔥 新增：恢復選擇狀態"""
        try:
            if item_to_select and self.tree.exists(item_to_select):
                # 選擇項目
                self.tree.selection_set(item_to_select)
                self.tree.focus(item_to_select)
                self.tree.see(item_to_select)

                # 觸發選擇事件
                self.tree.event_generate('<<TreeviewSelect>>')

                # 更新記錄
                self.current_selected_case_id = case_id
                self.current_selected_item = item_to_select

                print(f"已恢復選擇案件: {case_id}")
            else:
                print(f"無法恢復選擇，項目不存在: {item_to_select}")
        except Exception as e:
            print(f"恢復選擇失敗: {e}")

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

        # 🔥 新增：結案轉移按鈕（第三個按鈕）
        self.transfer_btn = self.create_button(
            self.toolbar_frame,
            '結案轉移',
            self._on_case_transfer,
            'Function'
        )
        self.transfer_btn.pack(side='left', padx=5)
        # 初始狀態為隱藏
        self.transfer_btn.pack_forget()

        self.import_btn = self.create_button(
            self.toolbar_frame,
            '匯入資料',
            self._on_import_data,
            'Function'
        )
        self.import_btn.pack(side='right', padx=(5, 10))

        # self.export_btn = self.create_button(
        #     self.toolbar_frame,
        #     '匯出案件資訊',
        #     self._on_export_excel,
        #     'Function'
        # )
        # self.export_btn.pack(side='left', padx=5)

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

    def _on_import_data(self):
        """匯入資料事件"""
        if not self.case_controller:
            UnifiedMessageDialog.show_warning(self.window, "案件控制器未初始化")
            return

        # 顯示匯入對話框
        ImportDataDialog.show_import_dialog(self.window, self.case_controller, self._on_import_complete)

    def _on_import_complete(self):
        """匯入完成後的回調"""
        print("Excel資料匯入完成，重新載入案件列表")
        self._load_cases()

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

        # 綁定事件 - 修正事件綁定順序
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        self.tree.bind('<Button-3>', self._on_item_right_click)
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # 編輯相關變數
        self.edit_item = None
        self.edit_entry = None
        self.is_editing = False  # 新增：編輯狀態標記


    def _on_tree_double_click(self, event):
        """樹狀圖雙擊事件 - 修正欄位識別"""
        # 如果正在編輯，先完成當前編輯
        if self.is_editing:
            self._finish_edit_case_id()
            return

        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if not item:
            return

        # 修正：根據實際欄位位置判斷是否為案件編號欄位
        current_columns = list(self.tree['columns'])
        if column == '#1' and current_columns and current_columns[0] == 'case_id':
            # 延遲執行編輯，確保事件處理完成
            self.window.after(10, lambda: self._start_edit_case_id(item, event))
        else:
            # 原有的編輯案件功能
            self._edit_selected_case(item)

    def _edit_selected_case(self, item):
        """編輯選中的案件（原有功能）- 確保不在編輯狀態時才執行"""
        if self.is_editing:
            return

        try:
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
                    success = self.case_controller.update_case(case_data)  # ✅ 正確：只傳入 case_data
                    if success:
                        self._load_cases()
                        case_display_name = AppConfig.format_case_display_name(case_data)
                        self.window.after(100, lambda: UnifiedMessageDialog.show_success(self.window, f"案件 {case_display_name} 更新成功！"))
                    else:
                        UnifiedMessageDialog.show_error(self.window, "案件更新失敗！")
                    return success

                CaseFormDialog.show_edit_dialog(self.window, case, save_edited_case)
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except (ValueError, IndexError) as e:
            print(f"編輯案件失敗: {e}")
            UnifiedMessageDialog.show_error(self.window, "無法開啟案件編輯")

    def _start_edit_case_id(self, item, event):
        """開始編輯案件編號 - 修正焦點問題"""
        try:
            # 設定編輯狀態
            self.is_editing = True

            # 如果已經在編輯其他項目，先完成編輯
            if self.edit_entry:
                self._cancel_edit_case_id()

            # 取得當前案件編號
            values = self.tree.item(item, 'values')
            if not values:
                self.is_editing = False
                return

            current_case_id = values[0]

            # 取得欄位位置和大小
            try:
                x, y, width, height = self.tree.bbox(item, '#1')
            except tk.TclError:
                # 如果無法取得bbox，使用預設位置
                self.is_editing = False
                return

            # 建立編輯輸入框
            self.edit_item = item
            self.edit_entry = tk.Entry(
                self.tree,
                font=AppConfig.FONTS['text'],
                justify='center',
                borderwidth=1,
                relief='solid'
            )

            # 設定位置和內容
            self.edit_entry.place(x=x, y=y, width=width, height=height)
            self.edit_entry.insert(0, current_case_id)
            self.edit_entry.select_range(0, tk.END)

            # 重要：延遲設定焦點，確保輸入框已經顯示
            self.window.after(50, self._set_edit_focus)

            # 綁定事件 - 修正事件處理
            self.edit_entry.bind('<Return>', self._on_edit_return)
            self.edit_entry.bind('<Escape>', self._on_edit_escape)
            self.edit_entry.bind('<FocusOut>', self._on_edit_focus_out)

            # 綁定點擊其他位置完成編輯
            self.tree.bind('<Button-1>', self._on_tree_click_while_editing, add='+')

        except Exception as e:
            print(f"開始編輯案件編號失敗: {e}")
            self.is_editing = False

    def _set_edit_focus(self):
        """設定編輯框焦點"""
        if self.edit_entry and self.edit_entry.winfo_exists():
            self.edit_entry.focus_force()
            self.edit_entry.icursor(tk.END)

    def _on_edit_return(self, event):
        """處理Enter鍵"""
        self._finish_edit_case_id()
        return 'break'  # 阻止事件繼續傳播

    def _on_edit_escape(self, event):
        """處理Escape鍵"""
        self._cancel_edit_case_id()
        return 'break'

    def _on_edit_focus_out(self, event):
        """處理失去焦點 - 延遲處理避免衝突"""
        if self.is_editing:
            # 延遲處理，給其他事件處理的時間
            self.window.after(100, self._check_and_finish_edit)

    def _on_tree_click_while_editing(self, event):
        """編輯時點擊樹狀圖其他位置"""
        if self.is_editing and self.edit_entry:
            # 檢查是否點擊在編輯框內
            try:
                edit_x = self.edit_entry.winfo_x()
                edit_y = self.edit_entry.winfo_y()
                edit_width = self.edit_entry.winfo_width()
                edit_height = self.edit_entry.winfo_height()

                if not (edit_x <= event.x <= edit_x + edit_width and
                    edit_y <= event.y <= edit_y + edit_height):
                    # 點擊在編輯框外，完成編輯
                    self._finish_edit_case_id()
            except:
                pass

    def _check_and_finish_edit(self):
        """檢查並完成編輯"""
        if self.is_editing and self.edit_entry:
            # 檢查焦點是否還在編輯框
            try:
                focused_widget = self.window.focus_get()
                if focused_widget != self.edit_entry:
                    self._finish_edit_case_id()
            except:
                self._finish_edit_case_id()

    def _finish_edit_case_id(self):
        """完成編輯案件編號 - 🔥 修正：添加必需的case_type參數"""
        if not self.edit_entry or not self.edit_item or not self.is_editing:
            return

        # 立即設定編輯狀態為False，避免重複執行
        self.is_editing = False

        try:
            new_case_id = self.edit_entry.get().strip().upper()

            # 取得原始案件編號和案件類型
            tags = self.tree.item(self.edit_item, 'tags')
            case_index = None
            for tag in tags:
                if tag.startswith('index_'):
                    case_index = int(tag.replace('index_', ''))
                    break

            if case_index is not None and case_index < len(self.case_data):
                case_data = self.case_data[case_index]
                old_case_id = case_data.case_id
                case_type = case_data.case_type  # 🔥 修正：取得案件類型

                # 如果沒有變更，直接結束編輯
                if new_case_id == old_case_id:
                    self._cleanup_edit()
                    return

                # 🔥 修正：傳入必需的case_type參數
                success, message = self.case_controller.update_case_id(old_case_id, case_type, new_case_id)

                # 先清理編輯組件
                self._cleanup_edit()

                # 再顯示結果訊息
                if success:
                    # 重新載入資料
                    self._load_cases()
                    # 重新選擇該案件
                    self._reselect_case_by_id(new_case_id)
                    UnifiedMessageDialog.show_success(
                        self.window,
                        f"案件編號更新成功：{old_case_id} → {new_case_id}"
                    )
                else:
                    UnifiedMessageDialog.show_error(
                        self.window,
                        f"案件編號更新失敗：{message}"
                    )
            else:
                self._cleanup_edit()
                UnifiedMessageDialog.show_error(self.window, "無法找到對應的案件資料")

        except Exception as e:
            print(f"完成編輯案件編號失敗: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup_edit()
            UnifiedMessageDialog.show_error(self.window, f"編輯失敗：{str(e)}")

    def _cancel_edit_case_id(self):
        """取消編輯案件編號"""
        self.is_editing = False
        self._cleanup_edit()

    def _cleanup_edit(self):
        """🔥 修正：清理編輯相關組件和事件 - 增加安全檢查"""
        try:
            # 解除樹狀圖點擊事件綁定
            if hasattr(self, 'tree') and self.tree:
                try:
                    self.tree.unbind('<Button-1>')
                except:
                    pass

            # 銷毀編輯輸入框
            if hasattr(self, 'edit_entry') and self.edit_entry:
                try:
                    self.edit_entry.destroy()
                except:
                    pass
                self.edit_entry = None

            # 清理編輯項目
            self.edit_item = None

        except Exception as e:
            print(f"清理編輯組件失敗: {e}")

    def _reselect_case_by_id(self, case_id: str):
        """根據案件編號重新選擇案件"""
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
                                # 確保項目可見
                                self.tree.see(item)
                                return
                    break
        except Exception as e:
            print(f"重新選擇案件失敗: {e}")

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
        """更新樹狀圖欄位 - 🔥 確保方法存在"""
        try:
            # 按照 order 順序排序可見欄位
            visible_fields = []
            for field_id, field_info in sorted(AppConfig.OVERVIEW_FIELDS.items(),
                                            key=lambda x: x[1]['order']):
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
        """建立欄位顯示控制 - 修正初始化邏輯"""
        control_title = tk.Label(
            self.field_control_frame,
            text="隱藏欄位：",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        )
        control_title.pack(side='left', padx=(10, 10))

        self.field_vars = {}

        # 按照 order 順序建立控制項
        for field_id, field_info in sorted(AppConfig.OVERVIEW_FIELDS.items(),
                                        key=lambda x: x[1]['order']):
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
        """切換欄位顯示狀態 - 🔥 修正：使用正確的方法名稱"""
        try:
            is_hidden = self.field_vars[field_id].get()

            # 更新可見狀態
            AppConfig.OVERVIEW_FIELDS[field_id]['visible'] = not is_hidden

            # 重新設定樹狀圖欄位
            self._update_tree_columns()

            # 🔥 重要：使用正確的方法名稱重新載入資料
            self._refresh_tree_data()

        except Exception as e:
            print(f"切換欄位顯示狀態失敗: {e}")

    def _load_cases(self):
        """載入案件資料 - 🔥 修正：只在這裡更新日期提醒控件"""
        if self.case_controller:
            try:
                self.case_data = self.case_controller.get_cases()
                self.filtered_case_data = self.case_data.copy()

                print(f"載入案件資料: {len(self.case_data)} 個案件")

                # 更新樹狀圖顯示
                self._refresh_tree_data()

                # 🔥 重要：只在載入案件時更新日期提醒控件
                # 日期提醒控件應該始終顯示所有案件的重要日期，不隨搜尋變動
                if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                    try:
                        self.date_reminder_widget.update_case_data(self.case_data)
                        print("已更新日期提醒控件資料（載入時）")
                    except Exception as e:
                        print(f"更新日期提醒控件失敗: {e}")

            except Exception as e:
                print(f"載入案件資料失敗: {e}")
                import traceback
                traceback.print_exc()
                self.case_data = []
                self.filtered_case_data = []
        else:
            print("案件控制器未初始化")
            self.case_data = []
            self.filtered_case_data = []

    def _refresh_tree_data(self):
        """重新整理樹狀圖資料（支援搜尋過濾）- 🔥 確保方法存在"""
        try:
            # 決定要顯示的資料：如果有過濾資料就用過濾資料，否則用全部資料
            data_to_display = getattr(self, 'filtered_case_data', self.case_data)

            print(f"開始重新整理樹狀圖，顯示案件數量: {len(data_to_display)} / 總數: {len(self.case_data)}")

            # 清空現有項目
            for item in self.tree.get_children():
                self.tree.delete(item)

            # 取得當前顯示的欄位（按順序）
            current_columns = list(self.tree['columns'])
            print(f"當前樹狀圖欄位: {current_columns}")

            # 遍歷要顯示的資料
            for display_index, case in enumerate(data_to_display):
                values = []

                # 重要：按照當前欄位順序填入資料
                for col_id in current_columns:
                    value = self._get_case_field_value(case, col_id)
                    values.append(value)

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

    def _get_case_field_value(self, case, field_id):
        """取得案件指定欄位的值 - 🔥 修正：移除不存在的 notes 屬性"""
        try:
            if field_id == 'case_id':
                return getattr(case, 'case_id', '')
            elif field_id == 'case_type':
                return getattr(case, 'case_type', '')
            elif field_id == 'client':
                return getattr(case, 'client', '')
            elif field_id == 'lawyer':
                return getattr(case, 'lawyer', '') or ''
            elif field_id == 'legal_affairs':
                return getattr(case, 'legal_affairs', '') or ''
            elif field_id == 'case_reason':
                return getattr(case, 'case_reason', '') or ''
            elif field_id == 'case_number':
                return getattr(case, 'case_number', '') or ''
            elif field_id == 'opposing_party':
                return getattr(case, 'opposing_party', '') or ''
            elif field_id == 'court':
                return getattr(case, 'court', '') or ''
            elif field_id == 'division':
                return getattr(case, 'division', '') or ''
            elif field_id == 'progress':
                return getattr(case, 'progress', '待處理')
            elif field_id == 'progress_date':
                return getattr(case, 'progress_date', '') or ''
            # 🔥 移除：elif field_id == 'notes': 這個欄位在 CaseData 中不存在
            # 🔥 新增：如果需要備註資訊，可以顯示進度備註的摘要
            elif field_id == 'progress_summary':
                # 如果需要顯示進度相關的備註摘要
                progress_notes = getattr(case, 'progress_notes', {})
                if progress_notes:
                    # 取最新的備註（可以根據需要調整邏輯）
                    latest_note = list(progress_notes.values())[-1] if progress_notes else ''
                    return latest_note[:20] + '...' if len(latest_note) > 20 else latest_note
                return ''
            else:
                # 處理未知欄位 - 安全返回空字串
                return getattr(case, field_id, '') if hasattr(case, field_id) else ''
        except Exception as e:
            print(f"取得欄位值失敗 - field_id: {field_id}, error: {e}")
            return ''


    def _setup_progress_visualization(self):
        """設定進度可視化區域"""
        progress_title = tk.Label(
            self.progress_frame,
            text="案件進度",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        )
        progress_title.pack(pady=5)

        self.progress_display = tk.Frame(
            self.progress_frame,
            bg=AppConfig.COLORS['window_bg']
        )
        self.progress_display.pack(fill='both', expand=True, padx=10)

    def _on_tree_select(self, event):
        """樹狀圖選擇事件 - 🔥 修改：添加結案轉移按鈕控制"""
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

                    # 🔥 新增：檢查是否顯示結案轉移按鈕
                    self._update_transfer_button_visibility(case)

                    # 🔥 新增：同步更新日期提醒控件的選擇狀態
                    if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                        self.date_reminder_widget.set_selected_case(case.case_id)

                    # 🔥 新增：記住當前選中的案件
                    self.current_selected_case_id = case.case_id
                    self.current_selected_item = item

                    self._display_case_progress(case)
                else:
                    print(f"無法取得有效的案件索引：tags={tags}")
                    # 🔥 清除選擇狀態和隱藏轉移按鈕
                    self._hide_transfer_button()
                    if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                        self.date_reminder_widget.clear_selection()
                    self.current_selected_case_id = None
                    self.current_selected_item = None

            except (ValueError, IndexError) as e:
                print(f"取得案件索引失敗: {e}")
                # 🔥 清除選擇狀態和隱藏轉移按鈕
                self._hide_transfer_button()
                if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                    self.date_reminder_widget.clear_selection()
                self.current_selected_case_id = None
                self.current_selected_item = None
        else:
            # 🔥 沒有選擇時清除狀態和隱藏轉移按鈕
            self._hide_transfer_button()
            if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                self.date_reminder_widget.clear_selection()
            self.current_selected_case_id = None
            self.current_selected_item = None

    def _update_transfer_button_visibility(self, case):
        """🔥 新增：更新結案轉移按鈕顯示狀態"""
        try:
            # 檢查案件是否有"已結案"階段
            has_closed_stage = False
            if hasattr(case, 'progress_stages') and case.progress_stages:
                has_closed_stage = '已結案' in case.progress_stages

            if has_closed_stage:
                self._show_transfer_button()
            else:
                self._hide_transfer_button()

        except Exception as e:
            print(f"更新轉移按鈕顯示狀態失敗: {e}")
            self._hide_transfer_button()

    def _show_transfer_button(self):
        """🔥 新增：顯示結案轉移按鈕"""
        try:
            # 重新包裝按鈕到正確位置（第三個位置）
            self.transfer_btn.pack_forget()
            self.transfer_btn.pack(side='left', padx=5, after=self.upload_btn)
        except Exception as e:
            print(f"顯示轉移按鈕失敗: {e}")

    def _hide_transfer_button(self):
        """🔥 新增：隱藏結案轉移按鈕"""
        try:
            self.transfer_btn.pack_forget()
        except Exception as e:
            print(f"隱藏轉移按鈕失敗: {e}")

    def _on_case_transfer(self):
        """🔥 新增：結案轉移事件"""
        # 檢查是否選擇了案件
        selection = self.tree.selection()
        if not selection:
            UnifiedMessageDialog.show_warning(self.window, "請先選擇一個案件")
            return

        if not self.case_controller:
            UnifiedMessageDialog.show_warning(self.window, "案件控制器未初始化")
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

                # 再次確認案件是否有"已結案"階段
                if not (hasattr(case, 'progress_stages') and
                       case.progress_stages and
                       '已結案' in case.progress_stages):
                    UnifiedMessageDialog.show_warning(self.window, "選擇的案件尚未結案，無法執行轉移")
                    return

                # 顯示結案轉移對話框
                from views.case_transfer_dialog import CaseTransferDialog

                def on_transfer_complete():
                    """轉移完成後的回調"""
                    print("結案轉移完成，重新載入案件列表")
                    self._load_cases()
                    # 隱藏轉移按鈕
                    self._hide_transfer_button()

                CaseTransferDialog.show_transfer_dialog(
                    self.window,
                    case,
                    self.case_controller,
                    on_transfer_complete
                )
            else:
                print(f"無法取得有效的案件索引：tags={tags}")
                UnifiedMessageDialog.show_error(self.window, "無法取得選中的案件資訊")

        except Exception as e:
            print(f"開啟結案轉移對話框失敗: {e}")
            UnifiedMessageDialog.show_error(self.window, f"無法開啟轉移對話框：{str(e)}")



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
        """顯示案件進度 - 🔥 完整修正：統一使用截短組件"""
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

        # 🔥 統一使用截短組件
        from utils.text_widget import TruncatedTextWidget

        # 案號顯示
        case_number = getattr(case, 'case_number', None) or '無'
        case_number_widget = TruncatedTextWidget(
            info_frame,
            text=f"案號: {case_number}",
            max_length=AppConfig.TEXT_TRUNCATION['case_number_length'],
            font=AppConfig.FONTS['text'],
            bg_color=AppConfig.COLORS['window_bg'],
            fg_color=AppConfig.COLORS['text_color']
        )
        case_number_widget.pack(anchor='w', pady=(0, 4))

        # 第二行：案由和對造並排顯示
        row2_frame = tk.Frame(info_frame, bg=AppConfig.COLORS['window_bg'])
        row2_frame.pack(fill='x', pady=(0, 4))

        # 案由使用截短組件
        case_reason = getattr(case, 'case_reason', None) or '無'
        case_reason_widget = TruncatedTextWidget(
            row2_frame,
            text=f"案由: {case_reason}",
            max_length=AppConfig.TEXT_TRUNCATION['case_reason_length'],
            font=AppConfig.FONTS['text'],
            bg_color=AppConfig.COLORS['window_bg'],
            fg_color=AppConfig.COLORS['text_color']
        )
        case_reason_widget.pack(side='left', anchor='nw')

        # 對造使用截短組件
        opposing_party = getattr(case, 'opposing_party', None) or '無'
        opposing_party_widget = TruncatedTextWidget(
            row2_frame,
            text=f"對造: {opposing_party}",
            max_length=AppConfig.TEXT_TRUNCATION['opposing_party_length'],
            font=AppConfig.FONTS['text'],
            bg_color=AppConfig.COLORS['window_bg'],
            fg_color=AppConfig.COLORS['text_color']
        )
        opposing_party_widget.pack(side='left', anchor='nw', padx=(15, 0))

        # 🔥 第三行：負責法院和負責股別並排顯示 - 核心修正
        row3_frame = tk.Frame(info_frame, bg=AppConfig.COLORS['window_bg'])
        row3_frame.pack(fill='x', pady=(0, 4))

        # 🔥 負責法院使用截短組件
        court = getattr(case, 'court', None) or '無'
        court_widget = TruncatedTextWidget(
            row3_frame,
            text=f"負責法院: {court}",
            max_length=AppConfig.TEXT_TRUNCATION['court_name_length'],
            font=AppConfig.FONTS['text'],
            bg_color=AppConfig.COLORS['window_bg'],
            fg_color=AppConfig.COLORS['text_color']
        )
        court_widget.pack(side='left', anchor='nw')

        # 🔥 負責股別使用截短組件
        division = getattr(case, 'division', None) or '無'
        division_widget = TruncatedTextWidget(
            row3_frame,
            text=f"負責股別: {division}",
            max_length=AppConfig.TEXT_TRUNCATION['division_name_length'],
            font=AppConfig.FONTS['text'],
            bg_color=AppConfig.COLORS['window_bg'],
            fg_color=AppConfig.COLORS['text_color']
        )
        division_widget.pack(side='left', anchor='nw', padx=(15, 0))

        # 分隔線
        tk.Label(
            info_frame,
            text="－" * 15,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text']
        ).pack(anchor='w', pady=(5, 5))

        # 新增階段按鈕
        add_stage_btn = tk.Button(
            info_frame,
            text='新增進度階段',
            command=lambda: self._on_add_progress_stage(case),
            bg='#4CAF50',
            fg='white',
            font=AppConfig.FONTS['button'],
            width=15,
            height=1
        )
        add_stage_btn.pack(anchor='w', pady=5)

        # 右側進度階段顯示
        progress_bar_frame = tk.Frame(
            self.progress_display,
            bg=AppConfig.COLORS['window_bg']
        )
        progress_bar_frame.pack(side='right', expand=True, fill='x', padx=5)

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
        sorted_stages = sorted(
            case.progress_stages.items(),
            key=lambda x: x[1] if x[1] else '9999-12-31'
        )


        for i, (stage, date) in enumerate(sorted_stages):
            # 每個階段的容器
            stage_container = tk.Frame(
                progress_bar_frame,
                bg=AppConfig.COLORS['window_bg']
            )
            stage_container.pack(side='left', expand=True)

            # 🔥 修改：固定高度的上方區域（用於便籤圖示）
            note_frame = tk.Frame(
                stage_container,
                bg=AppConfig.COLORS['window_bg'],
                height=35  # 固定高度確保水平對齊
            )
            note_frame.pack(fill='x')
            note_frame.pack_propagate(False)  # 🔥 重要：防止框架縮小

            # 檢查是否有備註
            if hasattr(case, 'has_stage_note') and case.has_stage_note(stage):
                note_icon = tk.Label(
                    note_frame,
                    text="📄",  # 便籤圖示
                    bg=AppConfig.COLORS['window_bg'],
                    fg='white',
                    font=('Microsoft JhengHei', 14),
                    cursor='hand2'
                )
                note_icon.pack(anchor='center')  # 🔥 修改：置中顯示

                # 🔥 新增：綁定點擊事件顯示備註內容
                note_content = case.get_stage_note(stage)
                note_icon.bind('<Button-1>', lambda e, note=note_content: self._show_stage_note(note))

                # 🔥 新增：滑鼠懸停提示
                self._create_tooltip(note_icon, f"{note_content[:50]}{'...' if len(note_content) > 50 else ''}")

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

            # 🔥 修改：固定高度的日期時間區域
            datetime_frame = tk.Frame(
                stage_container,
                bg=AppConfig.COLORS['window_bg'],
                height=40  # 固定高度確保水平對齊
            )
            datetime_frame.pack(fill='x')
            datetime_frame.pack_propagate(False)  # 防止框架縮小

            # 顯示日期
            if date:
                date_label = tk.Label(
                    circle_frame,
                    text=date,
                    bg=AppConfig.COLORS['window_bg'],
                    fg="white",
                    font=('Microsoft JhengHei', 10)
                )
                date_label.pack(pady=(3, 0))

            # 🔥 修改：顯示時間（在固定區域內）
            if hasattr(case, 'progress_times') and case.progress_times:
                stage_time = case.progress_times.get(stage, '')
                if stage_time:
                    time_label = tk.Label(
                        datetime_frame,
                        text=stage_time,
                        bg=AppConfig.COLORS['window_bg'],
                        fg="white",
                        font=('Microsoft JhengHei', 9)
                    )
                    time_label.pack(pady=(1, 0))

            # 連接線
            if i < len(sorted_stages) - 1:
                line_frame = tk.Frame(
                    progress_bar_frame,
                    bg='white',
                    height=1,
                    width=15
                )
                line_frame.pack(side='left', pady=5)

    def _show_stage_note(self, note_content: str):
        """🔥 新增：顯示階段備註內容"""
        from views.dialogs import UnifiedMessageDialog
        UnifiedMessageDialog.show_info(self.window, note_content, "階段備註")

    def _create_tooltip(self, widget, text):
        """🔥 新增：建立工具提示"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")

            label = tk.Label(
                tooltip,
                text=text,
                background='#FFFFCC',
                foreground='black',
                font=AppConfig.FONTS['text'],
                relief='solid',
                borderwidth=1,
                wraplength=200
            )
            label.pack()

            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)

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
        """新增進度階段 - 🔥 統一流程：回調函數只處理業務邏輯"""
        from views.simple_progress_edit_dialog import SimpleProgressEditDialog

        def save_new_stage(result):
            """新增階段的回調函數 - 只處理業務邏輯，不顯示訊息"""
            try:
                # 執行實際的儲存操作
                success = self.case_controller.add_case_progress_stage(
                    case.case_id,
                    result['stage_name'],
                    result['stage_date'],
                    result.get('note', ''),
                    result.get('time', '')
                )

                if success:
                    # 刷新案件列表
                    self._load_cases()
                    self._reselect_case(case.case_id)

                return success

            except Exception as e:
                print(f"新增階段回調失敗: {e}")
                return False

        # 顯示新增對話框
        try:
            SimpleProgressEditDialog.show_add_dialog(self.window, case, save_new_stage)

        except Exception as e:
            print(f"顯示新增階段對話框時發生錯誤: {e}")
            from views.dialogs import UnifiedMessageDialog
            UnifiedMessageDialog.show_error(
                self.window,
                f"無法開啟新增階段對話框：{str(e)}"
            )

    def _on_edit_progress_stage(self, case: CaseData, stage_name: str):
        """編輯進度階段 - 🔥 統一流程：回調函數只處理業務邏輯"""
        from views.simple_progress_edit_dialog import SimpleProgressEditDialog

        stage_date = case.progress_stages.get(stage_name, '')

        def save_edited_stage(result):
            """編輯階段的回調函數 - 只處理業務邏輯，不顯示訊息"""
            try:
                # 執行實際的更新操作
                success = self.case_controller.update_case_progress_stage(
                    case.case_id,
                    result['stage_name'],
                    result['stage_date'],
                    result.get('note', ''),
                    result.get('time', '')
                )

                if success:
                    # 刷新案件列表
                    self._load_cases()
                    self._reselect_case(case.case_id)

                return success

            except Exception as e:
                print(f"更新階段回調失敗: {e}")
                return False

        # 顯示編輯對話框
        try:
            SimpleProgressEditDialog.show_edit_dialog(
                self.window, case, stage_name, stage_date, save_edited_stage
            )

        except Exception as e:
            print(f"顯示編輯階段對話框時發生錯誤: {e}")
            from views.dialogs import UnifiedMessageDialog
            UnifiedMessageDialog.show_error(
                self.window,
                f"無法開啟編輯階段對話框：{str(e)}"
            )

    def _on_remove_progress_stage(self, case: CaseData, stage_name: str):
        """移除進度階段 - 🔥 保持原有邏輯（因為刪除確認應該在操作前顯示）"""
        import os

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

        # 顯示確認對話框
        try:
            from views.dialogs import UnifiedConfirmDialog, UnifiedMessageDialog

            confirm_dialog = UnifiedConfirmDialog(
                self.window,
                title="確認刪除階段",
                message=confirm_message,
                confirm_text="確定刪除",
                cancel_text="取消"
            )

            confirm_dialog.window.wait_window()

            # 處理確認結果
            if confirm_dialog.result:
                try:
                    success = self.case_controller.remove_case_progress_stage(case.case_id, stage_name)
                    if success:
                        self._load_cases()
                        self._reselect_case(case.case_id)

                        if folder_exists:
                            UnifiedMessageDialog.show_success(
                                self.window,
                                f"已移除進度階段「{stage_name}」\n階段資料夾已同時刪除"
                            )
                        else:
                            UnifiedMessageDialog.show_success(
                                self.window,
                                f"已移除進度階段「{stage_name}」"
                            )
                    else:
                        UnifiedMessageDialog.show_error(self.window, "無法移除當前進度階段")
                except Exception as e:
                    UnifiedMessageDialog.show_error(self.window, f"移除階段失敗：{str(e)}")

        except Exception as e:
            print(f"顯示確認對話框時發生錯誤: {e}")
            from views.dialogs import UnifiedMessageDialog
            UnifiedMessageDialog.show_error(
                self.window,
                f"無法顯示確認對話框：{str(e)}"
            )

    # 🔥 新增：在所有可能觸發 after 回調的方法中增加狀態檢查
    def _reselect_case(self, case_id):
        """重新選擇案件 - 增加關閉狀態檢查"""
        if self._is_closing or self._is_destroyed:
            return

        try:
            # 檢查視窗是否仍然存在
            if not hasattr(self, 'window') or not self.window or not self.window.winfo_exists():
                return

            # 原有的重新選擇邏輯...
            for i, case in enumerate(self.case_data):
                if case.case_id == case_id:
                    for item in self.tree.get_children():
                        tags = self.tree.item(item, 'tags')
                        for tag in tags:
                            if tag == f'index_{i}':
                                if not self._is_closing:  # 再次檢查
                                    self.tree.selection_set(item)
                                    self.tree.focus(item)
                                    self.tree.see(item)
                                return
                    break
        except Exception as e:
            print(f"重新選擇案件失敗: {e}")

    def show(self):
        """顯示視窗 - 增加狀態檢查"""
        if self._is_closing or self._is_destroyed:
            return

        try:
            if hasattr(self, 'window') and self.window and self.window.winfo_exists():
                self.window.deiconify()
                self.window.lift()
                self.window.focus_force()
        except Exception as e:
            print(f"顯示視窗失敗: {e}")

    def hide(self):
        """隱藏視窗 - 增加狀態檢查"""
        if self._is_closing or self._is_destroyed:
            return

        try:
            if hasattr(self, 'window') and self.window and self.window.winfo_exists():
                self.window.withdraw()
        except Exception as e:
            print(f"隱藏視窗失敗: {e}")

    def _on_add_case(self):
        """新增案件事件 - 修正版本：避免重複載入"""
        if not self.case_controller:
            UnifiedMessageDialog.show_warning(self.window, "案件控制器未初始化")
            return

        from views.case_form import CaseFormDialog

        def save_new_case(case_data, mode):
            try:
                print(f"開始新增案件: {case_data.client}")

                # 讓 controller 自動生成案件編號
                if not case_data.case_id:
                    case_data.case_id = self.case_controller.generate_case_id(case_data.case_type)
                    print(f"產生案件編號: {case_data.case_id}")

                # 新增案件 - controller 會處理所有邏輯
                success = self.case_controller.add_case(case_data)

                if success:
                    print(f"案件新增成功")

                    # 修正：只需要重新載入 UI 顯示，不要重複載入資料
                    self._load_cases()  # 這會從 controller 取得最新資料
                    print(f"UI 重新載入完成，當前案件數量: {len(self.case_data)}")

                    # 取得資料夾路徑用於顯示訊息
                    folder_path = self.case_controller.get_case_folder_path(case_data.case_id)

                    # 使用統一的顯示格式
                    case_display_name = AppConfig.format_case_display_name(case_data)

                    if folder_path:
                        message = f"案件 {case_display_name} 新增成功！\n\n已建立資料夾結構：\n{folder_path}"
                    else:
                        message = f"案件 {case_display_name} 新增成功！\n\n注意：資料夾結構建立失敗，請手動建立。"

                    self.window.after(100, lambda: UnifiedMessageDialog.show_success(self.window, message))
                else:
                    print(f"案件新增失敗")
                    UnifiedMessageDialog.show_error(self.window, "案件新增失敗！")

                return success

            except Exception as e:
                print(f"新增案件回調發生錯誤: {e}")
                import traceback
                traceback.print_exc()
                UnifiedMessageDialog.show_error(self.window, f"新增案件時發生錯誤：{str(e)}")
                return False

        try:
            CaseFormDialog.show_add_dialog(self.window, save_new_case)
        except Exception as e:
            print(f"開啟新增案件對話框失敗: {e}")
            UnifiedMessageDialog.show_error(self.window, f"無法開啟新增案件對話框：{str(e)}")

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
                    success = self.case_controller.update_case(case_data)
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
        """刪除案件（含資料夾刪除確認）- 修正版本"""
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
                        # 🔥 修正：提供完整的參數
                        success = self.case_controller.delete_case(
                            case_id=case.case_id,
                            case_type=case.case_type,  # 明確提供 case_type
                            delete_folder=True
                        )

                        if success:
                            self._load_cases()

                            if folder_info['exists']:
                                UnifiedMessageDialog.show_success(
                                    self.window,
                                    f"案件 {case_display_name} 已刪除\n案件資料夾已同時刪除"
                                )
                            else:
                                UnifiedMessageDialog.show_success(
                                    self.window,
                                    f"案件 {case_display_name} 已刪除"
                                )
                        else:
                            UnifiedMessageDialog.show_error(self.window, "案件刪除失敗")
                    except Exception as e:
                        UnifiedMessageDialog.show_error(self.window, f"刪除案件失敗：{str(e)}")
            else:
                print(f"無法取得有效的案件索引：tags={tags}")

        except (ValueError, IndexError) as e:
            print(f"刪除案件失敗: {e}")
            UnifiedMessageDialog.show_error(self.window, "無法刪除案件")


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
        """🔥 完全修正：關閉視窗時安全清理資源"""
        if self._is_closing or self._is_destroyed:
            return

        self._is_closing = True
        print("開始關閉 CaseOverview...")

        try:
            # 第一步：立即停止所有定時器和回調
            self._stop_all_timers_and_callbacks()

            # 第二步：取消事件訂閱
            self._unsubscribe_all_events()

            # 第三步：安全銷毀子組件
            self._destroy_child_components()

            # 第四步：清理編輯狀態
            self._cleanup_edit_state()

            # 第五步：關閉主視窗
            self._destroy_main_window()

            print("CaseOverview 已安全關閉")

        except Exception as e:
            print(f"CaseOverview 關閉過程發生錯誤: {e}")
            # 強制關閉
            self._force_destroy()

    def _stop_all_timers_and_callbacks(self):
        """🔥 新增：停止所有定時器和回調"""
        try:
            # 停止日期提醒控件的所有定時器
            if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                # 停止滾動定時器
                if hasattr(self.date_reminder_widget, '_stop_scroll'):
                    self.date_reminder_widget._stop_scroll()

                # 關閉展開視窗
                if hasattr(self.date_reminder_widget, 'expanded_window') and self.date_reminder_widget.expanded_window:
                    try:
                        self.date_reminder_widget.expanded_window.destroy()
                        self.date_reminder_widget.expanded_window = None
                    except:
                        pass

                # 停止鈴鐺彈出視窗
                if hasattr(self.date_reminder_widget, '_hide_bell_popup'):
                    self.date_reminder_widget._hide_bell_popup()

            # 取消所有 after 調用
            if hasattr(self, 'window') and self.window:
                # 清除視窗的所有 after 調用
                try:
                    # 這個方法可能不存在於所有 Tkinter 版本
                    if hasattr(self.window, 'tk'):
                        self.window.tk.call('after', 'cancel', 'all')
                except:
                    pass

            print("已停止所有定時器和回調")

        except Exception as e:
            print(f"停止定時器失敗: {e}")

    def _unsubscribe_all_events(self):
        """🔥 新增：安全取消所有事件訂閱"""
        try:
            from utils.event_manager import event_manager, EventType

            # 取消事件訂閱
            events_to_unsubscribe = [
                (EventType.CASE_UPDATED, self._on_case_updated_event),
                (EventType.STAGE_ADDED, self._on_stage_updated_event),
                (EventType.STAGE_UPDATED, self._on_stage_updated_event),
                (EventType.STAGE_DELETED, self._on_stage_updated_event),
            ]

            for event_type, callback in events_to_unsubscribe:
                try:
                    event_manager.unsubscribe(event_type, callback)
                except Exception as e:
                    print(f"取消訂閱 {event_type} 失敗: {e}")

            print("已取消所有事件訂閱")

        except Exception as e:
            print(f"取消事件訂閱失敗: {e}")

    def _destroy_child_components(self):
        """🔥 新增：安全銷毀子組件"""
        try:
            # 銷毀日期提醒控件
            if hasattr(self, 'date_reminder_widget') and self.date_reminder_widget:
                try:
                    # 確保先清理日期提醒控件的資源
                    if hasattr(self.date_reminder_widget, 'destroy'):
                        self.date_reminder_widget.destroy()
                    else:
                        # 手動清理
                        if hasattr(self.date_reminder_widget, 'main_frame'):
                            self.date_reminder_widget.main_frame.destroy()
                except Exception as e:
                    print(f"銷毀日期提醒控件失敗: {e}")
                finally:
                    self.date_reminder_widget = None

            # 銷毀其他可能的子組件
            components_to_destroy = [
                'edit_entry',  # 編輯輸入框
                'toolbar_frame',
                'search_frame',
                'tree_frame',
                'field_control_frame'
            ]

            for component_name in components_to_destroy:
                if hasattr(self, component_name):
                    component = getattr(self, component_name)
                    if component:
                        try:
                            component.destroy()
                        except:
                            pass
                        setattr(self, component_name, None)

            print("已銷毀子組件")

        except Exception as e:
            print(f"銷毀子組件失敗: {e}")

    def _cleanup_edit_state(self):
        """🔥 新增：清理編輯狀態"""
        try:
            # 清理編輯狀態
            self.is_editing = False
            self.edit_entry = None
            self.edit_item = None

            # 清理選擇狀態
            self.current_selected_case_id = None
            self.current_selected_item = None

            print("已清理編輯狀態")

        except Exception as e:
            print(f"清理編輯狀態失敗: {e}")

    def _destroy_main_window(self):
        """🔥 新增：安全銷毀主視窗"""
        try:
            if hasattr(self, 'window') and self.window:
                # 解除視窗事件綁定
                try:
                    self.window.protocol("WM_DELETE_WINDOW", lambda: None)
                except:
                    pass

                # 銷毀視窗
                self.window.destroy()
                self.window = None

            self._is_destroyed = True
            print("主視窗已銷毀")

        except Exception as e:
            print(f"銷毀主視窗失敗: {e}")
            self._force_destroy()

    def _force_destroy(self):
        """🔥 新增：強制銷毀（緊急情況使用）"""
        try:
            self._is_destroyed = True
            if hasattr(self, 'window') and self.window:
                self.window.quit()  # 強制退出
                self.window = None
            print("已強制銷毀視窗")
        except:
            pass
