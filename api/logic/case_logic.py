#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件邏輯層 - 業務邏輯處理
將控制器的功能包裝為異步API邏輯，不修改原始程式碼
"""

import asyncio
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

# 導入專案現有模組（不修改原始程式碼）
from models.case_model import CaseData
from controllers.case_controller import CaseController
from config.settings import AppConfig


class CaseLogic:
    """案件業務邏輯層"""

    def __init__(self, data_file: str = None):
        """初始化案件邏輯層"""
        try:
            # 使用現有的 CaseController（不修改原始程式碼）
            self.case_controller = CaseController(data_file)

            # 驗證控制器是否正常初始化（檢查必要屬性）
            if not hasattr(self.case_controller, 'data_manager'):
                raise RuntimeError("CaseController 初始化失敗：缺少 data_manager")

            if not hasattr(self.case_controller, 'folder_manager'):
                raise RuntimeError("CaseController 初始化失敗：缺少 folder_manager")

            print("✅ CaseController 初始化成功")

        except Exception as e:
            print(f"❌ 初始化 CaseController 失敗: {e}")
            raise

    async def get_all_cases(self) -> List[CaseData]:
        """取得所有案件資料（異步包裝）"""
        try:
            # 在執行緒池中執行同步操作
            loop = asyncio.get_event_loop()
            cases = await loop.run_in_executor(
                None,
                self.case_controller.get_cases  # 修正：使用正確的方法名
            )
            return cases if cases else []
        except Exception as e:
            print(f"❌ 取得所有案件失敗: {e}")
            return []

    async def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """根據編號取得案件（異步包裝）"""
        try:
            loop = asyncio.get_event_loop()
            case = await loop.run_in_executor(
                None,
                self.case_controller.get_case_by_id,
                case_id
            )
            return case
        except Exception as e:
            print(f"❌ 取得案件 {case_id} 失敗: {e}")
            return None

    async def create_case(self, case_request) -> CaseData:
        """建立新案件（異步包裝）"""
        try:
            # 將請求轉換為 CaseData 物件
            case_data = CaseData(
                case_id="",  # 將由控制器自動生成
                case_type=case_request.case_type,
                client=case_request.client,
                lawyer=case_request.lawyer,
                legal_affairs=case_request.legal_affairs,
                progress=case_request.progress or "待處理",
                case_reason=case_request.case_reason,
                case_number=case_request.case_number,
                opposing_party=case_request.opposing_party,
                court=case_request.court,
                division=case_request.division,
                progress_date=case_request.progress_date
            )

            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.case_controller.add_case,
                case_data
            )

            if success:
                return case_data
            else:
                raise Exception("建立案件失敗")

        except Exception as e:
            print(f"❌ 建立案件失敗: {e}")
            raise

    async def update_case(self, case_id: str, update_request) -> Optional[CaseData]:
        """更新案件資料（異步包裝）"""
        try:
            # 先取得現有案件
            existing_case = await self.get_case_by_id(case_id)
            if not existing_case:
                return None

            # 更新欄位
            if update_request.client is not None:
                existing_case.client = update_request.client
            if update_request.lawyer is not None:
                existing_case.lawyer = update_request.lawyer
            if update_request.legal_affairs is not None:
                existing_case.legal_affairs = update_request.legal_affairs
            if update_request.progress is not None:
                existing_case.progress = update_request.progress
            if update_request.case_reason is not None:
                existing_case.case_reason = update_request.case_reason
            if update_request.case_number is not None:
                existing_case.case_number = update_request.case_number
            if update_request.opposing_party is not None:
                existing_case.opposing_party = update_request.opposing_party
            if update_request.court is not None:
                existing_case.court = update_request.court
            if update_request.division is not None:
                existing_case.division = update_request.division
            if update_request.progress_date is not None:
                existing_case.progress_date = update_request.progress_date

            # 更新時間戳
            existing_case.updated_date = datetime.now()

            # 使用控制器更新
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.case_controller.update_case,
                existing_case
            )

            return existing_case if success else None

        except Exception as e:
            print(f"❌ 更新案件 {case_id} 失敗: {e}")
            return None

    async def delete_case(self, case_id: str) -> bool:
        """刪除案件（異步包裝）"""
        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.case_controller.delete_case,
                case_id
            )
            return success
        except Exception as e:
            print(f"❌ 刪除案件 {case_id} 失敗: {e}")
            return False

    async def update_case_progress(self, case_id: str, progress_request) -> bool:
        """更新案件進度（異步包裝）"""
        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.case_controller.add_case_progress_stage,  # 修正：使用正確的方法名
                case_id,
                progress_request.stage_name,
                progress_request.stage_date,
                progress_request.note,
                progress_request.time
            )
            return success
        except Exception as e:
            print(f"❌ 更新案件進度失敗: {e}")
            return False

    async def get_case_progress_history(self, case_id: str) -> Optional[Dict[str, Any]]:
        """取得案件進度歷史（異步包裝）"""
        try:
            case = await self.get_case_by_id(case_id)
            if not case:
                return None

            return {
                "current_progress": case.progress,
                "progress_date": case.progress_date,
                "progress_stages": case.progress_stages,
                "progress_notes": getattr(case, 'progress_notes', {}),
                "progress_times": getattr(case, 'progress_times', {})
            }
        except Exception as e:
            print(f"❌ 取得案件進度歷史失敗: {e}")
            return None

    async def search_cases(self, search_criteria: Dict[str, Any]) -> List[CaseData]:
        """搜尋案件（異步包裝）"""
        try:
            all_cases = await self.get_all_cases()

            # 根據搜尋條件篩選
            filtered_cases = []
            for case in all_cases:
                match = True

                if search_criteria.get('client'):
                    if search_criteria['client'].lower() not in case.client.lower():
                        match = False

                if search_criteria.get('case_type'):
                    if case.case_type != search_criteria['case_type']:
                        match = False

                if search_criteria.get('progress'):
                    if case.progress != search_criteria['progress']:
                        match = False

                if search_criteria.get('lawyer'):
                    if not case.lawyer or search_criteria['lawyer'].lower() not in case.lawyer.lower():
                        match = False

                if match:
                    filtered_cases.append(case)

            return filtered_cases

        except Exception as e:
            print(f"❌ 搜尋案件失敗: {e}")
            return []

    async def get_case_statistics(self) -> Dict[str, Any]:
        """取得案件統計資料（異步包裝）"""
        try:
            all_cases = await self.get_all_cases()

            # 統計各種資料
            stats = {
                "total_cases": len(all_cases),
                "case_types": {},
                "progress_stages": {},
                "lawyers": {},
                "courts": {},
                "recent_cases": 0
            }

            # 計算最近30天的案件
            recent_threshold = datetime.now().timestamp() - (30 * 24 * 60 * 60)

            for case in all_cases:
                # 案件類型統計
                case_type = case.case_type
                stats["case_types"][case_type] = stats["case_types"].get(case_type, 0) + 1

                # 進度階段統計
                progress = case.progress
                stats["progress_stages"][progress] = stats["progress_stages"].get(progress, 0) + 1

                # 律師統計
                if case.lawyer:
                    lawyer = case.lawyer
                    stats["lawyers"][lawyer] = stats["lawyers"].get(lawyer, 0) + 1

                # 法院統計
                if case.court:
                    court = case.court
                    stats["courts"][court] = stats["courts"].get(court, 0) + 1

                # 最近案件統計
                if case.created_date.timestamp() > recent_threshold:
                    stats["recent_cases"] += 1

            return stats

        except Exception as e:
            print(f"❌ 取得統計資料失敗: {e}")
            return {}

    async def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態（異步包裝）"""
        try:
            # 檢查資料檔案狀態
            data_file_exists = os.path.exists(self.case_controller.data_file)
            data_folder_exists = os.path.exists(self.case_controller.data_folder)

            # 取得案件數量
            cases_count = len(await self.get_all_cases())

            # 檢查控制器狀態（修正：檢查必要屬性而不是 is_initialized）
            controller_status = (
                hasattr(self.case_controller, 'data_manager') and
                hasattr(self.case_controller, 'folder_manager')
            )

            status = {
                "controller_initialized": controller_status,
                "data_file_exists": data_file_exists,
                "data_folder_exists": data_folder_exists,
                "total_cases": cases_count,
                "data_file_path": self.case_controller.data_file,
                "data_folder_path": self.case_controller.data_folder,
                "last_check": datetime.now().isoformat()
            }

            return status

        except Exception as e:
            print(f"❌ 取得系統狀態失敗: {e}")
            return {
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }

    async def get_cases_by_client(self, client_name: str) -> List[CaseData]:
        """根據當事人姓名取得案件（新增功能）"""
        try:
            search_criteria = {"client": client_name}
            return await self.search_cases(search_criteria)
        except Exception as e:
            print(f"❌ 根據當事人取得案件失敗: {e}")
            return []

    async def get_urgent_cases(self, days_threshold: int = 7) -> List[CaseData]:
        """取得緊急案件（需要關注的案件）"""
        try:
            all_cases = await self.get_all_cases()
            urgent_cases = []

            current_time = datetime.now()

            for case in all_cases:
                # 判斷緊急標準（可以根據需求調整）
                is_urgent = False

                # 如果案件長時間沒有進度更新
                if case.progress_date:
                    try:
                        progress_date = datetime.strptime(case.progress_date, '%Y-%m-%d')
                        days_since_update = (current_time - progress_date).days
                        if days_since_update > days_threshold:
                            is_urgent = True
                    except ValueError:
                        pass

                # 或者是特定進度階段需要注意的
                urgent_stages = ["開庭", "調解", "審理", "宣判"]
                if case.progress in urgent_stages:
                    is_urgent = True

                if is_urgent:
                    urgent_cases.append(case)

            return urgent_cases

        except Exception as e:
            print(f"❌ 取得緊急案件失敗: {e}")
            return []