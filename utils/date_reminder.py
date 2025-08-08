#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日期提醒工具類
處理案件階段日期提醒相關功能
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from models.case_model import CaseData


class DateReminderManager:
    """日期提醒管理器"""

    @staticmethod
    def get_upcoming_stages(cases: List[CaseData], days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        取得指定天數內的即將到期階段

        Args:
            cases: 案件列表
            days_ahead: 提前天數

        Returns:
            List[Dict]: 排序後的階段列表
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)

        upcoming_stages = []

        for case in cases:
            if not hasattr(case, 'progress_stages') or not case.progress_stages:
                continue

            for stage_name, stage_date_str in case.progress_stages.items():
                if not stage_date_str:
                    continue

                try:
                    stage_date = datetime.strptime(stage_date_str, '%Y-%m-%d').date()

                    # 檢查是否在指定天數內
                    if today <= stage_date <= end_date:
                        # 取得時間（如果有）
                        stage_time = ""
                        if hasattr(case, 'progress_times') and case.progress_times:
                            stage_time = case.progress_times.get(stage_name, "")

                        # 取得備註（如果有）
                        stage_note = ""
                        if hasattr(case, 'progress_notes') and case.progress_notes:
                            stage_note = case.progress_notes.get(stage_name, "")

                        upcoming_stages.append({
                            'case': case,
                            'stage_name': stage_name,
                            'stage_date': stage_date,
                            'stage_date_str': stage_date_str,
                            'stage_time': stage_time,
                            'stage_note': stage_note,
                            'client': case.client,
                            'case_id': case.case_id,
                            'case_type': case.case_type,
                            'days_until': (stage_date - today).days,
                            'is_today': stage_date == today,
                            'is_overdue': stage_date < today
                        })

                except ValueError:
                    # 日期格式錯誤，跳過
                    continue

        # 按日期和時間排序
        upcoming_stages.sort(key=lambda x: (x['stage_date'], x['stage_time'] or "00:00"))

        return upcoming_stages

    @staticmethod
    def format_stage_display(stage_info: Dict[str, Any]) -> str:
        """
        格式化階段顯示文字

        Args:
            stage_info: 階段資訊

        Returns:
            str: 格式化的顯示文字
        """
        date_str = stage_info['stage_date'].strftime('%m/%d')

        # 組合時間（如果有）
        time_part = ""
        if stage_info['stage_time']:
            time_part = f" {stage_info['stage_time']}"

        # 組合顯示文字：日期 時間 當事人 階段
        display_text = f"{date_str}{time_part} {stage_info['client']} {stage_info['stage_name']}"

        return display_text

    @staticmethod
    def get_stage_color(stage_info: Dict[str, Any]) -> str:
        """
        取得階段顯示顏色

        Args:
            stage_info: 階段資訊

        Returns:
            str: 顏色代碼
        """
        if stage_info['is_overdue']:
            return '#FF6B6B'  # 紅色 - 已過期
        elif stage_info['is_today']:
            return '#FFD93D'  # 黃色 - 今天
        elif stage_info['days_until'] <= 1:
            return '#FFA726'  # 橙色 - 明天
        elif stage_info['days_until'] <= 3:
            return '#66BB6A'  # 綠色 - 3天內
        else:
            return '#42A5F5'  # 藍色 - 較遠

    @staticmethod
    def count_stages_by_status(upcoming_stages: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        統計各狀態的階段數量

        Args:
            upcoming_stages: 即將到期的階段列表

        Returns:
            Dict[str, int]: 各狀態統計
        """
        counts = {
            'overdue': 0,     # 已過期
            'today': 0,       # 今天
            'tomorrow': 0,    # 明天
            'this_week': 0,   # 本週
            'total': len(upcoming_stages)
        }

        for stage in upcoming_stages:
            if stage['is_overdue']:
                counts['overdue'] += 1
            elif stage['is_today']:
                counts['today'] += 1
            elif stage['days_until'] == 1:
                counts['tomorrow'] += 1
            elif stage['days_until'] <= 7:
                counts['this_week'] += 1

        return counts