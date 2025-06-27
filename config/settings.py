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

    # 字體設定 - 統一調整字體大小
    FONTS = {
        'title': ('Microsoft JhengHei', 11, 'bold'),
        'button': ('Microsoft JhengHei', 10),         # 按鈕字體改為 20
        'text': ('Microsoft JhengHei',11),           # 一般文字改為 10
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

    @classmethod
    def get_progress_options(cls, case_type: str = None) -> list:
        """
        根據案件類型取得對應的進度選項

        Args:
            case_type: 案件類型 ('刑事' 或 '民事')

        Returns:
            list: 對應的進度選項列表
        """
        if case_type and case_type in cls.PROGRESS_OPTIONS:
            return cls.PROGRESS_OPTIONS[case_type]
        return cls.PROGRESS_OPTIONS['default']

    @classmethod
    def format_case_display_name(cls, case_data) -> str:
        """
        統一的案件顯示名稱格式：case_number(當事人名稱)

        Args:
            case_data: 案件資料物件

        Returns:
            str: 格式化的顯示名稱
        """
        case_number = getattr(case_data, 'case_number', None) or '未設定案號'
        client_name = getattr(case_data, 'client', '未知當事人')
        return f"{case_number}({client_name})"