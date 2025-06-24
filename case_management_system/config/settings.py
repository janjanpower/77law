class AppConfig:
    """應用程式設定"""

    # 顏色設定
    COLORS = {
        'window_bg': '#383838',
        'title_bg': '#8B8B8B',
        'title_fg': 'white',
        'button_bg': '#8B8B8B',
        'button_fg': 'white',
        'button_hover': '#A0A0A0',
        'text_color': 'white',
        'border_color': '#555555'
    }

    # 尺寸設定
    SIZES = {
        # 固定按鈕尺寸
        'dialog_button': {'width': 80, 'height': 30},
        'function_button': {'width': 50, 'height': 15},

        # 視窗最小尺寸
        'min_window': {'width': 800, 'height': 600},

        # 標題列高度
        'title_height': 25,

        # 邊距
        'padding': 20,
        'button_spacing': 10
    }

    # 案件欄位設定 (移除進度追蹤欄位)
    CASE_FIELDS = {
        'case_type': {'name': '案件類型', 'width': 100, 'visible': True},
        'client': {'name': '當事人', 'width': 150, 'visible': True},
        'lawyer': {'name': '委任律師', 'width': 120, 'visible': True},
        'legal_affairs': {'name': '法務', 'width': 100, 'visible': True}
    }

    # 預設視窗設定
    DEFAULT_WINDOW = {
        'title': '案件管理系統',
        'width': 400,
        'height': 600,
        'resizable': True
    }