# config/marquee_settings.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跑馬燈相關配置設定
統一管理跑馬燈的所有配置參數
"""

class MarqueeConfig:
    """跑馬燈配置管理"""

    # 天數控制設定
    DEFAULT_DAYS_AHEAD = 3
    MIN_DAYS_AHEAD = 1
    MAX_DAYS_AHEAD = 30

    # 顯示設定
    MARQUEE_HEIGHT = 25
    MARQUEE_WIDTH = 200
    SCROLL_INTERVAL = 3000  # 毫秒
    ANIMATION_SPEED = 20    # 毫秒
    ANIMATION_STEP = 2      # 像素

    # 顏色設定
    URGENCY_COLORS = {
        'today': '#FF0000',      # 紅色 - 今天
        'tomorrow': '#FF8C00',   # 橘色 - 明天
        'urgent': '#FFD700',     # 金色 - 3天內
        'normal': '#666666',     # 灰色 - 其他
        'no_data': '#999999'     # 淺灰 - 無資料
    }

    # 背景顏色
    BACKGROUND_COLORS = {
        'container': '#383838',
        'display': '#F5F5F5',
        'border': '#E0E0E0'
    }

    # 鈴聲提醒設定
    BELL_POPUP_SETTINGS = {
        'width': 80,
        'height': 70,
        'bg_color': '#FFB000',  # 金黃色
        'fg_color': 'white',
        'show_duration': 5000,  # 顯示5秒
        'check_interval': 60000  # 每分鐘檢查一次
    }

    # 字體設定
    FONTS = {
        'marquee': ('SimHei', 10, 'bold'),
        'control': ('SimHei', 10, 'bold'),
        'control_arrow': ('Arial', 10),
        'bell_icon': ('Arial', 18, 'bold'),
        'bell_text': ('SimHei', 9, 'bold')
    }

    # 文字截斷設定
    TEXT_LIMITS = {
        'client_name': 4,      # 客戶名稱最大字數
        'stage_name': 6,       # 階段名稱最大字數
        'note_preview': 50     # 備註預覽最大字數
    }

    @staticmethod
    def get_urgency_color(days_remaining: int) -> str:
        """根據剩餘天數取得緊急程度顏色"""
        if days_remaining == 0:
            return MarqueeConfig.URGENCY_COLORS['today']
        elif days_remaining == 1:
            return MarqueeConfig.URGENCY_COLORS['tomorrow']
        elif days_remaining <= 3:
            return MarqueeConfig.URGENCY_COLORS['urgent']
        else:
            return MarqueeConfig.URGENCY_COLORS['normal']

    @staticmethod
    def get_priority_level(days_remaining: int) -> str:
        """取得優先級別名稱"""
        if days_remaining == 0:
            return 'critical'
        elif days_remaining == 1:
            return 'high'
        elif days_remaining <= 3:
            return 'medium'
        elif days_remaining <= 7:
            return 'low'
        else:
            return 'normal'

    @staticmethod
    def validate_days_range(days: int) -> int:
        """驗證並調整天數範圍"""
        if days < MarqueeConfig.MIN_DAYS_AHEAD:
            return MarqueeConfig.MIN_DAYS_AHEAD
        elif days > MarqueeConfig.MAX_DAYS_AHEAD:
            return MarqueeConfig.MAX_DAYS_AHEAD
        else:
            return days

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
        """截斷文字並添加後綴"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + suffix