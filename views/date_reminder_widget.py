#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔥 整合版本 - 簡約浮動式日期提醒控件
整合功能：
- 第一個版本的明天案件鈴聲提示功能（含觀察者模式）
- 第二個版本的文字樣式顯示格式
- 統一的案件資料更新處理機制
"""
import tkinter as tk
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable, Optional

from config.notification_settings import NotificationConfig
from config.settings import AppConfig
from utils.date_reminder import DateReminderManager
from utils.event_manager import event_manager, EventType
from utils.notification_manager import NotificationManager


class DateReminderWidget:
    """簡約浮動式日期提醒控件 - 🔥 整合版本"""

    def __init__(self, parent, case_data: List = None, on_case_select: Optional[Callable] = None):
        """
        初始化日期提醒控件 - 🆕 整合音量控制功能

        Args:
            parent: 父視窗（用於相對定位）
            case_data: 案件資料列表
            on_case_select: 案件選擇回調函數
        """
        # ========================================
        # 基本屬性初始化
        # ========================================
        self.parent_window = parent
        self.case_data = case_data or []
        self.on_case_select = on_case_select

        # 顯示控制屬性
        self.days_ahead = 3  # 預設顯示3天內的階段
        self.upcoming_stages = []
        self.current_index = 0
        self.scroll_job = None
        self.is_expanded = False

        # 案件選擇相關屬性
        self.selected_case_index = None
        self.selected_case_id = None
        self.expanded_window = None

        # ========================================
        # 鈴聲與通知相關屬性
        # ========================================
        # 動態彈出標籤相關
        self.bell_popup_window = None
        self.bell_popup_job = None
        self.current_showing_tomorrow = False  # 追蹤當前是否顯示明天案件
        self.last_checked_case_id = None  # 避免重複觸發鈴聲

        # 通知管理器初始化
        self.notification_manager = NotificationManager()
        self.notification_config = NotificationConfig()
        self.last_notification_check = None

        self.notification_icon = None

        # ========================================
        # 🆕 音量控制相關屬性
        # ========================================
        # 註冊音量變更回調，確保 UI 同步
        self.notification_manager.register_notification_state_callback(self._on_notification_state_changed)

        # 設定鈴鐺回調
        self.notification_manager.set_bell_callback(self._on_bell_triggered)

        # ========================================
        # 事件訂閱與觀察者模式
        # ========================================
        # 訂閱案件相關事件
        self._subscribe_to_events()

        # ========================================
        # UI 元件創建與初始化
        # ========================================
        # 創建主框架和所有 UI 元件
        self._create_widget()

        # 初始化顯示內容
        self._update_display()

        print("DateReminderWidget 初始化完成")


    def _subscribe_to_events(self):
        """🔥 修正：訂閱案件相關事件，增強事件處理"""
        try:
            event_manager.subscribe(EventType.STAGE_ADDED, self._on_stage_event)
            event_manager.subscribe(EventType.STAGE_UPDATED, self._on_stage_event)
            event_manager.subscribe(EventType.STAGE_DELETED, self._on_stage_event)
            event_manager.subscribe(EventType.CASE_UPDATED, self._on_case_event)  # 🔥 重要
            event_manager.subscribe(EventType.CASES_RELOADED, self._on_cases_reloaded)

            print("DateReminderWidget 已訂閱案件事件:")
            print(f"  - STAGE_ADDED: {event_manager.get_subscribers_count(EventType.STAGE_ADDED)} 訂閱者")
            print(f"  - STAGE_UPDATED: {event_manager.get_subscribers_count(EventType.STAGE_UPDATED)} 訂閱者")
            print(f"  - STAGE_DELETED: {event_manager.get_subscribers_count(EventType.STAGE_DELETED)} 訂閱者")
            print(f"  - CASE_UPDATED: {event_manager.get_subscribers_count(EventType.CASE_UPDATED)} 訂閱者")
            print(f"  - CASES_RELOADED: {event_manager.get_subscribers_count(EventType.CASES_RELOADED)} 訂閱者")

        except Exception as e:
            print(f"訂閱事件失敗: {e}")
            import traceback
            traceback.print_exc()

    def _on_bell_triggered(self, is_urgent: bool, count: int):
        """🆕 鈴鐺圖示觸發回調"""
        try:
            if is_urgent:
                print(f"🔔 緊急提醒觸發: {count} 個案件")
                # 可以在這裡添加 UI 反饋，如鈴鐺圖示閃爍動畫
            else:
                print(f"🔔 一般提醒觸發: {count} 個案件")
        except Exception as e:
            print(f"處理鈴鐺觸發回調失敗: {e}")

    def _on_stage_event(self, event_data):
        """🔥 修正：處理階段相關事件，增強除錯資訊"""
        try:
            if not event_data:
                print("DateReminderWidget 收到空的階段事件資料")
                return

            case_id = event_data.get('case_id')
            stage_name = event_data.get('stage_name')
            action = event_data.get('action', 'unknown')

            print(f"DateReminderWidget 收到階段事件: case_id={case_id}, stage={stage_name}, action={action}")

            # 🔥 重要：立即強制刷新案件資料
            if hasattr(self, 'case_controller') and self.case_controller:
                self.case_data = self.case_controller.get_cases()
                print(f"已刷新案件資料，共 {len(self.case_data)} 個案件")

            # 立即更新顯示，避免跳躍
            self._update_display_no_interrupt()

        except Exception as e:
            print(f"處理階段事件失敗: {e}")
            import traceback
            traceback.print_exc()

    def _force_refresh_display(self):
        """🔥 新增：強制完全刷新顯示，不保留任何狀態"""
        try:
            print("強制刷新跑馬燈顯示...")

            # 停止當前滾動
            if hasattr(self, 'scroll_job') and self.scroll_job:
                self.main_frame.after_cancel(self.scroll_job)
                self.scroll_job = None

            # 重置所有狀態
            self.current_index = 0
            self.selected_case_id = None
            self.selected_case_index = None

            # 隱藏任何彈出視窗
            self._hide_bell_popup()
            if hasattr(self, 'expanded_window') and self.expanded_window:
                self.expanded_window.destroy()
                self.expanded_window = None

            # 完全重新載入顯示
            self._update_display()

            print(f"跑馬燈強制刷新完成，顯示項目數: {len(getattr(self, 'upcoming_stages', []))}")

        except Exception as e:
            print(f"強制刷新顯示失敗: {e}")
            import traceback
            traceback.print_exc()

    def _update_display_no_interrupt(self):
        """更新顯示（無中斷版本）- 增加狀態檢查"""
        try:
            # 檢查組件是否仍然存在
            if not hasattr(self, 'main_frame') or not self.main_frame:
                return

            if not hasattr(self, 'current_label') or not self.current_label:
                return

            # 檢查組件是否已被銷毀
            try:
                self.current_label.winfo_exists()
            except:
                return

            print("無中斷更新跑馬燈顯示...")

            # 保存當前狀態
            current_index = getattr(self, 'current_index', 0)
            was_scrolling = hasattr(self, 'scroll_job') and self.scroll_job is not None

            # 🔥 重要：重新計算即將到期的階段
            old_count = len(getattr(self, 'upcoming_stages', []))
            self._calculate_upcoming_stages()
            new_count = len(getattr(self, 'upcoming_stages', []))

            print(f"階段數量變化: {old_count} -> {new_count}")

            # 🔥 修正：調整索引以防越界
            if self.upcoming_stages:
                self.current_index = min(current_index, len(self.upcoming_stages) - 1)
                self.current_index = max(0, self.current_index)  # 確保不小於0
            else:
                self.current_index = 0

            # 更新顯示
            self._update_current_display()

            # 🔥 重要：如果之前在滾動且還有項目，則繼續滾動
            if was_scrolling and self.upcoming_stages and len(self.upcoming_stages) > 1:
                self._start_scroll()
                print("繼續滾動顯示")
            else:
                print("停止滾動或無足夠項目滾動")

        except Exception as e:
            print(f"無中斷更新失敗: {e}")
            import traceback
            traceback.print_exc()
            # 如果無中斷更新失敗，則執行強制刷新
            self._force_refresh_display()

    def _on_case_event(self, event_data):
        """🔥 修正：處理案件相關事件，增強處理邏輯"""
        try:
            if not event_data:
                print("DateReminderWidget 收到空的案件事件資料")
                return

            case_id = event_data.get('case_id')
            action = event_data.get('action', 'unknown')

            print(f"DateReminderWidget 收到案件事件: case_id={case_id}, action={action}")

            # 🔥 重要：立即強制刷新案件資料
            if hasattr(self, 'case_controller') and self.case_controller:
                self.case_data = self.case_controller.get_cases()
                print(f"已刷新案件資料，共 {len(self.case_data)} 個案件")

            # 立即更新顯示
            self._update_display_no_interrupt()

        except Exception as e:
            print(f"處理案件事件失敗: {e}")
            import traceback
            traceback.print_exc()

    def _on_cases_reloaded(self, event_data):
        """🔥 修正：處理案件重新載入事件，增強資料驗證"""
        try:
            if not event_data:
                print("DateReminderWidget 收到空的案件重新載入事件")
                # 即使事件資料為空，也嘗試從控制器獲取資料
                if hasattr(self, 'case_controller') and self.case_controller:
                    self.case_data = self.case_controller.get_cases()
                    print(f"從控制器獲取案件資料: {len(self.case_data)} 個案件")
                else:
                    self.case_data = []
                    print("無法獲取案件資料，設為空列表")
            else:
                cases = event_data.get('cases', [])
                case_count = event_data.get('case_count', 0)

                print(f"DateReminderWidget 收到案件重新載入事件:")
                print(f"  - 事件傳遞的案件數: {len(cases)}")
                print(f"  - 事件聲明的案件數: {case_count}")

                # 🔥 修正：優先使用事件中的案件資料，如果為空則從控制器獲取
                if cases:
                    self.case_data = cases
                    print(f"使用事件中的案件資料: {len(self.case_data)} 個案件")
                elif hasattr(self, 'case_controller') and self.case_controller:
                    self.case_data = self.case_controller.get_cases()
                    print(f"從控制器獲取案件資料: {len(self.case_data)} 個案件")
                else:
                    self.case_data = []
                    print("無案件資料可用")

            # 🔥 重要：強制完全重新載入顯示
            self._force_refresh_display()

        except Exception as e:
            print(f"處理案件重新載入事件失敗: {e}")
            import traceback
            traceback.print_exc()



    def destroy(self):
        """🔥 完全修正：銷毀控件時安全清理所有資源"""
        try:
            print("開始銷毀 DateReminderWidget...")

            # 🔥 第一步：停止所有定時器
            self._stop_all_timers()

            # 🔥 第二步：取消事件訂閱
            self._unsubscribe_all_events()

            # 🔥 第三步：關閉所有彈出視窗
            self._close_all_popups()

            # 🔥 第四步：清理通知管理器回調
            self._cleanup_notification_callbacks()

            # 🔥 第五步：銷毀主要組件
            self._destroy_main_components()

            print("DateReminderWidget 已安全銷毀")

        except Exception as e:
            print(f"DateReminderWidget 銷毀失敗: {e}")

    def _stop_all_timers(self):
        """🔥 新增：停止所有定時器"""
        try:
            # 停止主滾動定時器
            if hasattr(self, 'scroll_job') and self.scroll_job:
                try:
                    self.current_label.after_cancel(self.scroll_job)
                except:
                    pass
                self.scroll_job = None

            # 停止其他可能的定時器
            timer_attributes = ['_scroll_timer', '_update_timer', '_bell_timer']
            for attr in timer_attributes:
                if hasattr(self, attr):
                    timer = getattr(self, attr)
                    if timer:
                        try:
                            self.current_label.after_cancel(timer)
                        except:
                            pass
                        setattr(self, attr, None)

            print("已停止所有定時器")

        except Exception as e:
            print(f"停止定時器失敗: {e}")

    def _unsubscribe_all_events(self):
        """🔥 新增：取消所有事件訂閱"""
        try:
            from utils.event_manager import event_manager, EventType

            events_to_unsubscribe = [
                (EventType.STAGE_ADDED, self._on_stage_event),
                (EventType.STAGE_UPDATED, self._on_stage_event),
                (EventType.STAGE_DELETED, self._on_stage_event),
                (EventType.CASE_UPDATED, self._on_case_event),
                (EventType.CASES_RELOADED, self._on_cases_reloaded),
            ]

            for event_type, callback in events_to_unsubscribe:
                try:
                    event_manager.unsubscribe(event_type, callback)
                except Exception as e:
                    print(f"取消訂閱 {event_type} 失敗: {e}")

            print("已取消所有事件訂閱")

        except Exception as e:
            print(f"取消事件訂閱失敗: {e}")

    def _close_all_popups(self):
        """🔥 新增：關閉所有彈出視窗"""
        try:
            # 關閉展開視窗
            if hasattr(self, 'expanded_window') and self.expanded_window:
                try:
                    self.expanded_window.destroy()
                except:
                    pass
                self.expanded_window = None

            # 關閉鈴鐺彈出視窗
            if hasattr(self, 'bell_popup_window') and self.bell_popup_window:
                try:
                    self.bell_popup_window.destroy()
                except:
                    pass
                self.bell_popup_window = None

            print("已關閉所有彈出視窗")

        except Exception as e:
            print(f"關閉彈出視窗失敗: {e}")

    def _cleanup_notification_callbacks(self):
        """清理通知管理器回調"""
        try:
            if hasattr(self, 'notification_manager') and self.notification_manager:
                try:
                    if hasattr(self.notification_manager, 'unregister_notification_state_callback'):
                        self.notification_manager.unregister_notification_state_callback(self._on_notification_state_changed)
                except Exception as e:
                    print(f"取消通知狀態回調失敗: {e}")

        except Exception as e:
            print(f"清理通知回調失敗: {e}")

    def _destroy_main_components(self):
        """🔥 新增：銷毀主要組件"""
        try:
            # 銷毀主框架（這會自動銷毀所有子組件）
            if hasattr(self, 'main_frame') and self.main_frame:
                try:
                    self.main_frame.destroy()
                except Exception as e:
                    print(f"銷毀主框架失敗: {e}")
                self.main_frame = None

            # 清理其他組件引用
            components_to_clear = [
                'current_label', 'bell_label', 'parent_window',
                'case_data', 'notification_manager', 'on_case_select'
            ]

            for component in components_to_clear:
                if hasattr(self, component):
                    setattr(self, component, None)

            print("已銷毀主要組件")

        except Exception as e:
            print(f"銷毀主要組件失敗: {e}")

    def _create_widget(self):
        """建立控件"""
        # 主容器
        self.main_frame = tk.Frame(self.parent_window, bg=AppConfig.COLORS['window_bg'])
        self.main_frame.pack(side='right', fill='y', padx=(10, 0))

        # 天數控制（上方左側靠齊）
        self._create_days_control()

        # 跑馬燈容器
        self.marquee_container = tk.Frame(self.main_frame, bg=AppConfig.COLORS['window_bg'])
        self.marquee_container.pack(fill='x')

        # 簡約跑馬燈顯示
        self._create_minimal_display()

        # 初始化動態鈴鐺標籤變數
        self.bell_popup_window = None
        self.bell_popup_job = None
        self.current_showing_tomorrow = False

    def _create_days_control(self):
        """建立天數控制與音量控制 - 🆕 新增音量圖示"""
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

        # 🆕 音量控制容器（靠右對齊）
        self._create_notification_control(control_frame)


    def _create_notification_control(self, parent_frame):
        """🆕 建立鈴聲通知開關"""
        notification_container = tk.Frame(parent_frame, bg=AppConfig.COLORS['window_bg'])
        notification_container.pack(side='right')

        # 鈴聲通知開關按鈕
        self.notification_icon = tk.Label(
            notification_container,
            text="🔔",  # 預設為開啟狀態
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Arial', 12),
            cursor='hand2'
        )
        self.notification_icon.pack(side='right', padx=(0, 5))
        self.notification_icon.bind('<Button-1>', self._toggle_notification)

        # 初始化圖示狀態
        self._update_notification_icon()

    def _toggle_notification(self, event=None):
        """🆕 切換鈴聲通知開關狀態"""
        try:
            # 取得通知管理器當前通知狀態
            current_enabled = self.notification_manager.sound_enabled

            # 切換狀態
            new_enabled = not current_enabled
            self.notification_manager.set_sound_enabled(new_enabled)

            if new_enabled:
                print("🔔 鈴聲通知已開啟")
            else:
                print("🔕 鈴聲通知已關閉")

            # 更新圖示顯示
            self._update_notification_icon()

        except Exception as e:
            print(f"切換鈴聲通知狀態失敗: {e}")

    def _update_notification_icon(self):
        """🆕 更新鈴聲通知圖示顯示"""
        try:
            if not hasattr(self, 'notification_icon') or not self.notification_icon:
                return

            # 根據當前通知狀態更新圖示
            if self.notification_manager.sound_enabled:
                self.notification_icon.config(text="🔔", fg=AppConfig.COLORS['text_color'])  # 開啟圖示，正常顏色
            else:
                self.notification_icon.config(text="🔕", fg='#888888')  # 關閉圖示，灰色

        except Exception as e:
            print(f"更新鈴聲通知圖示失敗: {e}")

    def _create_minimal_display(self):
        """建立極簡跑馬燈顯示 - 使用第二個版本的樣式"""
        # 跑馬燈容器
        self.display_container = tk.Frame(
            self.marquee_container,
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

        # 當前顯示的標籤
        self.current_label = tk.Label(
            self.content_area,
            text="即將到期：無資料",
            bg='#F5F5F5',
            fg='#666666',
            font=('SimHei', 10, 'bold'),
            anchor='w',
            cursor='hand2'
        )
        self.current_label.bind('<Button-1>', self._on_display_click)

        # 下一個標籤（用於由下往上滾動動畫）
        self.next_label = tk.Label(
            self.content_area,
            text="",
            bg='#F5F5F5',
            fg='#666666',
            font=('SimHei', 10, 'bold'),
            anchor='w'
        )

        # 初始位置：當前標籤正常位置，下一個標籤在下方待命
        self.current_label.place(x=5, y=0, relwidth=0.95, relheight=1.0)
        self.next_label.place(x=5, y=25, relwidth=0.95, relheight=1.0)

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

    def set_case_data(self, case_data: List):
        """更新案件資料"""
        self.case_data = case_data
        self._update_display()

    def _update_display(self):
        """更新顯示 - 包含明天案件檢查"""
        if not self.case_data:
            self.upcoming_stages = []
        else:
            # 更新即將到期階段
            self.upcoming_stages = DateReminderManager.get_upcoming_stages(
                self.case_data, self.days_ahead
            )

        # 智慧重置索引邏輯
        if self.selected_case_id and self.upcoming_stages:
            for i, stage_info in enumerate(self.upcoming_stages):
                if stage_info['case'].case_id == self.selected_case_id:
                    self.current_index = i
                    self.selected_case_index = i
                    break
            else:
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
        """更新當前顯示 - 🆕 增加明天案件檢測和鈴聲提醒"""
        if not self.upcoming_stages:
            self.current_label.config(
                text="即將到期：無資料",
                fg='#AAAAAA',
                bg='#F5F5F5'
            )
            self.display_container.config(bg='#F5F5F5')
            self.content_area.config(bg='#F5F5F5')

            # 無資料時隱藏鈴鐺
            self._hide_bell_popup()
            self.current_showing_tomorrow = False
            self.last_checked_case_id = None
            return

        # 取得當前要顯示的項目
        stage_info = self.upcoming_stages[self.current_index]

        # 格式化顯示文字 - 使用第二個版本的格式
        display_text = self._format_simple_display(stage_info)

        # 設定顏色 - 使用第二個版本的極簡風格
        bg_color, fg_color = self._get_minimal_colors(stage_info)

        self.current_label.config(
            text=display_text,
            fg=fg_color,
            bg=bg_color
        )
        self.display_container.config(bg=bg_color)
        self.content_area.config(bg=bg_color)

        # 🆕 檢查是否為明天的案件 - 來自第一個版本的功能
        self._check_tomorrow_case_display(stage_info)

    def _check_tomorrow_case_display(self, stage_info):
        """🔥 修正：檢查明天案件顯示，檢查鈴聲通知開關"""
        try:
            # 🔥 新增：檢查鈴聲通知是否開啟
            if not self.notification_manager.sound_enabled:
                # 如果鈴聲通知關閉，隱藏任何現有的鈴鐺彈出視窗
                if self.bell_popup_window:
                    self._hide_bell_popup()
                self.current_showing_tomorrow = False
                self.last_checked_case_id = None
                return

            # 🔥 重要：如果展開視窗已開啟，不顯示鈴鐺
            if self.is_expanded:
                return

            tomorrow = datetime.now().date() + timedelta(days=1)
            is_tomorrow_case = stage_info['stage_date'] == tomorrow
            current_case_id = stage_info['case'].case_id

            if is_tomorrow_case and (not self.current_showing_tomorrow or self.last_checked_case_id != current_case_id):
                # 🔔 顯示明天案件時，彈出鈴鐺標籤並播放音效
                self.current_showing_tomorrow = True
                self.last_checked_case_id = current_case_id
                self._show_tomorrow_bell_popup(stage_info)
                self._play_tomorrow_notification_sound()
                print(f"觸發明天案件提醒：{stage_info['client']} - {stage_info['stage_name']}")

            elif not is_tomorrow_case and self.current_showing_tomorrow:
                # 🔕 不是明天案件時，隱藏鈴鐺標籤
                self.current_showing_tomorrow = False
                self.last_checked_case_id = None
                self._hide_bell_popup()
                print("隱藏明天案件提醒鈴鐺")

        except Exception as e:
            print(f"檢查明天案件顯示失敗: {e}")

    def _show_tomorrow_bell_popup(self, stage_info):
        """🔥 修正：顯示明天案件鈴鐺，增加鈴聲通知開關檢查"""
        try:
            # 🔥 新增：檢查鈴聲通知是否開啟
            if not self.notification_manager.sound_enabled:
                print("🔕 鈴聲通知已關閉，跳過鈴鐺彈出視窗")
                return

            # 🔥 重要：如果展開視窗已開啟，不顯示鈴鐺
            if self.is_expanded:
                return

            # 先關閉現有的彈出視窗
            self._hide_bell_popup()

            # 創建鈴鐺彈出標籤
            self.bell_popup_window = tk.Toplevel(self.parent_window)
            self.bell_popup_window.overrideredirect(True)
            self.bell_popup_window.attributes('-topmost', True)
            # 設定標籤樣式
            popup_bg = '#FFB000'
            popup_fg = '#383838'

            # 主容器
            popup_frame = tk.Frame(
                self.bell_popup_window,
                bg=popup_bg,
                relief='solid',
                borderwidth=0
            )
            popup_frame.pack(fill='both', expand=True)

            # 內容容器
            content_frame = tk.Frame(popup_frame, bg=popup_bg)
            content_frame.pack(fill='both', expand=True, pady=(0,0))

            # 大鈴鐺圖示
            bell_label = tk.Label(
                content_frame,
                text="🔔",
                bg=popup_bg,
                fg=popup_fg,
                font=('Arial',17, 'bold')
            )
            bell_label.pack(side='top', pady=(0, 0))

            # 提醒文字
            client_name = stage_info['client'][:4] + '...' if len(stage_info['client']) > 4 else stage_info['client']
            message = f"明日案件 {client_name}"

            message_label = tk.Label(
                content_frame,
                text=message,
                bg=popup_bg,
                fg=popup_fg,
                font=('SimHei', 9, 'bold'),
                justify='center'
            )
            message_label.pack(side='top',padx=0,pady=(0,4))

            # 定位彈出標籤
            self._position_tomorrow_bell_popup()

            # 🔥 修正：點擊鈴鐺標籤可展開詳細列表，增加延遲處理
            def on_bell_popup_click(event):
                print("鈴鐺被點擊，準備展開")
                self._hide_bell_popup()
                # 🔥 關鍵：給足夠時間讓鈴鐺視窗完全銷毀再展開
                self.main_frame.after(100, self._show_expanded_window)

            for widget in [popup_frame, content_frame, bell_label, message_label]:
                widget.bind('<Button-1>', on_bell_popup_click)

            # 設定自動消失
            self.bell_popup_job = self.bell_popup_window.after(4500, self._hide_bell_popup)

        except Exception as e:
            print(f"顯示明天案件鈴鐺失敗: {e}")
            import traceback
            traceback.print_exc()

    def _position_tomorrow_bell_popup(self):
        """🆕 定位明天案件的鈴鐺彈出標籤"""
        try:
            # 更新跑馬燈的幾何資訊
            self.display_container.update_idletasks()

            # 取得跑馬燈的位置
            marquee_x = self.display_container.winfo_rootx()
            marquee_y = self.display_container.winfo_rooty()
            marquee_width = self.display_container.winfo_width()
            marquee_height = self.display_container.winfo_height()

            # 設定彈出標籤大小
            popup_width = 100
            popup_height = 50

            # 計算彈出位置（在跑馬燈右側）
            popup_x = marquee_x + marquee_width + 10
            popup_y = marquee_y + (marquee_height // 2) - (popup_height // 2)

            # 確保不超出螢幕範圍
            screen_width = self.bell_popup_window.winfo_screenwidth()
            screen_height = self.bell_popup_window.winfo_screenheight()

            if popup_x + popup_width > screen_width:
                # 如果右側空間不足，顯示在左側
                popup_x = marquee_x - popup_width - 10

            if popup_y < 0:
                popup_y = 5
            elif popup_y + popup_height > screen_height:
                popup_y = screen_height - popup_height - 5

            self.bell_popup_window.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")

        except Exception as e:
            print(f"定位鈴鐺彈出標籤失敗: {e}")
            # 使用預設位置
            self.bell_popup_window.geometry(f"80x70+250+100")

    def _hide_bell_popup(self):
        """🔥 修正：隱藏鈴鐺彈出標籤，增強清理邏輯"""
        try:
            # 取消自動消失任務
            if self.bell_popup_job:
                try:
                    self.main_frame.after_cancel(self.bell_popup_job)
                except:
                    pass
                self.bell_popup_job = None

            # 銷毀彈出視窗
            if self.bell_popup_window:
                try:
                    self.bell_popup_window.destroy()
                except:
                    pass
                self.bell_popup_window = None

            print("鈴鐺彈出視窗已隱藏")

        except Exception as e:
            print(f"隱藏鈴鐺彈出視窗失敗: {e}")
            # 強制重置狀態
            self.bell_popup_window = None
            self.bell_popup_job = None

    def _play_tomorrow_notification_sound(self):
        """🆕 播放明天案件提醒音效，檢查鈴聲通知開關"""
        try:
            # 🔥 新增：檢查鈴聲通知是否開啟
            if not self.notification_manager.sound_enabled:
                print("🔕 鈴聲通知已關閉，跳過音效播放")
                return

            # 🔥 修正：使用通知管理器播放音效
            self.notification_manager._play_sound('tomorrow_reminder')
            print(f"播放明天案件提醒音效 - {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"播放明天案件音效失敗: {e}")

    def _get_minimal_colors(self, stage_info: Dict[str, Any]) -> tuple:
        """取得極簡風格的顏色 - 使用第二個版本的樣式"""
        if stage_info['is_overdue']:
            return ('white', '#383838')  # 極淺紅背景，深文字
        elif stage_info['is_today']:
            return ('white', '#383838')  # 極淺橙背景，深文字
        elif stage_info['days_until'] <= 1:
            return ('white', '#383838')  # 極淺黃背景，深文字
        else:
            return ('white', '#383838')    # 預設淺灰背景，深文字

    def _format_simple_display(self, stage_info: Dict[str, Any]) -> str:
        """格式化簡單顯示文字 - 使用第二個版本的格式"""
        date_str = stage_info['stage_date'].strftime('%m/%d')

        # 極簡格式：日期 時間 當事人 階段
        if stage_info['stage_time']:
            display_text = f"{date_str} {stage_info['stage_time']} {stage_info['client'][:6]} {stage_info['stage_name']}"
        else:
            display_text = f"{date_str} {stage_info['client'][:6]} {stage_info['stage_name']}"

        return display_text

    def _start_scroll(self):
        """開始滾動效果"""
        try:
            # 檢查組件是否仍然存在
            if not hasattr(self, 'current_label') or not self.current_label:
                return

            try:
                self.current_label.winfo_exists()
            except:
                return

            self._stop_scroll()

            if not self.upcoming_stages or len(self.upcoming_stages) <= 1:
                return

            if not self.is_expanded:
                scroll_interval = 5000  # 5秒切換一次
                self.scroll_job = self.current_label.after(scroll_interval, self._on_scroll_timer)
        except Exception as e:
            print(f"開始滾動失敗: {e}")


    def _stop_scroll(self):
        """停止滾動效果"""
        if self.scroll_job:
            self.current_label.after_cancel(self.scroll_job)
            self.scroll_job = None

    def _on_scroll_timer(self):
        """滾動計時器回調"""
        if not self.is_expanded and self.upcoming_stages and len(self.upcoming_stages) > 1:
            # 更新索引
            self.current_index = (self.current_index + 1) % len(self.upcoming_stages)

            # 執行由下往上滾動動畫
            self._animate_scroll_up()

            # 設定下一次滾動
            scroll_interval = 5000
            self.scroll_job = self.current_label.after(scroll_interval, self._on_scroll_timer)

    def _animate_scroll_up(self):
        """執行由下往上的滾動動畫 - 使用第二個版本的動畫"""
        if not self.upcoming_stages or len(self.upcoming_stages) <= 1:
            return

        # 準備下一個項目
        next_stage_info = self.upcoming_stages[self.current_index]  # 當前要顯示的項目
        next_text = self._format_simple_display(next_stage_info)

        # 設定顏色
        bg_color, fg_color = self._get_minimal_colors(next_stage_info)

        # 設定下一個標籤
        self.next_label.config(
            text=next_text,
            fg=fg_color,
            bg=bg_color
        )

        # 開始流暢的由下往上動畫 - 15步，每步約1.7像素
        self._smooth_scroll_up_animation(0, 15, bg_color)

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

        # 🆕 檢查新顯示的項目是否為明天案件
        if self.upcoming_stages and 0 <= self.current_index < len(self.upcoming_stages):
            self._check_tomorrow_case_display(self.upcoming_stages[self.current_index])

    def _on_display_click(self, event):
        """🔥 修正：點擊跑馬燈顯示區域，解決明天案件展開衝突"""
        try:
            print("跑馬燈被點擊")

            if not self.upcoming_stages:
                print("無案件資料，無法展開")
                return

            # 🔥 關鍵修正：先強制隱藏鈴鐺彈出視窗，避免衝突
            if self.bell_popup_window:
                print("檢測到鈴鐺彈出視窗，先隱藏")
                self._hide_bell_popup()
                # 給一點時間讓鈴鐺視窗完全銷毀
                self.main_frame.after(50, self._show_expanded_window)
            else:
                # 沒有鈴鐺彈出視窗，直接展開
                self._show_expanded_window()

        except Exception as e:
            print(f"處理點擊事件失敗: {e}")
            import traceback
            traceback.print_exc()

    def _show_expanded_window(self):
        """🔥 修正：顯示展開視窗，增強衝突處理"""
        try:
            # 🔥 修正：檢查是否已經展開或無資料
            if self.is_expanded:
                print("視窗已展開，跳過")
                return

            if not self.upcoming_stages:
                print("無案件資料，無法展開")
                return

            # 🔥 重要：確保鈴鐺彈出視窗已完全清理
            if self.bell_popup_window:
                print("強制清理殘留的鈴鐺彈出視窗")
                self._hide_bell_popup()
                # 等待一個frame的時間確保清理完成
                self.main_frame.after(10, self._actually_show_expanded_window)
                return

            self._actually_show_expanded_window()

        except Exception as e:
            print(f"顯示展開視窗失敗: {e}")
            import traceback
            traceback.print_exc()

    # views/date_reminder_widget.py - 修正展開功能的關鍵部分
# 🔥 解決明天案件無法展開的問題

    def _on_display_click(self, event):
        """🔥 修正：點擊跑馬燈顯示區域，解決明天案件展開衝突"""
        try:
            print("跑馬燈被點擊")

            if not self.upcoming_stages:
                print("無案件資料，無法展開")
                return

            # 🔥 關鍵修正：先強制隱藏鈴鐺彈出視窗，避免衝突
            if self.bell_popup_window:
                print("檢測到鈴鐺彈出視窗，先隱藏")
                self._hide_bell_popup()
                # 給一點時間讓鈴鐺視窗完全銷毀
                self.main_frame.after(50, self._show_expanded_window)
            else:
                # 沒有鈴鐺彈出視窗，直接展開
                self._show_expanded_window()

        except Exception as e:
            print(f"處理點擊事件失敗: {e}")
            import traceback
            traceback.print_exc()

    def _show_expanded_window(self):
        """🔥 修正：顯示展開視窗，增強衝突處理"""
        try:
            # 🔥 修正：檢查是否已經展開或無資料
            if self.is_expanded:
                print("視窗已展開，跳過")
                return

            if not self.upcoming_stages:
                print("無案件資料，無法展開")
                return

            # 🔥 重要：確保鈴鐺彈出視窗已完全清理
            if self.bell_popup_window:
                print("強制清理殘留的鈴鐺彈出視窗")
                self._hide_bell_popup()
                # 等待一個frame的時間確保清理完成
                self.main_frame.after(10, self._actually_show_expanded_window)
                return

            self._actually_show_expanded_window()

        except Exception as e:
            print(f"顯示展開視窗失敗: {e}")
            import traceback
            traceback.print_exc()

    def _actually_show_expanded_window(self):
        """🔥 新增：實際執行展開視窗的邏輯"""
        try:
            print("開始創建展開視窗")

            # 停止滾動
            self._stop_scroll()

            # 創建展開視窗
            self.expanded_window = tk.Toplevel(self.parent_window)
            self.expanded_window.configure(bg='#F8F8F8')
            self.expanded_window.overrideredirect(True)
            self.expanded_window.attributes('-topmost', True)

            # 🔥 重要：設定視窗焦點策略
            self.expanded_window.focus_set()

            # 計算位置（在跑馬燈下方）
            self._position_expanded_window()

            # 創建展開內容
            self._create_expanded_content()

            # 🔥 修正：設定點擊外部關閉的事件處理
            self._setup_expanded_window_events()

            # 設定展開狀態
            self.is_expanded = True

            print("展開視窗創建完成")

        except Exception as e:
            print(f"實際創建展開視窗失敗: {e}")
            import traceback
            traceback.print_exc()
            # 如果創建失敗，重置狀態
            self.is_expanded = False
            if self.expanded_window:
                try:
                    self.expanded_window.destroy()
                except:
                    pass
                self.expanded_window = None

    def _setup_expanded_window_events(self):
        """🔥 新增：設定展開視窗的事件處理"""
        try:
            # 🔥 重要：使用更穩定的焦點事件處理
            def on_focus_out(event):
                # 檢查焦點是否轉移到展開視窗的子元件
                try:
                    focused_widget = self.expanded_window.focus_get()
                    if focused_widget and str(focused_widget).startswith(str(self.expanded_window)):
                        # 焦點還在展開視窗內，不關閉
                        return
                    # 焦點離開展開視窗，關閉視窗
                    self._close_expanded_window()
                except:
                    # 如果檢查失敗，為安全起見還是關閉視窗
                    self._close_expanded_window()

            # 綁定失去焦點事件（延遲觸發，避免誤關閉）
            self.expanded_window.bind('<FocusOut>', lambda e: self.expanded_window.after(100, lambda: on_focus_out(e)))

            # 🔥 新增：點擊Escape鍵關閉
            self.expanded_window.bind('<Escape>', lambda e: self._close_expanded_window())

            # 🔥 新增：綁定全局點擊事件（可選）
            self.expanded_window.bind('<Button-1>', self._on_expanded_window_click)

        except Exception as e:
            print(f"設定展開視窗事件失敗: {e}")

    def _on_expanded_window_click(self, event):
        """🔥 新增：處理展開視窗內的點擊事件"""
        # 如果點擊的是視窗邊緣或空白區域，關閉視窗
        if event.widget == self.expanded_window:
            self._close_expanded_window()

    def _position_expanded_window(self):
        """定位展開視窗"""
        try:
            self.display_container.update_idletasks()
            x = self.display_container.winfo_rootx()
            y = self.display_container.winfo_rooty() + self.display_container.winfo_height() + 5

            # 確保視窗不超出螢幕範圍
            screen_width = self.expanded_window.winfo_screenwidth()
            screen_height = self.expanded_window.winfo_screenheight()

            if x + 200 > screen_width:
                x = screen_width - 200
            if y + 250 > screen_height:
                y = y - 250 - self.display_container.winfo_height() - 10

            self.expanded_window.geometry(f"200x250+{x}+{y}")
        except:
            self.expanded_window.geometry("200x250+100+100")

    def _create_expanded_content(self):
        """創建展開視窗內容"""
        # 標題列
        header_frame = tk.Frame(self.expanded_window, bg='#F8F8F8')
        header_frame.pack(fill='x', pady=5, padx=5)

        header_label = tk.Label(
            header_frame,
            text=f"未來 {self.days_ahead} 天內到期",
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
        """更新展開視窗內容"""
        # 清空現有顯示
        for widget in self.expanded_scroll_frame.winfo_children():
            widget.destroy()

        if not self.upcoming_stages:
            no_data_label = tk.Label(
                self.expanded_scroll_frame,
                text="無即將到期的案件",
                bg='white',
                fg='#999999',
                font=('SimHei', 9)
            )
            no_data_label.pack(pady=20)
            return

        # 顯示案件列表
        for i, stage_info in enumerate(self.upcoming_stages):
            self._create_expanded_item(stage_info, i)

    def _create_expanded_item(self, stage_info: Dict[str, Any], index: int):
        """建立展開列表項目"""
        # 項目容器
        item_frame = tk.Frame(
            self.expanded_scroll_frame,
            bg='white' if index != self.current_index else '#E3F2FD',
            relief='flat',
            borderwidth=0
        )
        item_frame.pack(fill='x', pady=1)

        # 狀態指示器
        status_color = '#FF4444' if stage_info['is_overdue'] else '#FF8800' if stage_info['is_today'] else '#4CAF50'
        status_indicator = tk.Label(
            item_frame,
            text="●",
            bg=item_frame.cget('bg'),
            fg=status_color,
            font=('Arial', 10)
        )
        status_indicator.pack(side='left', padx=(5, 3))

        # 內容標籤 - 使用第二個版本的格式
        content_text = f"{stage_info['client'][:8]}{'...' if len(stage_info['client']) > 8 else ''}\n{stage_info['stage_name'][:10]}{'...' if len(stage_info['stage_name']) > 10 else ''}"

        content_label = tk.Label(
            item_frame,
            text=content_text,
            bg=item_frame.cget('bg'),
            fg='#333333',
            font=('SimHei', 10),
            justify='left',
            anchor='w'
        )
        content_label.pack(side='left', fill='x', expand=True, padx=(0, 5))

        # 日期標籤
        if stage_info['is_overdue']:
            date_text = "逾期"
            date_color = '#FF4444'
        elif stage_info['is_today']:
            date_text = "今日"
            date_color = '#FF8800'
        elif stage_info['days_until'] == 1:
            date_text = "明日"
            date_color = '#FFAA00'
        else:
            date_text = f"{stage_info['days_until']}天"
            date_color = '#666666'

        date_label = tk.Label(
            item_frame,
            text=date_text,
            bg=item_frame.cget('bg'),
            fg=date_color,
            font=('SimHei', 10, 'bold')
        )
        date_label.pack(side='right', padx=(5, 5))

        # 綁定點擊事件
        def on_item_click(event, idx=index):
            self.current_index = idx
            self.selected_case_index = idx
            self.selected_case_id = stage_info['case'].case_id
            self._close_expanded_window()

            # 如果有案件選擇回調，呼叫它
            if self.on_case_select:
                self.on_case_select(stage_info['case'])

        for widget in [item_frame, status_indicator, content_label, date_label]:
            widget.bind('<Button-1>', on_item_click)
            widget.config(cursor='hand2')

    def _close_expanded_window(self):
        """🔥 修正：關閉展開視窗，增強清理邏輯"""
        try:
            print("關閉展開視窗")

            if self.expanded_window:
                self.expanded_window.destroy()
                self.expanded_window = None

            self.is_expanded = False

            # 🔥 重要：展開視窗關閉後，如果當前顯示明天案件，重新檢查是否需要顯示鈴鐺
            self._check_if_need_show_bell_after_expand_close()

            # 重新開始滾動
            self._start_scroll()

            print("展開視窗已關閉")

        except Exception as e:
            print(f"關閉展開視窗失敗: {e}")
            # 強制重置狀態
            self.expanded_window = None
            self.is_expanded = False

    def _check_if_need_show_bell_after_expand_close(self):
        """🔥 修正：展開視窗關閉後檢查是否需要重新顯示鈴鐺，檢查鈴聲通知開關"""
        try:
            # 🔥 新增：檢查鈴聲通知是否開啟
            if not self.notification_manager.sound_enabled:
                print("🔕 鈴聲通知已關閉，跳過展開後鈴鐺檢查")
                return

            if not self.upcoming_stages or self.is_expanded:
                return

            # 取得當前顯示的項目
            if 0 <= self.current_index < len(self.upcoming_stages):
                stage_info = self.upcoming_stages[self.current_index]
                tomorrow = datetime.now().date() + timedelta(days=1)
                is_tomorrow_case = stage_info['stage_date'] == tomorrow

                # 如果當前顯示的是明天案件，重新顯示鈴鐺（但不播放音效）
                if is_tomorrow_case:
                    print("展開關閉後重新檢查明天案件鈴鐺顯示")
                    # 延遲一點時間再顯示鈴鐺，避免立即衝突
                    self.main_frame.after(500, lambda: self._show_tomorrow_bell_popup_silent(stage_info))

        except Exception as e:
            print(f"檢查鈴鐺重新顯示失敗: {e}")

    def _on_notification_state_changed(self, old_enabled: bool, new_enabled: bool):
        """🆕 鈴聲通知狀態變更回調"""
        try:
            print(f"鈴聲通知狀態變更: {old_enabled} -> {new_enabled}")

            # 如果鈴聲通知被關閉，立即隱藏所有彈出視窗
            if not new_enabled:
                if self.bell_popup_window:
                    print("鈴聲通知關閉，隱藏鈴鐺彈出視窗")
                    self._hide_bell_popup()
                self.current_showing_tomorrow = False
                self.last_checked_case_id = None

            # 更新圖示顯示
            self._update_notification_icon()

        except Exception as e:
            print(f"處理鈴聲通知狀態變更失敗: {e}")

    def _show_tomorrow_bell_popup_silent(self, stage_info):
        """🔥 修正：靜默顯示明天案件鈴鐺（不播放音效），檢查鈴聲通知開關"""
        try:
            # 🔥 新增：檢查鈴聲通知是否開啟
            if not self.notification_manager.sound_enabled:
                print("🔕 鈴聲通知已關閉，跳過靜默鈴鐺彈出視窗")
                return

            # 檢查是否還是明天案件且沒有其他彈出視窗
            if self.is_expanded or self.bell_popup_window:
                return

            tomorrow = datetime.now().date() + timedelta(days=1)
            if stage_info['stage_date'] != tomorrow:
                return

            print("靜默重新顯示明天案件鈴鐺")

            # 創建鈴鐺彈出標籤（與原方法相同，但不播放音效）
            self.bell_popup_window = tk.Toplevel(self.parent_window)
            self.bell_popup_window.overrideredirect(True)
            self.bell_popup_window.attributes('-topmost', True)

            # 設定標籤樣式
            popup_bg = '#FFB000'
            popup_fg = '#383838'

            # 主容器
            popup_frame = tk.Frame(
                self.bell_popup_window,
                bg=popup_bg,
                relief='solid',
                borderwidth=0
            )
            popup_frame.pack(fill='both', expand=True)

            # 內容容器
            content_frame = tk.Frame(popup_frame, bg=popup_bg)
            content_frame.pack(fill='both', expand=True, pady=(0,0))

            # 大鈴鐺圖示
            bell_label = tk.Label(
                content_frame,
                text="🔔",
                bg=popup_bg,
                fg=popup_fg,
                font=('Arial',17, 'bold')
            )
            bell_label.pack(side='top', pady=(0, 0))

            # 提醒文字
            client_name = stage_info['client'][:4] + '...' if len(stage_info['client']) > 4 else stage_info['client']
            message = f"明日案件 {client_name}"

            message_label = tk.Label(
                content_frame,
                text=message,
                bg=popup_bg,
                fg=popup_fg,
                font=('SimHei', 9, 'bold'),
                justify='center'
            )
            message_label.pack(side='top',padx=0,pady=(0,4))

            # 定位彈出標籤
            self._position_tomorrow_bell_popup()

            # 🔥 重要：點擊鈴鐺標籤可展開詳細列表
            def on_bell_popup_click(event):
                self._hide_bell_popup()
                # 延遲一點再展開，確保鈴鐺視窗完全銷毀
                self.main_frame.after(50, self._show_expanded_window)

            for widget in [popup_frame, content_frame, bell_label, message_label]:
                widget.bind('<Button-1>', on_bell_popup_click)

            # 設定自動消失
            self.bell_popup_job = self.bell_popup_window.after(4500, self._hide_bell_popup)

        except Exception as e:
            print(f"靜默顯示鈴鐺失敗: {e}")

    def clear_selection(self):
        """🆕 清除選擇狀態"""
        try:
            self.selected_case_index = None
            self.selected_case_id = None
            print("DateReminderWidget 選擇狀態已清除")
        except Exception as e:
            print(f"清除選擇狀態失敗: {e}")

    def update_case_data(self, case_data: List = None):
        """
        🔥 新增：更新案件資料並刷新顯示

        Args:
            case_data: 新的案件資料列表
        """
        try:
            print(f"DateReminderWidget.update_case_data 被調用，案件數量: {len(case_data) if case_data else 0}")

            # 更新案件資料
            self.case_data = case_data or []

            # 重新計算即將到期的階段
            self._calculate_upcoming_stages()

            # 強制刷新顯示
            self._force_refresh_display()

            print(f"案件資料已更新，即將到期階段數量: {len(self.upcoming_stages)}")

        except Exception as e:
            print(f"更新案件資料失敗: {e}")
            import traceback
            traceback.print_exc()

    def set_selected_case(self, case_id: str):
        """
        🔥 新增：設定選中的案件（保持選擇狀態）

        Args:
            case_id: 案件ID
        """
        try:
            self.selected_case_id = case_id
            print(f"DateReminderWidget 設定選中案件: {case_id}")

            # 更新顯示以反映選擇狀態
            self._update_display()

        except Exception as e:
            print(f"設定選中案件失敗: {e}")

    def _calculate_upcoming_stages(self):
        """
        🔥 新增：計算即將到期的階段
        """
        try:
            from utils.date_reminder import DateReminderManager

            self.upcoming_stages = DateReminderManager.get_upcoming_stages(
                self.case_data,
                self.days_ahead
            )

            print(f"重新計算即將到期階段，數量: {len(self.upcoming_stages)}")

        except Exception as e:
            print(f"計算即將到期階段失敗: {e}")
            self.upcoming_stages = []

    def _update_display_no_interrupt(self):
        """
        🔥 修正：不中斷的顯示更新（避免跳躍）
        """
        try:
            # 保存當前狀態
            current_index = getattr(self, 'current_index', 0)

            # 重新計算階段
            self._calculate_upcoming_stages()

            # 調整索引以避免越界
            if self.upcoming_stages:
                self.current_index = min(current_index, len(self.upcoming_stages) - 1)
            else:
                self.current_index = 0

            # 更新顯示
            self._update_display()

        except Exception as e:
            print(f"不中斷更新顯示失敗: {e}")

    def get_case_data(self):
        """
        🔥 新增：取得當前案件資料

        Returns:
            List: 當前案件資料列表
        """
        return self.case_data

    def refresh_data(self):
        """
        🔥 新增：從控制器重新載入資料
        """
        try:
            if hasattr(self, 'case_controller') and self.case_controller:
                self.case_data = self.case_controller.get_cases()
                self._calculate_upcoming_stages()
                self._force_refresh_display()
                print(f"從控制器重新載入案件資料: {len(self.case_data)} 個案件")
            else:
                print("警告：無法從控制器重新載入資料")

        except Exception as e:
            print(f"重新載入資料失敗: {e}")

    def set_case_controller(self, case_controller):
        """
        🔥 新增：設定案件控制器引用

        Args:
            case_controller: 案件控制器實例
        """
        try:
            self.case_controller = case_controller
            print("DateReminderWidget 已設定案件控制器")

            # 立即載入最新資料
            if case_controller:
                self.refresh_data()

        except Exception as e:
            print(f"設定案件控制器失敗: {e}")