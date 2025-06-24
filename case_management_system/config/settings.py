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

    # 字體設定
    FONTS = {
        'title': ('Microsoft JhengHei', 12, 'bold'),
        'button': ('Microsoft JhengHei', 10),
        'text': ('Microsoft JhengHei', 9),
        'welcome': ('Microsoft JhengHei', 16, 'bold')
    }

    # 案件欄位設定
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

    # 視窗標題設定
    WINDOW_TITLES = {
        'main': '案件管理系統',
        'overview': '案件管理系統 - 總覽',
        'add_case': '案件管理系統 - 新增案件',
        'edit_case': '案件管理系統 - 編輯案件'
    }

    # 資料儲存設定 - 簡化版本
    DATA_CONFIG = {
        'case_data_file': 'cases_data.json',  # 案件資料庫檔案
        'settings_file': 'app_settings.json'  # 應用程式設定檔案
    }

    # 案件類型對應的資料夾名稱
    CASE_TYPE_FOLDERS = {
        '刑事': '刑事',
        '民事': '民事'
    }