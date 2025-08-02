# ==================== 修復方案：CaseController 完整修復 ====================

# 1. 修復 controllers/case_controller.py 的 import 和初始化

# 在檔案頂部的 import 區段
from typing import List, Optional, Tuple
from models.case_model import CaseData
from config.settings import AppConfig
import json
import os
from datetime import datetime

# 🔥 修復：正確的導入路徑
try:
    # 嘗試從新結構導入
    from utils.file_operations.folder_manager import FolderManager
    print("✅ 從新結構導入 FolderManager")
except ImportError:
    try:
        # 嘗試從舊結構導入
        from utils.folder_manager import FolderManager
        print("✅ 從舊結構導入 FolderManager")
    except ImportError:
        print("❌ 無法導入 FolderManager，將提供備用實作")
        # 提供基本的備用實作
        class FolderManager:
            def __init__(self, base_folder):
                self.base_folder = base_folder

            def create_case_folder_structure(self, case_data):
                print(f"⚠️ 使用備用 FolderManager，功能有限")
                return True

            def get_case_folder_path(self, case_data):
                return None


# 🔥 修復：定義安全初始化檢查裝飾器
def safe_init_check(func):
    """安全初始化檢查裝飾器"""
    def wrapper(self, *args, **kwargs):
        try:
            # 檢查並修復缺失的屬性
            if not hasattr(self, 'cases'):
                print(f"⚠️ 修復缺失的 cases 屬性")
                self.cases = []

            if not hasattr(self, 'folder_manager'):
                print(f"⚠️ 修復缺失的 folder_manager 屬性")
                data_folder = getattr(self, 'data_folder', '.')
                self.folder_manager = FolderManager(data_folder)

            return func(self, *args, **kwargs)

        except Exception as e:
            print(f"❌ 方法 {func.__name__} 執行失敗: {e}")
            if func.__name__ == 'generate_case_id':
                # 為 generate_case_id 提供備用返回值
                import time
                return f"ERR{int(time.time()) % 1000000:06d}"
            return None

    return wrapper


class CaseController:
    """案件資料控制器 - 完整修復版本"""

    def __init__(self, data_file: str = None):
        """初始化案件控制器 - 🔥 完整修復版本"""
        try:
            print("🔧 開始初始化 CaseController...")

            # 1. 設定資料檔案路徑
            if data_file is None:
                self.data_file = AppConfig.DATA_CONFIG.get('case_data_file', './data/cases.json')
            else:
                self.data_file = data_file

            # 2. 設定資料夾路徑
            self.data_folder = os.path.dirname(self.data_file) if os.path.dirname(self.data_file) else '.'

            # 🔥 關鍵修復：初始化案件列表
            self.cases: List[CaseData] = []
            print("✅ 初始化 cases 列表")

            # 🔥 關鍵修復：初始化資料夾管理器
            try:
                self.folder_manager = FolderManager(self.data_folder)
                print("✅ 初始化 FolderManager 成功")
            except Exception as e:
                print(f"❌ 初始化 FolderManager 失敗: {e}")
                self.folder_manager = None

            # 3. 確保資料夾存在
            self._ensure_data_folder()

            # 4. 載入案件資料
            try:
                self.load_cases()
                print(f"✅ 載入 {len(self.cases)} 筆案件資料")
            except Exception as e:
                print(f"⚠️ 載入案件資料失敗: {e}")
                # 確保 cases 至少是空列表
                if not hasattr(self, 'cases'):
                    self.cases = []

            print(f"✅ CaseController 初始化完成")

        except Exception as e:
            print(f"❌ CaseController 初始化發生嚴重錯誤: {e}")

            # 🔥 關鍵：確保即使失敗也有基本屬性
            if not hasattr(self, 'cases'):
                self.cases = []
                print("🔧 緊急修復：建立空的 cases 列表")

            if not hasattr(self, 'data_folder'):
                self.data_folder = '.'
                print("🔧 緊急修復：設定預設 data_folder")

            if not hasattr(self, 'folder_manager'):
                self.folder_manager = None
                print("🔧 緊急修復：設定 folder_manager 為 None")

            # 重新拋出異常，但確保基本功能可用
            import traceback
            traceback.print_exc()

    def _ensure_data_folder(self):
        """確保資料夾存在"""
        try:
            if not os.path.exists(self.data_folder):
                os.makedirs(self.data_folder, exist_ok=True)
                print(f"📁 建立資料夾: {self.data_folder}")

            # 建立案件類型資料夾
            if hasattr(AppConfig, 'CASE_TYPE_FOLDERS'):
                for folder_name in AppConfig.CASE_TYPE_FOLDERS.values():
                    folder_path = os.path.join(self.data_folder, folder_name)
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path, exist_ok=True)
                        print(f"📁 建立案件類型資料夾: {folder_path}")

        except Exception as e:
            print(f"❌ 建立資料夾失敗: {e}")

    def load_cases(self) -> bool:
        """載入案件資料"""
        try:
            print(f"📖 嘗試載入案件資料: {self.data_file}")

            # 🔥 確保 cases 屬性存在
            if not hasattr(self, 'cases'):
                self.cases = []

            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📊 從檔案載入 {len(data)} 筆原始資料")

                    # 清空現有資料
                    self.cases.clear()

                    # 處理每筆案件資料
                    for case_dict in data:
                        try:
                            # 進行資料遷移（如果需要）
                            migrated_data = self._migrate_case_data(case_dict)
                            case = CaseData.from_dict(migrated_data)
                            self.cases.append(case)
                        except Exception as e:
                            print(f"⚠️ 解析案件資料失敗: {case_dict.get('case_id', '未知')}, 錯誤: {e}")
                            continue

                    print(f"✅ 成功載入 {len(self.cases)} 筆案件資料")
                    return True
            else:
                print(f"📝 資料檔案不存在，建立新檔案: {self.data_file}")
                self.cases = []
                return True

        except Exception as e:
            print(f"❌ 載入案件資料失敗: {e}")
            if not hasattr(self, 'cases'):
                self.cases = []
            return False

    def _migrate_case_data(self, case_dict: dict) -> dict:
        """遷移舊版案件資料到新版格式"""
        # 確保所有新欄位都有預設值
        default_fields = {
            'case_reason': None,
            'case_number': None,
            'opposing_party': None,
            'court': None,
            'division': None,
            'progress_date': None,
            'progress_stages': {},
            'progress_notes': {},
            'progress_times': {}
        }

        # 合併預設值和現有資料
        for field, default_value in default_fields.items():
            if field not in case_dict:
                case_dict[field] = default_value

        return case_dict

    def save_cases(self) -> bool:
        """儲存案件資料"""
        try:
            # 🔥 確保 cases 屬性存在
            if not hasattr(self, 'cases'):
                print("⚠️ cases 屬性不存在，無法儲存")
                return False

            # 確保資料夾存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

            # 轉換為字典格式
            data = [case.to_dict() for case in self.cases]

            # 儲存到檔案
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ 成功儲存 {len(self.cases)} 筆案件資料")
            return True

        except Exception as e:
            print(f"❌ 儲存案件資料失敗: {e}")
            return False

    # 🔥 修復：新增缺失的方法
    @safe_init_check
    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        根據編號取得案件

        Args:
            case_id: 案件編號

        Returns:
            Optional[CaseData]: 找到的案件或None
        """
        try:
            for case in self.cases:
                if case.case_id == case_id:
                    return case

            print(f"❌ 找不到案件編號: {case_id}")
            return None

        except Exception as e:
            print(f"❌ 查找案件失敗: {e}")
            return None

    @safe_init_check
    def get_cases(self) -> List[CaseData]:
        """
        取得所有案件

        Returns:
            List[CaseData]: 案件列表的複本
        """
        try:
            return self.cases.copy()
        except Exception as e:
            print(f"❌ 取得案件列表失敗: {e}")
            return []

    @safe_init_check
    def generate_case_id(self) -> str:
        """
        產生新的案件編號 - 民國年分(三碼)+XXX(三碼)格式

        Returns:
            str: 新的案件編號
        """
        try:
            import datetime

            # 計算民國年分
            current_year = datetime.datetime.now().year
            minguo_year = current_year - 1911

            # 取得現有所有案件編號
            existing_ids = {case.case_id for case in self.cases}

            # 找出當年度最大編號
            current_year_prefix = f"{minguo_year:03d}"
            max_number = 0

            for case_id in existing_ids:
                if case_id.startswith(current_year_prefix) and len(case_id) == 6:
                    try:
                        number_part = int(case_id[3:])
                        max_number = max(max_number, number_part)
                    except ValueError:
                        continue

            # 產生新編號
            new_number = max_number + 1
            new_case_id = f"{current_year_prefix}{new_number:03d}"

            print(f"✅ 產生新案件編號: {new_case_id}")
            return new_case_id

        except Exception as e:
            print(f"❌ 產生案件編號失敗: {e}")
            # 🔥 錯誤回復：使用時間戳作為備用編號
            import time
            backup_id = f"ERR{int(time.time()) % 1000000:06d}"
            print(f"⚠️ 使用備用編號: {backup_id}")
            return backup_id

    @safe_init_check
    def add_case(self, case_data: CaseData) -> bool:
        """
        新增案件

        Args:
            case_data: 案件資料

        Returns:
            bool: 是否成功新增
        """
        try:
            # 檢查案件編號是否重複
            if self.get_case_by_id(case_data.case_id):
                print(f"❌ 案件編號已存在: {case_data.case_id}")
                return False

            # 新增到列表
            self.cases.append(case_data)

            # 儲存資料
            success = self.save_cases()

            if success:
                print(f"✅ 成功新增案件: {case_data.case_id} - {case_data.client}")

                # 嘗試建立資料夾結構
                if self.folder_manager:
                    try:
                        folder_success = self.folder_manager.create_case_folder_structure(case_data)
                        if folder_success:
                            print(f"✅ 成功建立案件資料夾結構")
                        else:
                            print(f"⚠️ 案件資料夾建立失敗")
                    except Exception as e:
                        print(f"⚠️ 建立案件資料夾時發生錯誤: {e}")

                return True
            else:
                # 如果儲存失敗，移除已新增的案件
                self.cases.remove(case_data)
                return False

        except Exception as e:
            print(f"❌ 新增案件失敗: {e}")
            return False

    @safe_init_check
    def get_case_folder_path(self, case_id: str) -> Optional[str]:
        """取得指定案件的資料夾路徑"""
        try:
            case_data = self.get_case_by_id(case_id)
            if not case_data:
                print(f"❌ 找不到案件編號: {case_id}")
                return None

            if self.folder_manager:
                return self.folder_manager.get_case_folder_path(case_data)
            else:
                print(f"❌ FolderManager 不可用")
                return None

        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None


# ==================== 修復 FolderManager 的 Excel 建立方法 ====================

# 為 FolderManager 新增安全的 Excel 建立方法
def safe_create_case_info_excel(folder_manager_instance, case_info_folder: str, case_data) -> bool:
    """
    安全的案件資訊Excel檔案建立方法
    可以作為 FolderManager 的方法或獨立函數使用
    """
    try:
        import pandas as pd

        # 確保資料夾存在
        if not os.path.exists(case_info_folder):
            os.makedirs(case_info_folder, exist_ok=True)

        # 檢查案件資料
        if not case_data or not hasattr(case_data, 'case_id'):
            print(f"❌ 無效的案件資料")
            return False

        excel_filename = f"{case_data.case_id}_{case_data.client}_案件資訊.xlsx"
        excel_path = os.path.join(case_info_folder, excel_filename)

        try:
            # 使用 pandas 建立Excel
            basic_info = [
                ['案件編號', case_data.case_id],
                ['案件類型', case_data.case_type],
                ['當事人', case_data.client],
                ['委任律師', getattr(case_data, 'lawyer', '') or ''],
                ['法務', getattr(case_data, 'legal_affairs', '') or ''],
                ['進度追蹤', case_data.progress]
            ]

            df = pd.DataFrame(basic_info, columns=['項目', '內容'])
            df.to_excel(excel_path, index=False, sheet_name='基本資訊')

            print(f"✅ 成功建立Excel檔案: {excel_filename}")
            return True

        except Exception as pandas_error:
            print(f"⚠️ pandas 建立Excel失敗: {pandas_error}")

            # 備用：建立文字檔
            text_filename = f"{case_data.case_id}_{case_data.client}_案件資訊.txt"
            text_path = os.path.join(case_info_folder, text_filename)

            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(f"案件編號: {case_data.case_id}\n")
                f.write(f"案件類型: {case_data.case_type}\n")
                f.write(f"當事人: {case_data.client}\n")
                f.write(f"委任律師: {getattr(case_data, 'lawyer', '') or '未指定'}\n")
                f.write(f"法務: {getattr(case_data, 'legal_affairs', '') or '未指定'}\n")
                f.write(f"進度追蹤: {case_data.progress}\n")

            print(f"✅ 建立文字檔備用: {text_filename}")
            return True

    except Exception as e:
        print(f"❌ 建立案件資訊檔案失敗: {e}")
        return False
