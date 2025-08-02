#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class AppConfig:
    """應用程式設定"""

    # 新增：文字截短設定
    TEXT_TRUNCATION = {
        'default_max_length': 50,           # 預設最大長度
        'client_name_length': 8,            # 當事人姓名
        'case_reason_length': 12,           # 案由
        'court_name_length': 6,            # 🔥 新增：負責法院
        'division_name_length': 6,          # 🔥 新增：負責股別
        'case_number_length': 15,           # 案號
        'opposing_party_length': 6,        # 對造
        'popup_width': 400,                 # 彈出視窗寬度
        'popup_max_height': 200             # 彈出視窗最大高度
    }


    VOLUME_SETTINGS = {

        # 🆕 鈴聲通知相關設定
        'notification_enabled_icon': '🔔',   # 通知開啟圖示
        'notification_disabled_icon': '🔕',  # 通知關閉圖示
        'notification_icon_size': 12,        # 通知圖示大小
        'notification_icon_color_disabled': '#888888',  # 通知關閉時的顏色
        'default_notification_enabled': True,  # 預設通知開關狀態
    }

    # 🔥 新增：事件系統配置
    EVENT_CONFIG = {
        'enable_debug_logging': True,
        'max_event_history': 100,
        'event_timeout': 5.0  # 秒
    }

    # 顏色設定
    COLORS = {
        'window_bg': '#383838',
        'title_bg': '#8B8B8B',
        'title_fg': 'white',
        'button_bg': '#8B8B8B',
        'button_fg': 'white',
        'button_hover': '#A0A0A0',
        'text_color': 'white',
        'border_color': '#555555',

        # 🔥 新增：缺少的次要按鈕顏色
        'secondary_button_bg': '#666666',   # 次要按鈕背景色（較暗的灰色）
        'secondary_button_fg': 'white',     # 次要按鈕文字顏色
        'secondary_button_hover': '#777777', # 次要按鈕懸停色

        # 🔥 新增：其他可能需要的顏色
        'success_color': '#4CAF50',         # 成功訊息顏色
        'error_color': '#F44336',           # 錯誤訊息顏色
        'warning_color': '#FF9800',         # 警告訊息顏色
        'info_color': '#2196F3',            # 資訊訊息顏色

        'truncated_text': '#2196F3',        # 可點擊截短文字顏色
        'truncated_hover': '#1976D2',       # 滑鼠懸停顏色
        'popup_bg': '#FFFFFF',              # 彈出視窗背景
        'popup_border': '#E0E0E0',          # 彈出視窗邊框

    }



    # 字體設定 - 統一調整字體大小
    FONTS = {
        'title': ('Microsoft JhengHei', 11, 'bold'),
        'button': ('Microsoft JhengHei', 10),         # 按鈕字體改為 20
        'text': ('Microsoft JhengHei',10),           # 一般文字改為 10
        'welcome': ('Microsoft JhengHei', 11, 'bold')
    }

    # 尺寸設定
    SIZES = {
        'dialog_button': {'width': 80, 'height': 30},
        'function_button': {'width': 50, 'height': 15},
        'min_window': {'width': 300, 'height': 300},
        'title_height': 25,
        'padding': 20,
        'button_spacing': 10
    }

    # 總覽樹狀圖顯示欄位（確保order值正確）
    OVERVIEW_FIELDS = {
        'case_id': {'name': '案件編號', 'width': 100, 'visible': True, 'order': 0},
        'case_type': {'name': '案件類型', 'width': 100, 'visible': True, 'order': 1},
        'client': {'name': '當事人', 'width': 150, 'visible': True, 'order': 2},
        'lawyer': {'name': '委任律師', 'width': 120, 'visible': True, 'order': 3},
        'legal_affairs': {'name': '法務', 'width': 100, 'visible': True, 'order': 4}
    }

    # 案件進度可視化顯示欄位（包含所有詳細資訊）
    PROGRESS_DISPLAY_FIELDS = {
        'case_number': {'name': '案號', 'order': 1},
        'case_reason': {'name': '案由', 'order': 2},
        'opposing_party': {'name': '對造', 'order': 3},
        'court': {'name': '負責法院', 'order': 4},
        'division': {'name': '負責股別', 'order': 5}
    }

    # 預設視窗設定
    DEFAULT_WINDOW = {
        'title': '案件管理系統',
        'width': 200,
        'height': 400,
        'resizable': True
    }

    # 視窗標題設定
    WINDOW_TITLES = {
        'main': '案件管理系統',
        'overview': '案件管理系統 - 總覽',
        'add_case': '案件管理系統 - 新增案件',
        'edit_case': '案件管理系統 - 編輯案件'
    }

    # 資料儲存設定
    DATA_CONFIG = {
        'case_data_file': 'cases_data.json',
        'settings_file': 'app_settings.json'
    }

    # 案件類型選項
    CASE_TYPES = ['刑事', '民事']

    # 根據案件類型的進度選項
    PROGRESS_OPTIONS = {
        '刑事': ['待處理', '偵查中', '起訴', '一審', '二審', '三審', '確定', '執行中', '已結案'],
        '民事': ['待處理', '調解', '一審', '二審', '三審', '確定', '強制執行', '已結案'],
        'default': ['待處理', '一審', '二審', '三審', '合議庭', '已結案']  # 預設選項（向後相容）
    }

    # 案件類型對應的資料夾名稱
    CASE_TYPE_FOLDERS = {
        '刑事': '刑事',
        '民事': '民事'
    }

    @staticmethod
    def format_case_display_name(case_data):
        """格式化案件顯示名稱"""
        if hasattr(case_data, 'case_number') and case_data.case_number:
            return f"{case_data.client} - {case_data.case_number}"
        else:
            return case_data.client

    @staticmethod
    def get_progress_options(case_type):
        """根據案件類型取得進度選項"""
        return AppConfig.PROGRESS_OPTIONS.get(case_type, [])

    @staticmethod
    def validate_color_config():
        """驗證顏色配置完整性"""
        required_colors = [
            'window_bg', 'title_bg', 'title_fg', 'button_bg', 'button_fg',
            'text_color', 'secondary_button_bg', 'secondary_button_fg',
            'border_color'
        ]

        missing_colors = []
        for color in required_colors:
            if color not in AppConfig.COLORS:
                missing_colors.append(color)

        if missing_colors:
            print(f"警告：缺少顏色定義: {missing_colors}")
            return False
        return True