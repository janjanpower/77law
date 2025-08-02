#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
驗證業務邏輯服務
專責處理各種資料驗證的業務邏輯
"""

from typing import List, Optional, Dict, Any, Tuple
from models.case_model import CaseData
from config.settings import AppConfig
import re
from datetime import datetime
import os


class ValidationService:
    """驗證業務邏輯服務"""

    def __init__(self):
        """初始化驗證服務"""
        # 驗證規則配置
        self.validation_rules = {
            'client_name': {
                'max_length': 50,
                'min_length': 1,
                'forbidden_chars': ['<', '>', ':', '"', '/', '\\', '|', '?', '*'],
                'required': True
            },
            'case_id': {
                'max_length': 20,
                'pattern': r'^[A-Z0-9_-]+$',
                'required': False  # 可以自動生成
            },
            'case_type': {
                'allowed_values': list(AppConfig.CASE_TYPE_FOLDERS.keys()) if hasattr(AppConfig, 'CASE_TYPE_FOLDERS') else [],
                'required': True
            },
            'status': {
                'allowed_values': ['待處理', '進行中', '已完成', '已結案', '暫停'],
                'required': False  # 有預設值
            }
        }

        print("✅ ValidationService 初始化完成")

    # ==================== 案件資料驗證 ====================

    def validate_case_data(self, case_data: CaseData, strict_mode: bool = False) -> Tuple[bool, str]:
        """
        驗證案件資料的完整性和正確性

        Args:
            case_data: 要驗證的案件資料
            strict_mode: 嚴格模式（更嚴格的驗證規則）

        Returns:
            (驗證是否通過, 錯誤訊息或成功訊息)
        """
        try:
            validation_errors = []

            # 1. 基本必填欄位驗證
            basic_validation = self._validate_basic_fields(case_data)
            if basic_validation:
                validation_errors.extend(basic_validation)

            # 2. 當事人姓名驗證
            client_validation = self._validate_client_name(case_data.client)
            if client_validation:
                validation_errors.extend(client_validation)

            # 3. 案件ID驗證（如果有提供）
            if case_data.case_id:
                case_id_validation = self._validate_case_id(case_data.case_id)
                if case_id_validation:
                    validation_errors.extend(case_id_validation)

            # 4. 案件類型驗證
            case_type_validation = self._validate_case_type(case_data.case_type)
            if not case_type_validation[0]:
                validation_errors.append(case_type_validation[1])

            # 5. 狀態驗證
            status_validation = self._validate_status(case_data.status)
            if not status_validation[0]:
                validation_errors.append(status_validation[1])

            # 6. 日期驗證
            if case_data.creation_date:
                date_validation = self._validate_date(case_data.creation_date, "建立日期")
                if date_validation:
                    validation_errors.extend(date_validation)

            # 7. 重要日期驗證
            if case_data.important_dates:
                important_dates_validation = self._validate_important_dates(case_data.important_dates)
                if important_dates_validation:
                    validation_errors.extend(important_dates_validation)

            # 8. 嚴格模式額外驗證
            if strict_mode:
                strict_validation = self._strict_mode_validation(case_data)
                if strict_validation:
                    validation_errors.extend(strict_validation)

            # 9. 業務邏輯驗證
            business_validation = self._validate_business_logic(case_data)
            if business_validation:
                validation_errors.extend(business_validation)

            if validation_errors:
                error_message = "; ".join(validation_errors)
                return False, f"資料驗證失敗: {error_message}"
            else:
                return True, "資料驗證通過"

        except Exception as e:
            return False, f"驗證過程發生錯誤: {str(e)}"

    def validate_case_type(self, case_type: str) -> Tuple[bool, str]:
        """
        驗證案件類型

        Args:
            case_type: 案件類型

        Returns:
            (是否有效, 訊息)
        """
        return self._validate_case_type(case_type)

    def validate_client_name_for_folder(self, client_name: str) -> Tuple[bool, str]:
        """
        驗證當事人姓名是否適合作為資料夾名稱

        Args:
            client_name: 當事人姓名

        Returns:
            (是否有效, 訊息)
        """
        if not client_name or client_name.strip() == "":
            return False, "當事人姓名不能為空"

        # 檢查長度
        if len(client_name) > 50:
            return False, "當事人姓名過長（最多50字元）"

        # 檢查禁用字元
        forbidden_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in forbidden_chars:
            if char in client_name:
                return False, f"當事人姓名不能包含字元: {char}"

        # 檢查是否為保留名稱
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']

        if client_name.upper() in reserved_names:
            return False, f"當事人姓名不能使用系統保留名稱: {client_name}"

        return True, "當事人姓名驗證通過"

    # ==================== 檔案和路徑驗證 ====================

    def validate_file_path(self, file_path: str, check_exists: bool = False) -> Tuple[bool, str]:
        """
        驗證檔案路徑

        Args:
            file_path: 檔案路徑
            check_exists: 是否檢查檔案是否存在

        Returns:
            (是否有效, 訊息)
        """
        if not file_path or file_path.strip() == "":
            return False, "檔案路徑不能為空"

        # 檢查路徑長度（Windows限制）
        if len(file_path) > 260:
            return False, "檔案路徑過長（最多260字元）"

        # 檢查非法字元
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in illegal_chars:
            if char in file_path:
                return False, f"檔案路徑包含非法字元: {char}"

        # 檢查是否存在（如果需要）
        if check_exists and not os.path.exists(file_path):
            return False, f"檔案或路徑不存在: {file_path}"

        return True, "檔案路徑驗證通過"

    def validate_folder_name(self, folder_name: str) -> Tuple[bool, str]:
        """
        驗證資料夾名稱

        Args:
            folder_name: 資料夾名稱

        Returns:
            (是否有效, 訊息)
        """
        if not folder_name or folder_name.strip() == "":
            return False, "資料夾名稱不能為空"

        # 檢查長度
        if len(folder_name) > 100:
            return False, "資料夾名稱過長（最多100字元）"

        # 檢查禁用字元
        forbidden_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in forbidden_chars:
            if char in folder_name:
                return False, f"資料夾名稱不能包含字元: {char}"

        # 檢查開頭和結尾
        if folder_name.startswith('.') or folder_name.endswith('.'):
            return False, "資料夾名稱不能以點號開頭或結尾"

        if folder_name.startswith(' ') or folder_name.endswith(' '):
            return False, "資料夾名稱不能以空格開頭或結尾"

        return True, "資料夾名稱驗證通過"

    # ==================== 匯入匯出驗證 ====================

    def validate_excel_file(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證Excel檔案

        Args:
            file_path: Excel檔案路徑

        Returns:
            (是否有效, 訊息)
        """
        # 基本路徑驗證
        path_validation = self.validate_file_path(file_path, check_exists=True)
        if not path_validation[0]:
            return path_validation

        # 檢查副檔名
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            return False, "檔案必須是Excel格式（.xlsx或.xls）"

        # 檢查檔案大小
        try:
            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                return False, f"檔案過大（{file_size/1024/1024:.1f}MB），最大限制50MB"
        except Exception as e:
            return False, f"無法檢查檔案大小: {str(e)}"

        return True, "Excel檔案驗證通過"

    def validate_import_data_structure(self, data: List[Dict]) -> Tuple[bool, str, List[Dict]]:
        """
        驗證匯入資料的結構

        Args:
            data: 匯入的資料列表

        Returns:
            (是否有效, 訊息, 驗證結果詳情)
        """
        if not data:
            return False, "匯入資料為空", []

        # 必要欄位
        required_fields = ['client', 'case_type']
        optional_fields = ['case_id', 'status', 'notes', 'creation_date']

        validation_results = []
        valid_count = 0

        for i, row in enumerate(data):
            row_result = {
                'row_index': i + 1,
                'valid': True,
                'errors': [],
                'warnings': []
            }

            # 檢查必要欄位
            for field in required_fields:
                if field not in row or not row[field] or str(row[field]).strip() == "":
                    row_result['valid'] = False
                    row_result['errors'].append(f"缺少必要欄位: {field}")

            # 檢查資料格式
            if 'client' in row and row['client']:
                client_validation = self.validate_client_name_for_folder(str(row['client']))
                if not client_validation[0]:
                    row_result['valid'] = False
                    row_result['errors'].append(f"當事人姓名格式錯誤: {client_validation[1]}")

            if 'case_type' in row and row['case_type']:
                case_type_validation = self.validate_case_type(str(row['case_type']))
                if not case_type_validation[0]:
                    row_result['valid'] = False
                    row_result['errors'].append(f"案件類型無效: {case_type_validation[1]}")

            # 檢查日期格式
            if 'creation_date' in row and row['creation_date']:
                try:
                    if isinstance(row['creation_date'], str):
                        datetime.strptime(row['creation_date'], '%Y-%m-%d')
                except ValueError:
                    row_result['warnings'].append("日期格式可能不正確，建議使用 YYYY-MM-DD 格式")

            if row_result['valid']:
                valid_count += 1

            validation_results.append(row_result)

        success_rate = valid_count / len(data) * 100

        if valid_count == 0:
            return False, "所有資料都無效", validation_results
        elif success_rate < 50:
            return False, f"有效資料比例過低 ({success_rate:.1f}%)", validation_results
        else:
            message = f"資料結構驗證通過，有效資料: {valid_count}/{len(data)} ({success_rate:.1f}%)"
            return True, message, validation_results

    # ==================== 業務規則驗證 ====================

    def validate_business_rules(self, case_data: CaseData, existing_cases: List[CaseData] = None) -> Tuple[bool, str]:
        """
        驗證業務規則

        Args:
            case_data: 要驗證的案件資料
            existing_cases: 現有案件列表（用於檢查重複等）

        Returns:
            (是否符合業務規則, 訊息)
        """
        business_errors = []

        # 1. 檢查案件ID重複（如果提供了現有案件列表）
        if existing_cases and case_data.case_id:
            duplicate_case = next((c for c in existing_cases if c.case_id == case_data.case_id), None)
            if duplicate_case:
                business_errors.append(f"案件ID已存在: {case_data.case_id}")

        # 2. 檢查同一當事人的重複案件類型
        if existing_cases:
            similar_cases = [c for c in existing_cases
                           if c.client == case_data.client and c.case_type == case_data.case_type]
            active_similar = [c for c in similar_cases if c.status in ['待處理', '進行中']]

            if active_similar:
                business_errors.append(f"當事人 {case_data.client} 已有進行中的 {case_data.case_type} 案件")

        # 3. 檢查日期邏輯
        if case_data.creation_date and case_data.creation_date > datetime.now():
            business_errors.append("建立日期不能是未來時間")

        # 4. 檢查重要日期的合理性
        if case_data.important_dates:
            for date_info in case_data.important_dates:
                if hasattr(date_info, 'date') and date_info.date:
                    # 檢查重要日期是否過於久遠
                    if date_info.date < datetime(2000, 1, 1):
                        business_errors.append(f"重要日期過於久遠: {date_info.date}")

        if business_errors:
            return False, "; ".join(business_errors)
        else:
            return True, "業務規則驗證通過"

    def validate_case_status_transition(self, old_status: str, new_status: str) -> Tuple[bool, str]:
        """
        驗證案件狀態轉換是否合理

        Args:
            old_status: 舊狀態
            new_status: 新狀態

        Returns:
            (是否允許轉換, 訊息)
        """
        # 定義允許的狀態轉換
        allowed_transitions = {
            '待處理': ['進行中', '暫停'],
            '進行中': ['已完成', '暫停', '待處理'],
            '暫停': ['進行中', '待處理'],
            '已完成': ['已結案'],
            '已結案': []  # 已結案不能再轉換
        }

        if old_status not in allowed_transitions:
            return False, f"未知的舊狀態: {old_status}"

        if new_status not in allowed_transitions.get(old_status, []):
            if old_status == new_status:
                return True, "狀態未變更"
            else:
                return False, f"不允許從 '{old_status}' 轉換到 '{new_status}'"

        return True, f"允許狀態轉換: {old_status} → {new_status}"

    # ==================== 私有驗證方法 ====================

    def _validate_basic_fields(self, case_data: CaseData) -> List[str]:
        """驗證基本必填欄位"""
        errors = []

        # 檢查必填欄位
        if not case_data.client or case_data.client.strip() == "":
            errors.append("當事人姓名為必填欄位")

        if not case_data.case_type or case_data.case_type.strip() == "":
            errors.append("案件類型為必填欄位")

        return errors

    def _validate_client_name(self, client_name: str) -> List[str]:
        """驗證當事人姓名"""
        errors = []

        if not client_name:
            return errors  # 基本驗證已處理

        rule = self.validation_rules['client_name']

        # 長度檢查
        if len(client_name) > rule['max_length']:
            errors.append(f"當事人姓名過長，最多{rule['max_length']}字元")

        if len(client_name) < rule['min_length']:
            errors.append(f"當事人姓名過短，至少{rule['min_length']}字元")

        # 禁用字元檢查
        for char in rule['forbidden_chars']:
            if char in client_name:
                errors.append(f"當事人姓名不能包含字元: {char}")

        return errors

    def _validate_case_id(self, case_id: str) -> List[str]:
        """驗證案件ID"""
        errors = []

        if not case_id:
            return errors

        rule = self.validation_rules['case_id']

        # 長度檢查
        if len(case_id) > rule['max_length']:
            errors.append(f"案件ID過長，最多{rule['max_length']}字元")

        # 格式檢查
        if 'pattern' in rule and not re.match(rule['pattern'], case_id):
            errors.append("案件ID格式不正確，只能包含大寫字母、數字、底線和連字號")

        return errors

    def _validate_case_type(self, case_type: str) -> Tuple[bool, str]:
        """驗證案件類型"""
        if not case_type or case_type.strip() == "":
            return False, "案件類型不能為空"

        rule = self.validation_rules['case_type']

        # 如果有定義允許的值，檢查是否在列表中
        if rule['allowed_values'] and case_type not in rule['allowed_values']:
            return False, f"無效的案件類型: {case_type}，允許的類型: {', '.join(rule['allowed_values'])}"

        return True, "案件類型有效"

    def _validate_status(self, status: str) -> Tuple[bool, str]:
        """驗證案件狀態"""
        if not status:
            return True, "狀態為空，將使用預設值"  # 允許空值，會設定預設值

        rule = self.validation_rules['status']

        if status not in rule['allowed_values']:
            return False, f"無效的案件狀態: {status}，允許的狀態: {', '.join(rule['allowed_values'])}"

        return True, "案件狀態有效"

    def _validate_date(self, date_value, field_name: str) -> List[str]:
        """驗證日期"""
        errors = []

        if not date_value:
            return errors

        try:
            if isinstance(date_value, str):
                # 嘗試解析字串日期
                datetime.strptime(date_value, '%Y-%m-%d')
            elif not isinstance(date_value, datetime):
                errors.append(f"{field_name}格式不正確")
        except ValueError:
            errors.append(f"{field_name}格式不正確，請使用 YYYY-MM-DD 格式")

        return errors

    def _validate_important_dates(self, important_dates) -> List[str]:
        """驗證重要日期列表"""
        errors = []

        if not important_dates:
            return errors

        try:
            for i, date_info in enumerate(important_dates):
                if hasattr(date_info, 'date') and date_info.date:
                    date_errors = self._validate_date(date_info.date, f"重要日期{i+1}")
                    errors.extend(date_errors)

                if hasattr(date_info, 'description'):
                    if not date_info.description or date_info.description.strip() == "":
                        errors.append(f"重要日期{i+1}缺少描述")
        except Exception as e:
            errors.append(f"重要日期格式錯誤: {str(e)}")

        return errors

    def _strict_mode_validation(self, case_data: CaseData) -> List[str]:
        """嚴格模式驗證"""
        errors = []

        # 嚴格模式要求更多欄位
        if not case_data.case_id or case_data.case_id.strip() == "":
            errors.append("嚴格模式要求提供案件ID")

        if not case_data.status or case_data.status.strip() == "":
            errors.append("嚴格模式要求提供案件狀態")

        if not case_data.creation_date:
            errors.append("嚴格模式要求提供建立日期")

        # 檢查備註長度
        if case_data.notes and len(case_data.notes) > 1000:
            errors.append("備註內容過長（嚴格模式限制1000字元）")

        return errors

    def _validate_business_logic(self, case_data: CaseData) -> List[str]:
        """業務邏輯驗證"""
        errors = []

        # 檢查特殊業務規則
        if case_data.case_type == "刑事" and case_data.status == "已完成":
            # 刑事案件完成時可能需要特殊檢查
            if not case_data.notes or "判決" not in case_data.notes:
                errors.append("刑事案件完成時建議在備註中記錄判決結果")

        # 檢查案件類型與狀態的合理性
        if case_data.case_type == "諮詢" and case_data.status not in ["待處理", "已完成"]:
            errors.append("諮詢案件通常只有'待處理'或'已完成'狀態")

        return errors

    # ==================== 批量驗證功能 ====================

    def validate_multiple_cases(self, cases: List[CaseData],
                               cross_validation: bool = True) -> Dict[str, Any]:
        """
        批量驗證多個案件

        Args:
            cases: 案件列表
            cross_validation: 是否進行交叉驗證（檢查重複等）

        Returns:
            驗證結果統計
        """
        results = {
            'total_cases': len(cases),
            'valid_cases': 0,
            'invalid_cases': 0,
            'validation_details': [],
            'cross_validation_errors': []
        }

        # 逐一驗證每個案件
        for i, case in enumerate(cases):
            validation_result = self.validate_case_data(case)

            detail = {
                'case_index': i,
                'case_id': case.case_id,
                'client': case.client,
                'valid': validation_result[0],
                'message': validation_result[1]
            }

            results['validation_details'].append(detail)

            if validation_result[0]:
                results['valid_cases'] += 1
            else:
                results['invalid_cases'] += 1

        # 交叉驗證
        if cross_validation:
            cross_errors = self._cross_validate_cases(cases)
            results['cross_validation_errors'] = cross_errors

        return results

    def _cross_validate_cases(self, cases: List[CaseData]) -> List[str]:
        """交叉驗證案件列表"""
        errors = []

        # 檢查案件ID重複
        case_ids = [case.case_id for case in cases if case.case_id]
        duplicate_ids = [case_id for case_id in set(case_ids) if case_ids.count(case_id) > 1]

        for dup_id in duplicate_ids:
            errors.append(f"重複的案件ID: {dup_id}")

        # 檢查同一當事人的多個相同類型案件
        client_type_combinations = {}
        for case in cases:
            key = (case.client, case.case_type)
            if key not in client_type_combinations:
                client_type_combinations[key] = []
            client_type_combinations[key].append(case)

        for (client, case_type), case_list in client_type_combinations.items():
            if len(case_list) > 1:
                active_cases = [c for c in case_list if c.status in ['待處理', '進行中']]
                if len(active_cases) > 1:
                    errors.append(f"當事人 {client} 有多個進行中的 {case_type} 案件")

        return errors

    # ==================== 驗證報告生成 ====================

    def generate_validation_report(self, validation_results: Dict[str, Any]) -> str:
        """生成驗證報告"""
        report_lines = []

        # 總覽
        total = validation_results['total_cases']
        valid = validation_results['valid_cases']
        invalid = validation_results['invalid_cases']

        report_lines.append("=== 案件資料驗證報告 ===")
        report_lines.append(f"總案件數: {total}")
        report_lines.append(f"有效案件: {valid} ({valid/total*100:.1f}%)")
        report_lines.append(f"無效案件: {invalid} ({invalid/total*100:.1f}%)")
        report_lines.append("")

        # 詳細錯誤
        if invalid > 0:
            report_lines.append("=== 驗證錯誤詳情 ===")
            for detail in validation_results['validation_details']:
                if not detail['valid']:
                    report_lines.append(f"案件 {detail['case_index']+1} ({detail['client']}): {detail['message']}")
            report_lines.append("")

        # 交叉驗證錯誤
        if validation_results.get('cross_validation_errors'):
            report_lines.append("=== 交叉驗證錯誤 ===")
            for error in validation_results['cross_validation_errors']:
                report_lines.append(f"- {error}")
            report_lines.append("")

        report_lines.append(f"報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(report_lines)