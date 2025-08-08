# utils/event_manager.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一事件管理器 - 實現觀察者模式
負責協調各個元件之間的資料同步
🔥 修正：統一事件名稱定義，解決跑馬燈更新問題
"""

from typing import Dict, List, Callable, Any
from enum import Enum

class EventType(Enum):
    """事件類型枚舉 - 🔥 修正：統一事件名稱"""
    CASE_ADDED = "case_added"
    CASE_UPDATED = "case_updated"
    CASE_DELETED = "case_deleted"
    STAGE_ADDED = "stage_added"
    STAGE_UPDATED = "stage_updated"
    STAGE_DELETED = "stage_deleted"
    CASES_RELOADED = "cases_reloaded"  # 🔥 統一使用這個事件名稱

    # 🔥 新增：為了向後相容，保留舊名稱但指向同一個值
    CASES_LOADED = "cases_reloaded"  # 指向同一個事件

class EventManager:
    """事件管理器 - 單例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._initialized = True
        print("EventManager 初始化完成")

    def subscribe(self, event_type: EventType, callback: Callable):
        """訂閱事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            print(f"已訂閱事件: {event_type.value}")

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """取消訂閱事件"""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                print(f"已取消訂閱事件: {event_type.value}")

    def publish(self, event_type: EventType, data: Any = None):
        """🔥 修正：發布事件，支援事件別名"""
        # 統一事件處理 - 將 CASES_LOADED 也當作 CASES_RELOADED 處理
        actual_event_type = event_type
        if event_type == EventType.CASES_LOADED:
            actual_event_type = EventType.CASES_RELOADED

        if actual_event_type in self._subscribers:
            print(f"發布事件: {actual_event_type.value}, 訂閱者數量: {len(self._subscribers[actual_event_type])}")

            # 🔥 新增：增強錯誤處理和事件資料驗證
            for callback in self._subscribers[actual_event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"事件回調執行失敗 [{actual_event_type.value}]: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            print(f"事件無訂閱者: {actual_event_type.value}")

    def clear_all(self):
        """清除所有訂閱"""
        self._subscribers.clear()
        print("已清除所有事件訂閱")

    def get_subscribers_count(self, event_type: EventType) -> int:
        """🔥 新增：取得事件訂閱者數量（用於除錯）"""
        return len(self._subscribers.get(event_type, []))

    def list_all_subscriptions(self):
        """🔥 新增：列出所有訂閱資訊（用於除錯）"""
        print("\n=== 事件訂閱狀況 ===")
        for event_type, callbacks in self._subscribers.items():
            print(f"{event_type.value}: {len(callbacks)} 個訂閱者")
            for i, callback in enumerate(callbacks):
                callback_name = getattr(callback, '__name__', str(callback))
                print(f"  {i+1}. {callback_name}")
        print("==================\n")

# 全局事件管理器實例
event_manager = EventManager()