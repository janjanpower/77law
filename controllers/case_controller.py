#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件控制器 - 修正版本
使用新的 Services 層架構，同時保持向後相容性
"""

from typing import List, Optional, Tuple, Dict, Any
from models.case_model import CaseData
from services.services_controller import ServicesController
from config.settings import AppConfig
import os
from datetime import datetime


class CaseController:
    """案件控制器 - 修正版本（委託給 Services 層 + 向後相容）"""

    def __init__(self, data_folder: str = None):
        """
        初始化案件控制器

        Args:
            data_folder: 資料資料夾路徑
        """
        self.data_folder = data_folder or AppConfig.DATA_CONFIG.get('data_folder', './data')

        # 確保資料夾存在
        os.makedirs(self.data_folder, exist_ok=True)

        # 初始化服務控制器（所有業務邏輯都委託給它）
        self.services = ServicesController(self.data_folder)

        # 向後相容：維護cases屬性用於generate_case_id
        self.cases = []
        self.data_file = os.path.join(self.data_folder, "cases.json")

        # 載入現有案件資料
        self.load_cases()

        print("✅ CaseController 初始化完成 (使用 Services 架構 + 向後相容)")

    # ==================== 資料載入與儲存 ====================

    def load_cases(self) -> bool:
        """載入案件資料（向後相容）"""
        try:
            # 委託給services層載入資料
            self.cases = self.services.case_service.repository.get_all_cases()
            print(f"✅ 成功載入 {len(self.cases)} 筆案件資料")
            return True
        except Exception as e:
            print(f"❌ 載入案件資料失敗: {e}")
            self.cases = []
            return False

    def save_cases(self) -> bool:
        """儲存案件資料（向後相容）"""
        try:
            # 委託給services層儲存資料
            return self.services.case_service.repository._save_data()
        except Exception as e:
            print(f"❌ 儲存案件資料失敗: {e}")
            return False

    # ==================== 案件CRUD操作 ====================

    def add_case(self, case_data: CaseData, create_folder: bool = True,
                 apply_template: str = None) -> bool:
        """
        新增案件

        Args:
            case_data: 案件資料
            create_folder: 是否建立資料夾
            apply_template: 套用的進度範本名稱

        Returns:
            bool: 是否新增成功
        """
        try:
            result = self.services.create_case(case_data, create_folder, apply_template)
            if result[0]:
                print(f"✅ 控制器: 成功新增案件 {case_data.client}")
                # 重新載入cases以保持同步
                self.load_cases()
            else:
                print(f"❌ 控制器: 新增案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.add_case 失敗: {e}")
            return False

    def update_case(self, case_data: CaseData, update_folder: bool = False) -> bool:
        """
        更新案件

        Args:
            case_data: 更新後的案件資料
            update_folder: 是否同步更新資料夾

        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.services.update_case(case_data, update_folder, sync_progress=True)
            if result[0]:
                print(f"✅ 控制器: 成功更新案件 {case_data.case_id}")
                # 重新載入cases以保持同步
                self.load_cases()
            else:
                print(f"❌ 控制器: 更新案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.update_case 失敗: {e}")
            return False

    def delete_case(self, case_id: str, delete_folder: bool = True, force: bool = False) -> bool:
        """
        刪除案件

        Args:
            case_id: 案件ID
            delete_folder: 是否刪除資料夾
            force: 是否強制刪除

        Returns:
            bool: 是否刪除成功
        """
        try:
            result = self.services.delete_case(case_id, delete_folder, delete_progress=True, force=force)
            if result[0]:
                print(f"✅ 控制器: 成功刪除案件 {case_id}")
                # 重新載入cases以保持同步
                self.load_cases()
            else:
                print(f"❌ 控制器: 刪除案件失敗 - {result[1]}")
            return result[0]
        except Exception as e:
            print(f"❌ CaseController.delete_case 失敗: {e}")
            return False

    # ==================== 案件編號生成（向後相容）====================

    def generate_case_id(self, case_type: str = None) -> str:
        """
        產生新的案件編號 - 民國年分(三碼)+XXX(三碼)格式

        Args:
            case_type: 案件類型（可選，用於未來擴展）

        Returns:
            str: 新的案件編號
        """
        try:
            # 計算民國年分
            current_year = datetime.now().year
            minguo_year = current_year - 1911

            # 取得現有所有案件編號
            existing_ids = {case.case_id for case in self.cases if case.case_id}

            # 找出當年度最大編號
            current_year_prefix = f"{minguo_year:03d}"
            max_number = 0

            for case_id in existing_ids:
                if case_id.startswith(current_year_prefix) and len(case_id) == 6:
                    try:
                        number = int(case_id[3:])
                        max_number = max(max_number, number)
                    except ValueError:
                        continue

            # 產生新編號
            new_number = max_number + 1
            new_case_id = f"{current_year_prefix}{new_number:03d}"

            print(f"✅ 產生新案件編號: {new_case_id}")
            return new_case_id

        except Exception as e:
            print(f"❌ 產生案件編號失敗: {e}")
            # 備用方案
            current_year = datetime.now().year
            minguo_year = current_year - 1911
            backup_id = f"{minguo_year:03d}001"
            print(f"⚠️ 使用備用編號: {backup_id}")
            return backup_id

    def validate_case_id_format(self, case_id: str) -> bool:
        """驗證案件編號格式"""
        if not case_id or len(case_id) != 6:
            return False

        try:
            # 檢查前三碼是否為數字（民國年分）
            year_part = int(case_id[:3])
            # 檢查後三碼是否為數字（流水號）
            number_part = int(case_id[3:])

            # 基本範圍檢查
            if year_part < 100 or year_part > 200:  # 民國100-200年合理範圍
                return False
            if number_part < 1 or number_part > 999:
                return False

            return True
        except ValueError:
            return False

    def check_case_id_duplicate(self, case_id: str, exclude_case_id: str = None) -> bool:
        """檢查案件編號是否重複"""
        for case in self.cases:
            if case.case_id == case_id and case.case_id != exclude_case_id:
                return True
        return False

    # ==================== 查詢與搜尋（向後相容）====================

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據案件ID取得案件"""
        for case in self.cases:
            if case.case_id == case_id:
                return case
        return None

    def get_cases_by_type(self, case_type: str) -> List[CaseData]:
        """根據案件類型取得案件列表"""
        return [case for case in self.cases if case.case_type == case_type]

    def search_cases(self, keyword: str) -> List[CaseData]:
        """搜尋案件"""
        if not keyword:
            return self.cases

        keyword = keyword.lower()
        results = []

        for case in self.cases:
            if (keyword in case.client.lower() or
                keyword in case.case_type.lower() or
                keyword in case.case_id.lower() or
                (case.notes and keyword in case.notes.lower())):
                results.append(case)

        return results

    # ==================== 資料夾管理（向後相容）====================

    def get_case_folder_path(self, case_id: str) -> Optional[str]:
        """取得案件資料夾路徑"""
        try:
            case = self.get_case_by_id(case_id)
            if case:
                return self.services.folder_service.get_case_folder_path(case)
            return None
        except Exception as e:
            print(f"❌ 取得案件資料夾路徑失敗: {e}")
            return None

    def create_case_folder(self, case_id: str) -> bool:
        """建立案件資料夾"""
        try:
            case = self.get_case_by_id(case_id)
            if case:
                result = self.services.folder_service.create_case_folder_structure(case)
                return result[0]
            return False
        except Exception as e:
            print(f"❌ 建立案件資料夾失敗: {e}")
            return False

    # ==================== 統計與狀態====================

    def get_case_statistics(self) -> Dict[str, Any]:
        """取得案件統計資訊"""
        try:
            total = len(self.cases)
            by_type = {}
            by_status = {}

            for case in self.cases:
                # 依類型統計
                case_type = case.case_type or "未分類"
                by_type[case_type] = by_type.get(case_type, 0) + 1

                # 依狀態統計 - 使用progress作為狀態
                status = getattr(case, 'progress', '待處理')
                by_status[status] = by_status.get(status, 0) + 1

            return {
                'total_cases': total,
                'by_type': by_type,
                'by_status': by_status,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ 取得統計資訊失敗: {e}")
            return {'total_cases': 0, 'by_type': {}, 'by_status': {}}

    # ==================== 向後相容的方法 ====================

    def get_cases(self) -> List[CaseData]:
        """取得所有案件 - 向後相容方法"""
        return self.cases.copy()

    def get_all_cases(self) -> List[CaseData]:
        """取得所有案件 - 別名方法"""
        return self.get_cases()

    def reload_cases(self) -> bool:
        """重新載入案件 - 向後相容方法"""
        return self.load_cases()

    # ==================== Services層方法委託====================

    def get_controller_status(self) -> Dict[str, Any]:
        """取得控制器狀態"""
        try:
            return {
                'total_cases': len(self.cases),
                'data_folder': self.data_folder,
                'services_available': hasattr(self, 'services'),
                'system_health': {
                    'overall_status': 'healthy',
                    'last_check': datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                'total_cases': 0,
                'data_folder': self.data_folder,
                'services_available': False,
                'system_health': {
                    'overall_status': 'error',
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }
            }

    def get_available_progress_templates(self) -> List[str]:
        """取得可用的進度範本"""
        try:
            return self.services.progress_service.get_available_templates()
        except Exception as e:
            print(f"❌ 取得進度範本失敗: {e}")
            return []

    def apply_progress_template(self, case_id: str, template_name: str) -> bool:
        """套用進度範本"""
        try:
            result = self.services.progress_service.apply_progress_template(case_id, template_name)
            return result[0]
        except Exception as e:
            print(f"❌ 套用進度範本失敗: {e}")
            return False


# ==================== 向後相容的工廠函數 ====================

def create_case_controller(data_folder: str = None) -> CaseController:
    """
    建立案件控制器的工廠函數

    Args:
        data_folder: 資料資料夾路徑

    Returns:
        CaseController 實例
    """
    return CaseController(data_folder)


# ==================== 便利裝飾器 ====================

def handle_controller_errors(func):
    """控制器方法的錯誤處理裝飾器"""
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            print(f"❌ {func.__name__} 執行失敗: {e}")
            # 根據方法返回類型決定預設返回值
            if func.__name__.startswith('get_') and 'List' in str(func.__annotations__.get('return', '')):
                return []
            elif func.__name__.startswith('get_') and 'Dict' in str(func.__annotations__.get('return', '')):
                return {}
            elif func.__name__.startswith('get_'):
                return None
            else:
                return False
    return wrapper


# ==================== 使用範例 ====================

if __name__ == "__main__":
    # 示範如何使用修正後的控制器
    print("🎯 案件控制器測試")

    try:
        # 初始化控制器
        controller = CaseController("./test_data")

        # 測試案件編號生成
        print("\n🔢 測試案件編號生成:")
        for i in range(3):
            case_id = controller.generate_case_id()
            print(f"生成編號 {i+1}: {case_id}")

        # 查看系統狀態
        print("\n📊 系統狀態:")
        status = controller.get_controller_status()
        print(f"總案件數: {status['total_cases']}")
        print(f"系統健康: {status['system_health'].get('overall_status', 'unknown')}")

        # 示範建立案件
        test_case = CaseData(
            case_id=controller.generate_case_id(),
            client="測試當事人",
            case_type="民事",
            status="待處理",
            notes="測試案件",
            creation_date=datetime.now()
        )

        print(f"\n🏗️ 建立測試案件...")
        if controller.add_case(test_case, create_folder=True):
            print("✅ 案件建立成功")

        print(f"\n📋 案件統計:")
        stats = controller.get_case_statistics()
        print(f"總案件: {stats['total_cases']}")
        print(f"類型分佈: {stats['by_type']}")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()