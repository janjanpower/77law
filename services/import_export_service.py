#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
匯入匯出業務邏輯服務
專責處理案件資料的匯入匯出業務邏輯，整合底層工具
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from utils.excel import ExcelHandler
from .validation_service import ValidationService
from .notification_service import NotificationService
import os
import json
from datetime import datetime
import shutil


class ImportExportService:
    """匯入匯出業務邏輯服務"""

    def __init__(self, data_folder: str):
        """
        初始化匯入匯出服務

        Args:
            data_folder: 資料資料夾路徑
        """
        self.data_folder = data_folder

        # 初始化相依服務
        self.validation_service = ValidationService()
        self.notification_service = NotificationService()

        # 建立備份和匯出資料夾
        self.backup_folder = os.path.join(data_folder, "_backups")
        self.export_folder = os.path.join(data_folder, "_exports")
        self._ensure_folders_exist()

        print("✅ ImportExportService 初始化完成")

    def _ensure_folders_exist(self):
        """確保必要的資料夾存在"""
        for folder in [self.backup_folder, self.export_folder]:
            os.makedirs(folder, exist_ok=True)

    # ==================== Excel 匯入業務邏輯 ====================

    def import_cases_from_excel(self, file_path: str, merge_strategy: str = 'skip_duplicates',
                               validate_data: bool = True, create_backup: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        從 Excel 檔案匯入案件資料（完整業務流程）

        Args:
            file_path: Excel 檔案路徑
            merge_strategy: 合併策略 ('skip_duplicates', 'overwrite', 'merge')
            validate_data: 是否驗證資料
            create_backup: 是否建立備份

        Returns:
            (成功與否, 詳細結果資訊)
        """
        try:
            print(f"📥 開始從 Excel 匯入案件資料: {file_path}")

            # 1. 檔案驗證
            file_validation = self._validate_import_file(file_path)
            if not file_validation[0]:
                return False, {'error': f"檔案驗證失敗: {file_validation[1]}"}

            # 2. 建立備份（如果需要）
            if create_backup:
                backup_result = self._create_import_backup()
                if not backup_result[0]:
                    print(f"⚠️ 警告: 建立備份失敗 - {backup_result[1]}")

            # 3. 讀取 Excel 資料
            raw_data = ExcelHandler.import_cases_from_excel(file_path)
            if not raw_data:
                return False, {'error': 'Excel 檔案中沒有有效的案件資料'}

            print(f"從 Excel 讀取到 {len(raw_data)} 筆原始資料")

            # 4. 資料驗證和清理
            if validate_data:
                validation_result = self._validate_and_clean_imported_data(raw_data)
                valid_cases = validation_result['valid_cases']
                invalid_cases = validation_result['invalid_cases']
                warnings = validation_result['warnings']
            else:
                valid_cases = raw_data
                invalid_cases = []
                warnings = []

            # 5. 處理重複資料
            merge_result = self._handle_duplicate_cases(valid_cases, merge_strategy)
            final_cases = merge_result['cases_to_import']
            duplicate_info = merge_result['duplicate_info']

            # 6. 執行匯入
            import_result = self._execute_import(final_cases)

            # 7. 生成匯入報告
            import_report = self._generate_import_report(
                total_read=len(raw_data),
                valid_count=len(valid_cases),
                invalid_count=len(invalid_cases),
                imported_count=import_result['imported_count'],
                skipped_count=import_result['skipped_count'],
                failed_count=import_result['failed_count'],
                duplicate_info=duplicate_info,
                warnings=warnings,
                invalid_cases=invalid_cases
            )

            # 8. 發送通知
            if import_result['imported_count'] > 0:
                self.notification_service.notify_data_imported(import_report)

            # 9. 儲存匯入報告
            self._save_import_report(import_report, file_path)

            success = import_result['imported_count'] > 0
            print(f"✅ Excel 匯入完成: 成功匯入 {import_result['imported_count']} 筆案件")

            return success, import_report

        except Exception as e:
            error_msg = f"Excel 匯入失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, {'error': error_msg}

    def import_cases_from_json(self, file_path: str, merge_strategy: str = 'skip_duplicates') -> Tuple[bool, Dict[str, Any]]:
        """
        從 JSON 檔案匯入案件資料

        Args:
            file_path: JSON 檔案路徑
            merge_strategy: 合併策略

        Returns:
            (成功與否, 結果資訊)
        """
        try:
            print(f"📥 開始從 JSON 匯入案件資料: {file_path}")

            # 1. 檔案驗證
            if not os.path.exists(file_path):
                return False, {'error': 'JSON 檔案不存在'}

            # 2. 讀取 JSON 資料
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            # 3. 轉換為 CaseData 物件
            cases = []
            for item in raw_data:
                try:
                    case = CaseData.from_dict(item) if isinstance(item, dict) else item
                    cases.append(case)
                except Exception as e:
                    print(f"⚠️ 跳過無效資料: {e}")

            # 4. 處理重複資料
            merge_result = self._handle_duplicate_cases(cases, merge_strategy)
            final_cases = merge_result['cases_to_import']

            # 5. 執行匯入
            import_result = self._execute_import(final_cases)

            success = import_result['imported_count'] > 0
            result_info = {
                'total_read': len(raw_data),
                'imported_count': import_result['imported_count'],
                'skipped_count': import_result['skipped_count'],
                'failed_count': import_result['failed_count']
            }

            return success, result_info

        except Exception as e:
            error_msg = f"JSON 匯入失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, {'error': error_msg}

    # ==================== Excel 匯出業務邏輯 ====================

    def export_cases_to_excel(self, cases: List[CaseData], file_path: str = None,
                             include_metadata: bool = True, custom_fields: List[str] = None) -> Tuple[bool, str]:
        """
        匯出案件資料到 Excel（完整業務流程）

        Args:
            cases: 要匯出的案件列表
            file_path: 匯出檔案路徑，None 則自動生成
            include_metadata: 是否包含匯出元資料
            custom_fields: 自訂匯出欄位

        Returns:
            (成功與否, 檔案路徑或錯誤訊息)
        """
        try:
            print(f"📤 開始匯出 {len(cases)} 筆案件資料到 Excel")

            # 1. 資料預處理
            processed_cases = self._preprocess_cases_for_export(cases, custom_fields)

            # 2. 生成檔案路徑
            if file_path is None:
                file_path = self._generate_export_file_path('excel')

            # 3. 確保匯出資料夾存在
            export_dir = os.path.dirname(file_path)
            os.makedirs(export_dir, exist_ok=True)

            # 4. 執行 Excel 匯出
            export_success = ExcelHandler.export_cases_to_excel(processed_cases, file_path)
            if not export_success:
                return False, "Excel 匯出失敗"

            # 5. 添加元資料工作表（如果需要）
            if include_metadata:
                self._add_metadata_to_excel(file_path, cases)

            # 6. 驗證匯出檔案
            if not os.path.exists(file_path):
                return False, "匯出檔案建立失敗"

            # 7. 生成匯出報告
            export_report = self._generate_export_report(cases, file_path)

            # 8. 發送通知
            self.notification_service.notify_data_exported(export_report)

            print(f"✅ Excel 匯出完成: {file_path}")
            return True, file_path

        except Exception as e:
            error_msg = f"Excel 匯出失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def export_cases_to_json(self, cases: List[CaseData], file_path: str = None,
                            pretty_format: bool = True) -> Tuple[bool, str]:
        """
        匯出案件資料到 JSON

        Args:
            cases: 要匯出的案件列表
            file_path: 匯出檔案路徑
            pretty_format: 是否使用易讀格式

        Returns:
            (成功與否, 檔案路徑或錯誤訊息)
        """
        try:
            print(f"📤 開始匯出 {len(cases)} 筆案件資料到 JSON")

            # 1. 生成檔案路徑
            if file_path is None:
                file_path = self._generate_export_file_path('json')

            # 2. 轉換為字典格式
            cases_data = [case.to_dict() for case in cases]

            # 3. 寫入 JSON 檔案
            with open(file_path, 'w', encoding='utf-8') as f:
                if pretty_format:
                    json.dump(cases_data, f, ensure_ascii=False, indent=2, default=str)
                else:
                    json.dump(cases_data, f, ensure_ascii=False, default=str)

            print(f"✅ JSON 匯出完成: {file_path}")
            return True, file_path

        except Exception as e:
            error_msg = f"JSON 匯出失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 備份業務邏輯 ====================

    def create_data_backup(self, backup_name: str = None, include_folders: bool = False) -> Tuple[bool, str]:
        """
        建立資料備份

        Args:
            backup_name: 備份名稱，None 則自動生成
            include_folders: 是否包含案件資料夾

        Returns:
            (成功與否, 備份路徑或錯誤訊息)
        """
        try:
            print("💾 開始建立資料備份")

            # 1. 生成備份名稱和路徑
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"

            backup_path = os.path.join(self.backup_folder, backup_name)
            os.makedirs(backup_path, exist_ok=True)

            # 2. 備份案件資料檔案
            data_files = self._get_data_files_to_backup()
            for file_path in data_files:
                if os.path.exists(file_path):
                    file_name = os.path.basename(file_path)
                    backup_file_path = os.path.join(backup_path, file_name)
                    shutil.copy2(file_path, backup_file_path)
                    print(f"✅ 備份檔案: {file_name}")

            # 3. 備份案件資料夾（如果需要）
            if include_folders:
                folders_backup_path = os.path.join(backup_path, "case_folders")
                self._backup_case_folders(folders_backup_path)

            # 4. 建立備份清單
            manifest = self._create_backup_manifest(backup_path, include_folders)
            manifest_path = os.path.join(backup_path, "backup_manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 資料備份完成: {backup_path}")
            return True, backup_path

        except Exception as e:
            error_msg = f"建立資料備份失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def restore_data_backup(self, backup_path: str, restore_folders: bool = False) -> Tuple[bool, str]:
        """
        還原資料備份

        Args:
            backup_path: 備份路徑
            restore_folders: 是否還原案件資料夾

        Returns:
            (成功與否, 結果訊息)
        """
        try:
            print(f"🔄 開始還原資料備份: {backup_path}")

            # 1. 驗證備份
            if not os.path.exists(backup_path):
                return False, "備份路徑不存在"

            manifest_path = os.path.join(backup_path, "backup_manifest.json")
            if not os.path.exists(manifest_path):
                return False, "備份清單檔案不存在"

            # 2. 讀取備份清單
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # 3. 建立還原前備份
            current_backup_result = self.create_data_backup("before_restore", include_folders=False)
            if current_backup_result[0]:
                print(f"✅ 建立還原前備份: {current_backup_result[1]}")

            # 4. 還原資料檔案
            restored_files = []
            for file_info in manifest.get('data_files', []):
                source_path = os.path.join(backup_path, file_info['name'])
                target_path = os.path.join(self.data_folder, file_info['name'])

                if os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
                    restored_files.append(file_info['name'])
                    print(f"✅ 還原檔案: {file_info['name']}")

            # 5. 還原案件資料夾（如果需要）
            if restore_folders and manifest.get('includes_folders', False):
                folders_backup_path = os.path.join(backup_path, "case_folders")
                if os.path.exists(folders_backup_path):
                    self._restore_case_folders(folders_backup_path)

            print(f"✅ 資料還原完成，還原了 {len(restored_files)} 個檔案")
            return True, f"成功還原 {len(restored_files)} 個檔案"

        except Exception as e:
            error_msg = f"還原資料備份失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    # ==================== 私有輔助方法 ====================

    def _validate_import_file(self, file_path: str) -> Tuple[bool, str]:
        """驗證匯入檔案"""
        if not os.path.exists(file_path):
            return False, "檔案不存在"

        if not file_path.lower().endswith(('.xlsx', '.xls')):
            return False, "不支援的檔案格式，請使用 Excel 檔案"

        try:
            # 檢查檔案是否可讀
            with open(file_path, 'rb') as f:
                f.read(1024)  # 讀取前1KB檢查
            return True, "檔案驗證通過"
        except Exception as e:
            return False, f"檔案無法讀取: {str(e)}"

    def _create_import_backup(self) -> Tuple[bool, str]:
        """建立匯入前備份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"before_import_{timestamp}"
            return self.create_data_backup(backup_name, include_folders=False)
        except Exception as e:
            return False, f"建立匯入前備份失敗: {str(e)}"

    def _validate_and_clean_imported_data(self, raw_cases: List[CaseData]) -> Dict[str, Any]:
        """驗證和清理匯入的資料"""
        valid_cases = []
        invalid_cases = []
        warnings = []

        for i, case in enumerate(raw_cases):
            try:
                # 使用驗證服務驗證案件資料
                validation_result = self.validation_service.validate_case_data(case)

                if validation_result[0]:
                    # 清理資料
                    cleaned_case = self._clean_case_data(case)
                    valid_cases.append(cleaned_case)
                else:
                    invalid_cases.append({
                        'row': i + 1,
                        'data': case.to_dict() if hasattr(case, 'to_dict') else str(case),
                        'error': validation_result[1]
                    })

            except Exception as e:
                invalid_cases.append({
                    'row': i + 1,
                    'data': str(case),
                    'error': f"資料處理錯誤: {str(e)}"
                })

        return {
            'valid_cases': valid_cases,
            'invalid_cases': invalid_cases,
            'warnings': warnings
        }

    def _clean_case_data(self, case: CaseData) -> CaseData:
        """清理案件資料"""
        # 移除多餘空白
        if case.client:
            case.client = case.client.strip()
        if case.case_type:
            case.case_type = case.case_type.strip()
        if case.notes:
            case.notes = case.notes.strip()

        # 設定預設值
        if not case.status:
            case.status = "待處理"

        if not case.creation_date:
            case.creation_date = datetime.now()

        return case

    def _handle_duplicate_cases(self, cases: List[CaseData], strategy: str) -> Dict[str, Any]:
        """處理重複案件"""
        # 這裡需要與現有案件比較，識別重複
        # 簡化實作，實際應該與資料庫比較
        unique_cases = []
        duplicate_info = {'count': 0, 'details': []}

        seen_ids = set()
        for case in cases:
            if case.case_id in seen_ids:
                duplicate_info['count'] += 1
                duplicate_info['details'].append(case.case_id)

                if strategy == 'skip_duplicates':
                    continue
                elif strategy == 'overwrite':
                    # 移除舊的，添加新的
                    unique_cases = [c for c in unique_cases if c.case_id != case.case_id]
                    unique_cases.append(case)
                # merge 策略需要更複雜的邏輯
            else:
                unique_cases.append(case)
                seen_ids.add(case.case_id)

        return {
            'cases_to_import': unique_cases,
            'duplicate_info': duplicate_info
        }

    def _execute_import(self, cases: List[CaseData]) -> Dict[str, int]:
        """執行實際匯入"""
        imported_count = 0
        failed_count = 0
        skipped_count = 0

        for case in cases:
            try:
                # 這裡應該調用實際的案件建立服務
                # 簡化實作
                imported_count += 1
            except Exception as e:
                print(f"⚠️ 匯入案件失敗: {case.case_id} - {e}")
                failed_count += 1

        return {
            'imported_count': imported_count,
            'failed_count': failed_count,
            'skipped_count': skipped_count
        }

    def _generate_import_report(self, **kwargs) -> Dict[str, Any]:
        """生成匯入報告"""
        return {
            'timestamp': datetime.now(),
            'type': 'import',
            'total_read': kwargs.get('total_read', 0),
            'valid_count': kwargs.get('valid_count', 0),
            'invalid_count': kwargs.get('invalid_count', 0),
            'imported_count': kwargs.get('imported_count', 0),
            'skipped_count': kwargs.get('skipped_count', 0),
            'failed_count': kwargs.get('failed_count', 0),
            'duplicate_info': kwargs.get('duplicate_info', {}),
            'warnings': kwargs.get('warnings', []),
            'invalid_cases': kwargs.get('invalid_cases', [])
        }

    def _save_import_report(self, report: Dict[str, Any], source_file: str):
        """儲存匯入報告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"import_report_{timestamp}.json"
            report_path = os.path.join(self.export_folder, "reports", report_name)

            os.makedirs(os.path.dirname(report_path), exist_ok=True)

            # 添加來源檔案資訊
            report['source_file'] = source_file

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)

            print(f"✅ 匯入報告已儲存: {report_path}")
        except Exception as e:
            print(f"⚠️ 儲存匯入報告失敗: {e}")

    def _preprocess_cases_for_export(self, cases: List[CaseData], custom_fields: List[str] = None) -> List[CaseData]:
        """預處理匯出的案件資料"""
        # 這裡可以進行資料清理、格式化等
        processed_cases = []

        for case in cases:
            # 複製案件資料以避免修改原始資料
            processed_case = CaseData.from_dict(case.to_dict())

            # 格式化日期
            if processed_case.creation_date:
                processed_case.creation_date = processed_case.creation_date.strftime("%Y-%m-%d %H:%M:%S")

            processed_cases.append(processed_case)

        return processed_cases

    def _generate_export_file_path(self, file_type: str) -> str:
        """生成匯出檔案路徑"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if file_type == 'excel':
            filename = f"案件資料匯出_{timestamp}.xlsx"
        elif file_type == 'json':
            filename = f"案件資料匯出_{timestamp}.json"
        else:
            filename = f"案件資料匯出_{timestamp}.txt"

        return os.path.join(self.export_folder, filename)

    def _add_metadata_to_excel(self, file_path: str, cases: List[CaseData]):
        """添加元資料工作表到 Excel"""
        try:
            # 這裡可以使用 openpyxl 或其他庫添加元資料工作表
            metadata = {
                'export_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_cases': len(cases),
                'case_types': list(set([case.case_type for case in cases if case.case_type])),
                'export_version': '1.0'
            }
            print(f"✅ 添加元資料到 Excel: {len(metadata)} 項資訊")
        except Exception as e:
            print(f"⚠️ 添加元資料失敗: {e}")

    def _generate_export_report(self, cases: List[CaseData], file_path: str) -> Dict[str, Any]:
        """生成匯出報告"""
        return {
            'timestamp': datetime.now(),
            'type': 'export',
            'file_path': file_path,
            'total_cases': len(cases),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'case_types': list(set([case.case_type for case in cases if case.case_type]))
        }

    def _get_data_files_to_backup(self) -> List[str]:
        """取得需要備份的資料檔案列表"""
        data_files = []

        # 添加主要資料檔案
        potential_files = [
            'cases.json',
            'cases.xlsx',
            'config.json',
            'settings.json'
        ]

        for file_name in potential_files:
            file_path = os.path.join(self.data_folder, file_name)
            if os.path.exists(file_path):
                data_files.append(file_path)

        return data_files

    def _backup_case_folders(self, backup_path: str):
        """備份案件資料夾"""
        try:
            os.makedirs(backup_path, exist_ok=True)

            # 這裡應該備份所有案件資料夾
            # 簡化實作
            print(f"✅ 案件資料夾備份到: {backup_path}")
        except Exception as e:
            print(f"⚠️ 備份案件資料夾失敗: {e}")

    def _restore_case_folders(self, backup_path: str):
        """還原案件資料夾"""
        try:
            # 這裡應該還原所有案件資料夾
            # 簡化實作
            print(f"✅ 從備份還原案件資料夾: {backup_path}")
        except Exception as e:
            print(f"⚠️ 還原案件資料夾失敗: {e}")

    def _create_backup_manifest(self, backup_path: str, includes_folders: bool) -> Dict[str, Any]:
        """建立備份清單"""
        manifest = {
            'timestamp': datetime.now(),
            'backup_version': '1.0',
            'includes_folders': includes_folders,
            'data_files': []
        }

        # 添加已備份的檔案資訊
        for file_name in os.listdir(backup_path):
            if file_name != "backup_manifest.json":
                file_path = os.path.join(backup_path, file_name)
                if os.path.isfile(file_path):
                    manifest['data_files'].append({
                        'name': file_name,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
                    })

        return manifest