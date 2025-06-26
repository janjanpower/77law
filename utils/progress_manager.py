"""
進度管理工具類
統一處理案件進度相關的邏輯，支援真正的漸進式進度管理
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from config.settings import AppConfig

class ProgressManager:
    """進度管理工具類"""

    @staticmethod
    def get_experienced_stages(case_data) -> List[str]:
        """
        🔥 修正：取得實際經歷過的階段列表

        Args:
            case_data: 案件資料

        Returns:
            List[str]: 實際經歷過的階段列表
        """
        if hasattr(case_data, 'experienced_stages'):
            return case_data.experienced_stages.copy()
        elif hasattr(case_data, 'get_display_stages'):
            return case_data.get_display_stages()
        else:
            # 向後相容性
            return [case_data.progress] if hasattr(case_data, 'progress') else []

    @staticmethod
    def get_next_available_stages(case_type: str, current_stage: str) -> List[str]:
        """
        取得可以前進的下一個階段列表（基於標準流程）

        Args:
            case_type: 案件類型
            current_stage: 當前進度階段

        Returns:
            List[str]: 可以前進的階段列表
        """
        all_stages = AppConfig.get_progress_options(case_type)

        try:
            current_index = all_stages.index(current_stage)
            if current_index < len(all_stages) - 1:
                return all_stages[current_index + 1:]
            return []
        except ValueError:
            # 如果當前階段不在標準列表中，返回所有階段
            return all_stages

    @staticmethod
    def validate_stage_progression(case_type: str, experienced_stages: List[str]) -> bool:
        """
        🔥 修正：驗證階段進展是否合理（不強制要求順序，只驗證存在性）

        Args:
            case_type: 案件類型
            experienced_stages: 經歷過的階段列表

        Returns:
            bool: 進展是否合理
        """
        all_stages = AppConfig.get_progress_options(case_type)

        # 檢查所有經歷過的階段是否都在標準列表中（允許自訂階段）
        for stage in experienced_stages:
            if stage not in all_stages:
                # 自訂階段也是允許的，所以只是記錄但不返回False
                print(f"發現自訂階段: {stage}")

        return True

    @staticmethod
    def add_new_stage(case_data, new_stage: str, stage_date: str = None) -> bool:
        """
        🔥 新增：添加新的進度階段

        Args:
            case_data: 案件資料
            new_stage: 新的階段名稱
            stage_date: 階段日期

        Returns:
            bool: 是否成功添加
        """
        if stage_date is None:
            stage_date = datetime.now().strftime('%Y-%m-%d')

        try:
            # 更新案件進度
            case_data.update_progress(new_stage, stage_date)
            return True
        except Exception as e:
            print(f"添加新階段失敗: {e}")
            return False

    @staticmethod
    def get_stage_status(case_data, stage: str) -> str:
        """
        🔥 修正：取得階段狀態（基於實際經歷過的階段）

        Args:
            case_data: 案件資料
            stage: 要檢查的階段

        Returns:
            str: 階段狀態 ('completed', 'current', 'pending')
        """
        current_stage = getattr(case_data, 'progress', '')
        experienced_stages = ProgressManager.get_experienced_stages(case_data)

        if stage == current_stage:
            return 'current'
        elif stage in experienced_stages:
            # 如果在經歷過的階段中但不是當前階段，則為已完成
            return 'completed'
        else:
            return 'pending'

    @staticmethod
    def get_progress_statistics(cases_data) -> Dict[str, any]:
        """
        取得進度統計資訊

        Args:
            cases_data: 案件資料列表

        Returns:
            Dict: 統計資訊
        """
        stats = {
            'total_cases': len(cases_data),
            'progress_distribution': {},
            'case_type_progress': {},
            'monthly_progress': {},
            'stage_frequency': {}  # 🔥 新增：各階段經歷頻率
        }

        for case in cases_data:
            # 進度分布統計
            progress = getattr(case, 'progress', '未知')
            stats['progress_distribution'][progress] = stats['progress_distribution'].get(progress, 0) + 1

            # 案件類型進度統計
            case_type = getattr(case, 'case_type', '未知')
            if case_type not in stats['case_type_progress']:
                stats['case_type_progress'][case_type] = {}
            stats['case_type_progress'][case_type][progress] = stats['case_type_progress'][case_type].get(progress, 0) + 1

            # 月度進度統計
            progress_date = getattr(case, 'progress_date', None)
            if progress_date:
                try:
                    year_month = progress_date[:7]  # YYYY-MM
                    stats['monthly_progress'][year_month] = stats['monthly_progress'].get(year_month, 0) + 1
                except:
                    pass

            # 🔥 新增：各階段經歷頻率統計
            experienced_stages = ProgressManager.get_experienced_stages(case)
            for stage in experienced_stages:
                stats['stage_frequency'][stage] = stats['stage_frequency'].get(stage, 0) + 1

        return stats

    @staticmethod
    def calculate_progress_percentage(case_type: str, current_stage: str, experienced_stages: List[str] = None) -> float:
        """
        🔥 修正：計算進度百分比（基於實際經歷的階段數）

        Args:
            case_type: 案件類型
            current_stage: 當前階段
            experienced_stages: 經歷過的階段列表

        Returns:
            float: 進度百分比 (0.0 - 1.0)
        """
        all_stages = AppConfig.get_progress_options(case_type)

        if experienced_stages:
            # 基於實際經歷的階段數計算
            max_index = -1
            for stage in experienced_stages:
                try:
                    index = all_stages.index(stage)
                    max_index = max(max_index, index)
                except ValueError:
                    # 自訂階段，使用當前位置
                    continue

            if max_index >= 0:
                return (max_index + 1) / len(all_stages)

        # 回退到基於當前階段計算
        try:
            current_index = all_stages.index(current_stage)
            return (current_index + 1) / len(all_stages)
        except ValueError:
            return 0.0

    @staticmethod
    def get_stage_color(stage_status: str) -> str:
        """
        取得階段狀態對應的顏色

        Args:
            stage_status: 階段狀態 ('completed', 'current', 'pending')

        Returns:
            str: 顏色代碼
        """
        color_map = {
            'completed': '#2196F3',  # 藍色 - 已完成
            'current': '#4CAF50',    # 綠色 - 當前階段
            'pending': '#E0E0E0'     # 灰色 - 待處理
        }
        return color_map.get(stage_status, '#E0E0E0')

    @staticmethod
    def format_progress_display(case_data, include_dates: bool = True, include_percentage: bool = False) -> str:
        """
        🔥 修正：格式化進度顯示文字（預設不顯示百分比）

        Args:
            case_data: 案件資料
            include_dates: 是否包含日期
            include_percentage: 是否包含進度百分比（預設為False）

        Returns:
            str: 格式化的進度文字
        """
        current_stage = getattr(case_data, 'progress', '未知')
        progress_text = f"目前狀態: {current_stage}"

        if include_dates:
            progress_date = getattr(case_data, 'progress_date', None)
            if progress_date:
                progress_text += f" ({progress_date})"

        if include_percentage:
            case_type = getattr(case_data, 'case_type', '')
            experienced_stages = ProgressManager.get_experienced_stages(case_data)
            percentage = ProgressManager.calculate_progress_percentage(
                case_type, current_stage, experienced_stages
            )
            progress_text += f" [{percentage:.0%}]"

        return progress_text

    @staticmethod
    def get_overdue_cases(cases_data, days_threshold: int = 30) -> List:
        """
        取得逾期案件列表

        Args:
            cases_data: 案件資料列表
            days_threshold: 逾期天數閾值

        Returns:
            List: 逾期案件列表
        """
        from datetime import datetime, timedelta

        overdue_cases = []
        threshold_date = (datetime.now() - timedelta(days=days_threshold)).strftime('%Y-%m-%d')

        for case in cases_data:
            progress_date = getattr(case, 'progress_date', None)
            current_progress = getattr(case, 'progress', '')

            if (progress_date and progress_date < threshold_date and
                current_progress != '已結案'):
                overdue_cases.append(case)

        return overdue_cases

    @staticmethod
    def suggest_next_stages(case_data) -> List[str]:
        """
        🔥 新增：建議下一個可能的階段

        Args:
            case_data: 案件資料

        Returns:
            List[str]: 建議的下一階段列表
        """
        case_type = getattr(case_data, 'case_type', '')
        current_stage = getattr(case_data, 'progress', '')

        # 取得標準流程中的下一階段
        standard_next = ProgressManager.get_next_available_stages(case_type, current_stage)

        # 也可以包含其他可能的階段（如調解、和解等）
        all_stages = AppConfig.get_progress_options(case_type)
        experienced_stages = ProgressManager.get_experienced_stages(case_data)

        # 移除已經歷過的階段
        suggestions = []
        for stage in standard_next:
            if stage not in experienced_stages:
                suggestions.append(stage)

        return suggestions

    @staticmethod
    def create_progress_timeline(case_data) -> List[Dict]:
        """
        🔥 新增：建立進度時間軸

        Args:
            case_data: 案件資料

        Returns:
            List[Dict]: 時間軸資料
        """
        timeline = []
        experienced_stages = ProgressManager.get_experienced_stages(case_data)
        progress_history = getattr(case_data, 'progress_history', {})
        current_stage = getattr(case_data, 'progress', '')

        for i, stage in enumerate(experienced_stages):
            stage_date = progress_history.get(stage, '未設定日期')
            is_current = (stage == current_stage)

            timeline.append({
                'stage': stage,
                'date': stage_date,
                'is_current': is_current,
                'order': i + 1,
                'status': 'current' if is_current else 'completed'
            })

        return timeline

    @staticmethod
    def export_progress_summary(case_data) -> Dict:
        """
        🔥 新增：匯出進度摘要

        Args:
            case_data: 案件資料

        Returns:
            Dict: 進度摘要資料
        """
        experienced_stages = ProgressManager.get_experienced_stages(case_data)
        progress_history = getattr(case_data, 'progress_history', {})
        case_type = getattr(case_data, 'case_type', '')
        current_stage = getattr(case_data, 'progress', '')

        summary = {
            'case_id': getattr(case_data, 'case_id', ''),
            'client': getattr(case_data, 'client', ''),
            'case_type': case_type,
            'current_stage': current_stage,
            'current_date': getattr(case_data, 'progress_date', ''),
            'experienced_stages': experienced_stages,
            'progress_history': progress_history,
            'total_stages': len(experienced_stages),
            'progress_percentage': ProgressManager.calculate_progress_percentage(
                case_type, current_stage, experienced_stages
            ),
            'timeline': ProgressManager.create_progress_timeline(case_data),
            'suggested_next': ProgressManager.suggest_next_stages(case_data)
        }

        return summary