#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Webhook 邏輯層 - LINE 訊息處理
處理來自 N8N 的 LINE Webhook 請求，分析訊息意圖並回覆適當內容
"""

import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 導入案件邏輯層
from api.logic.case_logic import CaseLogic


class WebhookLogic:
    """Webhook 業務邏輯層"""

    def __init__(self):
        """初始化 Webhook 邏輯層"""
        self.case_logic = CaseLogic()

        # 預定義的關鍵字和意圖對應
        self.intent_keywords = {
            "查詢案件": ["查詢", "查看", "案件", "進度", "狀況", "情況"],
            "新增案件": ["新增", "新建", "建立", "新案件", "新的案件"],
            "更新進度": ["更新", "修改", "進度", "階段", "狀態"],
            "統計資料": ["統計", "報表", "數量", "總計", "彙總"],
            "緊急案件": ["緊急", "重要", "優先", "急件", "催辦"],
            "律師查詢": ["律師", "代理人", "負責律師"],
            "法院資訊": ["法院", "開庭", "審理", "庭期"],
            "幫助": ["幫助", "說明", "教學", "怎麼用", "功能"]
        }

        # 回覆模板
        self.response_templates = {
            "查詢案件_無結果": "抱歉，沒有找到符合條件的案件。",
            "查詢案件_單筆": "找到案件：{case_info}",
            "查詢案件_多筆": "找到 {count} 筆案件：\n{case_list}",
            "新增案件_成功": "案件已成功建立，案件編號：{case_id}",
            "新增案件_失敗": "案件建立失敗，請檢查資料格式。",
            "更新進度_成功": "案件 {case_id} 進度已更新為：{progress}",
            "更新進度_失敗": "進度更新失敗，請確認案件編號。",
            "統計資料": "📊 案件統計：\n總案件數：{total}\n刑事案件：{criminal}\n民事案件：{civil}",
            "緊急案件": "🚨 緊急案件提醒：\n{urgent_list}",
            "系統錯誤": "系統發生錯誤，請稍後再試。",
            "無法理解": "抱歉，我無法理解您的需求。請輸入「幫助」查看可用功能。",
            "幫助": """📋 案件管理系統功能：
1. 查詢案件：輸入「查詢 [當事人姓名]」
2. 新增案件：輸入「新增案件 [案件資訊]」
3. 更新進度：輸入「更新 [案件編號] [新進度]」
4. 統計資料：輸入「統計」
5. 緊急案件：輸入「緊急」
6. 律師查詢：輸入「律師 [姓名]」"""
        }

    async def process_line_message(self, webhook_request) -> Any:
        """
        處理 LINE Webhook 訊息的主要函數

        Args:
            webhook_request: 來自 N8N 的 Webhook 請求

        Returns:
            回覆給 LINE 的訊息格式
        """
        try:
            # 解析訊息內容
            message_text = webhook_request.message
            user_id = webhook_request.user_id

            print(f"📨 收到 LINE 訊息: {message_text} (用戶: {user_id})")

            # 分析訊息意圖
            intent, extracted_data = await self.analyze_message_intent(message_text, user_id)

            # 根據意圖處理並生成回覆
            response_message = await self.handle_intent(intent, extracted_data, user_id)

            # 構建回覆格式
            webhook_response = {
                "type": "text",
                "text": response_message,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "processed_intent": intent
            }

            print(f"📤 回覆訊息: {response_message}")

            return webhook_response

        except Exception as e:
            print(f"❌ 處理 LINE 訊息失敗: {e}")
            return {
                "type": "text",
                "text": self.response_templates["系統錯誤"],
                "user_id": webhook_request.user_id if hasattr(webhook_request, 'user_id') else "unknown",
                "error": str(e)
            }

    async def analyze_message_intent(self, message_text: str, user_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        分析訊息意圖和提取相關資料

        Args:
            message_text: 用戶訊息文字
            user_id: 用戶ID

        Returns:
            (意圖, 提取的資料)
        """
        try:
            message_lower = message_text.lower()
            extracted_data = {"original_message": message_text, "user_id": user_id}

            # 1. 查詢案件意圖
            if any(keyword in message_lower for keyword in self.intent_keywords["查詢案件"]):
                # 提取當事人姓名或案件編號
                client_match = re.search(r'查詢\s*(.+)', message_text)
                if client_match:
                    extracted_data["client_name"] = client_match.group(1).strip()
                return "查詢案件", extracted_data

            # 2. 新增案件意圖
            if any(keyword in message_lower for keyword in self.intent_keywords["新增案件"]):
                # 嘗試解析案件資訊
                case_data = self._extract_case_data_from_message(message_text)
                extracted_data.update(case_data)
                return "新增案件", extracted_data

            # 3. 更新進度意圖
            if any(keyword in message_lower for keyword in self.intent_keywords["更新進度"]):
                # 提取案件編號和新進度
                progress_match = re.search(r'更新\s*(\S+)\s*(.+)', message_text)
                if progress_match:
                    extracted_data["case_id"] = progress_match.group(1).strip()
                    extracted_data["new_progress"] = progress_match.group(2).strip()
                return "更新進度", extracted_data

            # 4. 統計資料意圖
            if any(keyword in message_lower for keyword in self.intent_keywords["統計資料"]):
                return "統計資料", extracted_data

            # 5. 緊急案件意圖
            if any(keyword in message_lower for keyword in self.intent_keywords["緊急案件"]):
                return "緊急案件", extracted_data

            # 6. 律師查詢意圖
            if any(keyword in message_lower for keyword in self.intent_keywords["律師查詢"]):
                lawyer_match = re.search(r'律師\s*(.+)', message_text)
                if lawyer_match:
                    extracted_data["lawyer_name"] = lawyer_match.group(1).strip()
                return "律師查詢", extracted_data

            # 7. 幫助意圖
            if any(keyword in message_lower for keyword in self.intent_keywords["幫助"]):
                return "幫助", extracted_data

            # 8. 無法識別的意圖
            return "無法理解", extracted_data

        except Exception as e:
            print(f"❌ 分析訊息意圖失敗: {e}")
            return "系統錯誤", extracted_data

    def _extract_case_data_from_message(self, message: str) -> Dict[str, str]:
        """從訊息中提取案件資料"""
        case_data = {}

        # 簡單的關鍵字提取（可以根據需求擴展）
        patterns = {
            "client": r'當事人[:：]\s*(\S+)',
            "case_type": r'類型[:：]\s*(\S+)',
            "lawyer": r'律師[:：]\s*(\S+)',
            "case_reason": r'案由[:：]\s*(.+?)(?=\s|$)',
            "court": r'法院[:：]\s*(\S+)'
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, message)
            if match:
                case_data[field] = match.group(1).strip()

        return case_data

    async def handle_intent(self, intent: str, extracted_data: Dict[str, Any], user_id: str) -> str:
        """
        根據意圖處理業務邏輯並生成回覆

        Args:
            intent: 識別的意圖
            extracted_data: 提取的資料
            user_id: 用戶ID

        Returns:
            回覆訊息文字
        """
        try:
            if intent == "查詢案件":
                return await self._handle_query_cases(extracted_data)

            elif intent == "新增案件":
                return await self._handle_create_case(extracted_data)

            elif intent == "更新進度":
                return await self._handle_update_progress(extracted_data)

            elif intent == "統計資料":
                return await self._handle_get_statistics()

            elif intent == "緊急案件":
                return await self._handle_get_urgent_cases()

            elif intent == "律師查詢":
                return await self._handle_query_by_lawyer(extracted_data)

            elif intent == "幫助":
                return self.response_templates["幫助"]

            elif intent == "系統錯誤":
                return self.response_templates["系統錯誤"]

            else:
                return self.response_templates["無法理解"]

        except Exception as e:
            print(f"❌ 處理意圖失敗: {e}")
            return self.response_templates["系統錯誤"]

    async def _handle_query_cases(self, data: Dict[str, Any]) -> str:
        """處理案件查詢"""
        try:
            client_name = data.get("client_name", "").strip()

            if not client_name:
                return "請提供當事人姓名，例如：「查詢 張三」"

            # 使用案件邏輯層查詢
            cases = await self.case_logic.get_cases_by_client(client_name)

            if not cases:
                return self.response_templates["查詢案件_無結果"]

            elif len(cases) == 1:
                case = cases[0]
                case_info = f"{case.case_id} - {case.client} ({case.case_type}) - {case.progress}"
                return self.response_templates["查詢案件_單筆"].format(case_info=case_info)

            else:
                case_list = []
                for case in cases[:5]:  # 最多顯示5筆
                    case_info = f"• {case.case_id} - {case.case_type} - {case.progress}"
                    case_list.append(case_info)

                case_list_str = "\n".join(case_list)
                if len(cases) > 5:
                    case_list_str += f"\n... 還有 {len(cases) - 5} 筆案件"

                return self.response_templates["查詢案件_多筆"].format(
                    count=len(cases),
                    case_list=case_list_str
                )

        except Exception as e:
            print(f"❌ 處理案件查詢失敗: {e}")
            return self.response_templates["系統錯誤"]

    async def _handle_create_case(self, data: Dict[str, Any]) -> str:
        """處理案件新增"""
        try:
            # 檢查必要欄位
            required_fields = ["client", "case_type"]
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                return f"請提供必要資訊：{', '.join(missing_fields)}"

            # 這裡簡化處理，實際應該要有完整的案件建立邏輯
            # 由於原始程式碼的複雜性，這裡先返回提示訊息
            return "案件新增功能需要更詳細的資訊，建議透過系統介面操作。"

        except Exception as e:
            print(f"❌ 處理案件新增失敗: {e}")
            return self.response_templates["新增案件_失敗"]

    async def _handle_update_progress(self, data: Dict[str, Any]) -> str:
        """處理進度更新"""
        try:
            case_id = data.get("case_id")
            new_progress = data.get("new_progress")

            if not case_id or not new_progress:
                return "請提供案件編號和新進度，例如：「更新 113001 開庭」"

            # 檢查案件是否存在
            case = await self.case_logic.get_case_by_id(case_id)
            if not case:
                return f"找不到案件編號：{case_id}"

            # 這裡簡化處理，實際的進度更新邏輯比較複雜
            return f"案件 {case_id} 的進度更新需要透過系統介面操作以確保資料完整性。"

        except Exception as e:
            print(f"❌ 處理進度更新失敗: {e}")
            return self.response_templates["更新進度_失敗"]

    async def _handle_get_statistics(self) -> str:
        """處理統計資料查詢"""
        try:
            stats = await self.case_logic.get_case_statistics()

            criminal_count = stats.get("case_types", {}).get("刑事", 0)
            civil_count = stats.get("case_types", {}).get("民事", 0)
            total_count = stats.get("total_cases", 0)

            return self.response_templates["統計資料"].format(
                total=total_count,
                criminal=criminal_count,
                civil=civil_count
            )

        except Exception as e:
            print(f"❌ 處理統計資料失敗: {e}")
            return self.response_templates["系統錯誤"]

    async def _handle_get_urgent_cases(self) -> str:
        """處理緊急案件查詢"""
        try:
            urgent_cases = await self.case_logic.get_urgent_cases()

            if not urgent_cases:
                return "目前沒有需要特別關注的緊急案件。"

            urgent_list = []
            for case in urgent_cases[:3]:  # 最多顯示3筆
                urgent_info = f"• {case.case_id} - {case.client} ({case.progress})"
                urgent_list.append(urgent_info)

            urgent_list_str = "\n".join(urgent_list)

            return self.response_templates["緊急案件"].format(urgent_list=urgent_list_str)

        except Exception as e:
            print(f"❌ 處理緊急案件查詢失敗: {e}")
            return self.response_templates["系統錯誤"]

    async def _handle_query_by_lawyer(self, data: Dict[str, Any]) -> str:
        """處理律師案件查詢"""
        try:
            lawyer_name = data.get("lawyer_name", "").strip()

            if not lawyer_name:
                return "請提供律師姓名，例如：「律師 王律師」"

            # 搜尋該律師的案件
            search_criteria = {"lawyer": lawyer_name}
            cases = await self.case_logic.search_cases(search_criteria)

            if not cases:
                return f"找不到律師「{lawyer_name}」的案件。"

            case_list = []
            for case in cases[:5]:  # 最多顯示5筆
                case_info = f"• {case.case_id} - {case.client} ({case.progress})"
                case_list.append(case_info)

            case_list_str = "\n".join(case_list)
            return f"律師「{lawyer_name}」的案件：\n{case_list_str}"

        except Exception as e:
            print(f"❌ 處理律師查詢失敗: {e}")
            return self.response_templates["系統錯誤"]