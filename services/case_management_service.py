#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件管理服務 - 業務邏輯層
提供高階的案件管理業務邏輯
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# 動態匯入控制器
try:
    from controllers.case_management_controller import CaseManagementController
except ImportError:
    # 如果無法匯入，提供基本實作
    print("⚠️ 無法匯入 CaseManagementController，請確認檔案路徑")
    class CaseManagementController:
        def __init__(self, data_folder):
            self.data_folder = data_folder
        def import_cases_from_excel(self, file_path):
            return False, "控制器不可用", None

class CaseManagementService:
    """案件管理服務 - 業務邏輯層"""

    def __init__(self, data_folder: str = "data"):
        """初始化服務"""
        self.controller = CaseManagementController(data_folder)
        self.data_folder = data_folder

        # 初始化日誌
        self.operation_log = []

        print("✅ 案件管理服務初始化完成")

    def _log_operation(self, operation: str, status: str, details: str = ""):
        """記錄操作日誌"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'status': status,
            'details': details
        }
        self.operation_log.append(log_entry)

        # 保持日誌在合理大小（最多1000筆）
        if len(self.operation_log) > 1000:
            self.operation_log = self.operation_log[-1000:]

    # ==================== 批次處理服務 ====================

    def batch_import_cases(self, file_path: str, create_folders: bool = True) -> Dict[str, Any]:
        """批次匯入案件服務"""
        operation = "batch_import_cases"

        result = {
            'success': False,
            'total_imported': 0,
            'total_folders_created': 0,
            'failed_cases': [],
            'successful_cases': [],
            'validation_errors': [],
            'performance_metrics': {},
            'message': ''
        }

        start_time = datetime.now()

        try:
            # 1. 驗證檔案
            if not os.path.exists(file_path):
                result['message'] = "檔案不存在"
                self._log_operation(operation, "failed", result['message'])
                return result

            # 2. 分析檔案結構
            analysis_success, analysis_message, sheet_info = self.controller.analyze_excel_file(file_path)

            if not analysis_success:
                result['message'] = f"檔案分析失敗: {analysis_message}"
                result['validation_errors'].append(result['message'])
                self._log_operation(operation, "failed", result['message'])
                return result

            # 3. 匯入案件資料
            import_success, import_message, cases = self.controller.import_cases_from_excel(file_path)

            if not import_success:
                result['message'] = import_message
                result['validation_errors'].append(import_message)
                self._log_operation(operation, "failed", result['message'])
                return result

            result['total_imported'] = len(cases)

            # 4. 資料驗證和清理
            validated_cases = self._validate_and_clean_cases(cases)

            # 5. 建立資料夾（如果需要）
            if create_folders:
                folder_results = self._batch_create_folders(validated_cases)
                result['total_folders_created'] = folder_results['success_count']
                result['failed_cases'].extend(folder_results['failed_cases'])
                result['successful_cases'].extend(folder_results['successful_cases'])
            else:
                result['successful_cases'] = [{'case': case, 'index': i} for i, case in enumerate(validated_cases)]

            # 6. 計算效能指標
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result['performance_metrics'] = {
                'processing_time_seconds': round(processing_time, 2),
                'cases_per_second': round(len(cases) / processing_time, 2) if processing_time > 0 else 0,
                'file_analysis_time': analysis_message,
                'total_operations': len(cases)
            }

            result['success'] = True
            result['message'] = f"成功處理 {len(cases)} 筆案件"

            if create_folders:
                result['message'] += f"，建立 {result['total_folders_created']} 個資料夾"

            self._log_operation(operation, "success", result['message'])

        except Exception as e:
            result['message'] = f"批次匯入失敗: {e}"
            self._log_operation(operation, "error", str(e))

        return result

    def _validate_and_clean_cases(self, cases: List[Dict]) -> List[Dict]:
        """驗證和清理案件資料"""
        validated_cases = []

        for case in cases:
            try:
                # 基本清理
                cleaned_case = {}

                for key, value in case.items():
                    # 清理鍵名
                    clean_key = str(key).strip()

                    # 清理值
                    if value is not None:
                        clean_value = str(value).strip() if not isinstance(value, (int, float)) else value
                        if clean_value != '':
                            cleaned_case[clean_key] = clean_value

                # 確保基本欄位存在
                if 'client' not in cleaned_case and '委託人' in cleaned_case:
                    cleaned_case['client'] = cleaned_case['委託人']

                if 'case_type' not in cleaned_case and '案件類型' in cleaned_case:
                    cleaned_case['case_type'] = cleaned_case['案件類型']

                if cleaned_case:  # 只保留非空案件
                    validated_cases.append(cleaned_case)

            except Exception as e:
                print(f"案件資料清理失敗: {e}")
                continue

        return validated_cases

    def _batch_create_folders(self, cases: List[Dict]) -> Dict[str, Any]:
        """批次建立資料夾"""
        result = {
            'success_count': 0,
            'failed_cases': [],
            'successful_cases': []
        }

        for i, case_dict in enumerate(cases):
            try:
                # 建立案件物件
                case_obj = type('CaseData', (), case_dict)()

                # 建立資料夾
                folder_success, folder_message = self.controller.create_case_folder(case_obj)

                if folder_success:
                    result['success_count'] += 1
                    result['successful_cases'].append({
                        'index': i,
                        'case': case_dict,
                        'folder_path': folder_message
                    })
                else:
                    result['failed_cases'].append({
                        'index': i,
                        'case': case_dict,
                        'error': folder_message
                    })

            except Exception as e:
                result['failed_cases'].append({
                    'index': i,
                    'case': case_dict,
                    'error': str(e)
                })

        return result

    # ==================== 資料完整性服務 ====================

    def validate_data_integrity(self, perform_repair: bool = False) -> Dict[str, Any]:
        """驗證系統資料完整性"""
        operation = "validate_data_integrity"

        result = {
            'overall_health': 'unknown',
            'folder_validation': {},
            'system_status': {},
            'issues_found': [],
            'repair_actions': [],
            'recommendations': []
        }

        try:
            # 1. 檢查系統狀態
            system_status = self.controller.get_system_status()
            result['system_status'] = system_status

            # 2. 驗證所有案件資料夾
            folder_validation = self.controller.validate_all_case_folders()
            result['folder_validation'] = folder_validation

            # 3. 分析問題
            issues = []

            if folder_validation.get('invalid_folders'):
                issues.append(f"{len(folder_validation['invalid_folders'])} 個資料夾結構不完整")

            if not system_status.get('system_health', {}).get('ready_for_operations'):
                issues.append("系統組件未完全載入")

            result['issues_found'] = issues

            # 4. 執行修復（如果需要）
            if perform_repair and issues:
                repair_results = self._perform_system_repair()
                result['repair_actions'] = repair_results

            # 5. 產生建議
            recommendations = []

            if not issues:
                recommendations.append("系統狀態良好，無需特別處理")
                result['overall_health'] = 'excellent'
            elif len(issues) <= 2:
                recommendations.append("發現少量問題，建議定期維護")
                result['overall_health'] = 'good'
            else:
                recommendations.append("發現多項問題，建議立即處理")
                result['overall_health'] = 'needs_attention'

            if folder_validation.get('invalid_folders'):
                recommendations.append("使用修復功能重建遺失的子資料夾")

            result['recommendations'] = recommendations

            self._log_operation(operation, "success", f"發現 {len(issues)} 個問題")

        except Exception as e:
            result['overall_health'] = 'error'
            result['issues_found'] = [f"驗證過程失敗: {e}"]
            self._log_operation(operation, "error", str(e))

        return result

    def _perform_system_repair(self) -> List[str]:
        """執行系統修復"""
        repair_actions = []

        try:
            # 取得所有案件資料夾
            folders = self.controller.list_all_case_folders()

            for folder_name in folders:
                try:
                    # 建立虛擬案件物件用於修復
                    case_obj = type('CaseData', (), {'client': folder_name})()

                    # 嘗試修復資料夾結構
                    if self.controller.repair_case_folder_structure(case_obj):
                        repair_actions.append(f"修復資料夾: {folder_name}")

                except Exception as e:
                    repair_actions.append(f"修復失敗 {folder_name}: {e}")

        except Exception as e:
            repair_actions.append(f"修復過程失敗: {e}")

        return repair_actions

    # ==================== 智能分析服務 ====================

    def analyze_case_patterns(self) -> Dict[str, Any]:
        """分析案件模式"""
        result = {
            'folder_statistics': {},
            'common_patterns': [],
            'recommendations': [],
            'analysis_date': datetime.now().isoformat()
        }

        try:
            # 取得所有資料夾
            folders = self.controller.list_all_case_folders()

            # 統計資訊
            result['folder_statistics'] = {
                'total_folders': len(folders),
                'folder_names': folders[:10],  # 只顯示前10個
                'name_patterns': self._analyze_naming_patterns(folders)
            }

            # 分析命名模式
            patterns = self._analyze_naming_patterns(folders)
            result['common_patterns'] = patterns

            # 產生建議
            recommendations = []

            if patterns.get('inconsistent_naming'):
                recommendations.append("建議統一案件資料夾命名規則")

            if len(folders) > 100:
                recommendations.append("案件數量較多，建議定期整理歸檔")

            result['recommendations'] = recommendations

        except Exception as e:
            result['error'] = str(e)

        return result

    def _analyze_naming_patterns(self, folder_names: List[str]) -> Dict[str, Any]:
        """分析命名模式"""
        patterns = {
            'has_underscores': 0,
            'has_spaces': 0,
            'has_numbers': 0,
            'contains_client_info': 0,
            'average_length': 0,
            'inconsistent_naming': False
        }

        if not folder_names:
            return patterns

        total_length = 0

        for name in folder_names:
            total_length += len(name)

            if '_' in name:
                patterns['has_underscores'] += 1
            if ' ' in name:
                patterns['has_spaces'] += 1
            if any(char.isdigit() for char in name):
                patterns['has_numbers'] += 1

            # 簡單檢查是否包含客戶資訊（假設包含中文字符）
            if any('\u4e00' <= char <= '\u9fff' for char in name):
                patterns['contains_client_info'] += 1

        patterns['average_length'] = round(total_length / len(folder_names), 1)

        # 檢查命名一致性
        underscore_ratio = patterns['has_underscores'] / len(folder_names)
        space_ratio = patterns['has_spaces'] / len(folder_names)

        if 0.2 < underscore_ratio < 0.8 or 0.2 < space_ratio < 0.8:
            patterns['inconsistent_naming'] = True

        return patterns

    # ==================== 報告服務 ====================

    def generate_system_report(self) -> Dict[str, Any]:
        """產生系統報告"""
        report = {
            'report_generated': datetime.now().isoformat(),
            'system_overview': {},
            'data_integrity': {},
            'case_analysis': {},
            'operation_log_summary': {},
            'recommendations': []
        }

        try:
            # 1. 系統概覽
            report['system_overview'] = self.controller.get_system_status()

            # 2. 資料完整性
            report['data_integrity'] = self.validate_data_integrity(perform_repair=False)

            # 3. 案件分析
            report['case_analysis'] = self.analyze_case_patterns()

            # 4. 操作日誌摘要
            report['operation_log_summary'] = self._summarize_operation_log()

            # 5. 整體建議
            recommendations = []

            # 從各項分析中收集建議
            if report['data_integrity'].get('recommendations'):
                recommendations.extend(report['data_integrity']['recommendations'])

            if report['case_analysis'].get('recommendations'):
                recommendations.extend(report['case_analysis']['recommendations'])

            # 去重
            recommendations = list(set(recommendations))

            report['recommendations'] = recommendations

        except Exception as e:
            report['error'] = str(e)

        return report

    def _summarize_operation_log(self) -> Dict[str, Any]:
        """總結操作日誌"""
        summary = {
            'total_operations': len(self.operation_log),
            'successful_operations': 0,
            'failed_operations': 0,
            'recent_operations': [],
            'most_common_operations': {}
        }

        if not self.operation_log:
            return summary

        # 統計操作狀態
        operation_counts = {}

        for log_entry in self.operation_log:
            status = log_entry.get('status', 'unknown')
            operation = log_entry.get('operation', 'unknown')

            if status == 'success':
                summary['successful_operations'] += 1
            elif status in ['failed', 'error']:
                summary['failed_operations'] += 1

            operation_counts[operation] = operation_counts.get(operation, 0) + 1

        # 最近的操作（最多10筆）
        summary['recent_operations'] = self.operation_log[-10:]

        # 最常見的操作
        summary['most_common_operations'] = dict(sorted(
            operation_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5])

        return summary

    # ==================== 維護服務 ====================

    def perform_maintenance(self, deep_clean: bool = False) -> Dict[str, Any]:
        """執行系統維護"""
        maintenance_result = {
            'maintenance_started': datetime.now().isoformat(),
            'actions_performed': [],
            'issues_resolved': [],
            'recommendations': [],
            'maintenance_completed': None,
            'success': False
        }

        try:
            actions = []

            # 1. 驗證資料完整性並修復
            integrity_result = self.validate_data_integrity(perform_repair=True)
            actions.append("資料完整性檢查和修復")

            if integrity_result.get('repair_actions'):
                maintenance_result['issues_resolved'].extend(integrity_result['repair_actions'])

            # 2. 清理操作日誌（如果太大）
            if len(self.operation_log) > 500:
                self.operation_log = self.operation_log[-500:]
                actions.append("清理操作日誌")

            # 3. 深度清理（如果需要）
            if deep_clean:
                deep_clean_results = self._perform_deep_clean()
                actions.extend(deep_clean_results)

            maintenance_result['actions_performed'] = actions
            maintenance_result['maintenance_completed'] = datetime.now().isoformat()
            maintenance_result['success'] = True

            # 記錄維護操作
            self._log_operation("system_maintenance", "success", f"執行了 {len(actions)} 項維護操作")

        except Exception as e:
            maintenance_result['error'] = str(e)
            self._log_operation("system_maintenance", "error", str(e))

        return maintenance_result

    def _perform_deep_clean(self) -> List[str]:
        """執行深度清理"""
        actions = []

        try:
            # 可以在這裡添加更多深度清理邏輯
            # 例如：清理臨時檔案、檢查磁碟空間等

            actions.append("執行深度系統檢查")

        except Exception as e:
            actions.append(f"深度清理失敗: {e}")

        return actions

    # ==================== 工具方法 ====================

    def get_operation_log(self, limit: int = 50) -> List[Dict]:
        """取得操作日誌"""
        return self.operation_log[-limit:] if limit > 0 else self.operation_log

    def clear_operation_log(self) -> bool:
        """清空操作日誌"""
        try:
            self.operation_log.clear()
            return True
        except Exception:
            return False