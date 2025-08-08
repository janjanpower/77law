#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件查詢路由模組
處理案件相關的API請求
"""

from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, List
import sys
import os

# 添加專案根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 導入schemas
from api.schemas.case_schemas import (
    CaseDetailResponse,
    CaseListResponse,
    DetailedCaseResponse,
    DetailedCaseListResponse,
    CaseProgressHistoryResponse,
    CaseProgressUpdateRequest,
    CaseProgressUpdateResponse,
    CaseStatistics,
    FinalCaseSelectionRequest,
    FinalCaseSelectionResponse,
    convert_case_data_to_response,
    create_case_list_response
)

# 導入控制器
try:
    from controllers.case_controller import CaseController
    CONTROLLER_AVAILABLE = True
except ImportError:
    print("⚠️ 警告：CaseController 不可用")
    CONTROLLER_AVAILABLE = False

# 建立路由器
router = APIRouter()

# 全域變數
controller = None

def get_controller():
    """取得控制器實例"""
    global controller
    if controller is None and CONTROLLER_AVAILABLE:
        try:
            controller = CaseController()
            print("✅ 案件路由：控制器初始化成功")
        except Exception as e:
            print(f"❌ 案件路由：控制器初始化失敗 - {e}")
    return controller

def check_system_availability():
    """檢查系統可用性"""
    if not CONTROLLER_AVAILABLE:
        raise HTTPException(status_code=503, detail="系統模組不可用")

    ctrl = get_controller()
    if not ctrl:
        raise HTTPException(status_code=503, detail="案件控制器不可用")

    return ctrl

# ==================== 基礎案件查詢端點 ====================

@router.get("/{case_id}/detail", response_model=CaseDetailResponse)
async def get_case_detail(case_id: str = Path(..., description="案件編號")):
    """取得指定案件的詳細資料"""
    try:
        ctrl = check_system_availability()

        # 搜尋案件
        cases = ctrl.get_cases()
        case = next((c for c in cases if c.case_id == case_id), None)

        if not case:
            raise HTTPException(status_code=404, detail=f"找不到案件: {case_id}")

        print(f"📋 API請求: 取得案件 {case_id} 詳細資料")
        return convert_case_data_to_response(case)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件詳細資料 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/all/detail", response_model=CaseListResponse)
async def get_all_cases_detail():
    """取得所有案件的詳細資料"""
    try:
        ctrl = check_system_availability()

        cases = ctrl.get_cases()
        result = create_case_list_response(cases)

        print(f"📋 API請求: 取得所有案件詳細資料，共 {result.total_count} 筆")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得所有案件詳細資料 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/search/detail", response_model=CaseListResponse)
async def search_cases_detail(
    keyword: Optional[str] = Query(None, description="關鍵字搜尋"),
    case_type: Optional[str] = Query(None, description="案件類型"),
    lawyer: Optional[str] = Query(None, description="律師"),
    court: Optional[str] = Query(None, description="法院")
):
    """搜尋案件並返回詳細資料"""
    try:
        ctrl = check_system_availability()

        # 取得所有案件
        all_cases = ctrl.get_cases()
        filtered_cases = all_cases

        # 應用過濾條件
        if keyword:
            filtered_cases = [
                case for case in filtered_cases
                if (keyword.lower() in case.client.lower() or
                    keyword.lower() in case.case_id.lower() or
                    (case.case_reason and keyword.lower() in case.case_reason.lower()))
            ]

        if case_type:
            filtered_cases = [
                case for case in filtered_cases
                if case.case_type == case_type
            ]

        if lawyer:
            filtered_cases = [
                case for case in filtered_cases
                if case.lawyer and lawyer.lower() in case.lawyer.lower()
            ]

        if court:
            filtered_cases = [
                case for case in filtered_cases
                if case.court and court.lower() in case.court.lower()
            ]

        result = create_case_list_response(filtered_cases)

        search_params = {k: v for k, v in {
            'keyword': keyword, 'case_type': case_type,
            'lawyer': lawyer, 'court': court
        }.items() if v is not None}

        print(f"📋 API請求: 搜尋案件詳細資料，條件: {search_params}，結果: {result.total_count} 筆")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 搜尋案件詳細資料 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

# ==================== 進度管理端點 ====================

@router.get("/{case_id}/progress-history", response_model=CaseProgressHistoryResponse)
async def get_case_progress_history(case_id: str = Path(..., description="案件編號")):
    """取得案件進度歷史"""
    try:
        ctrl = check_system_availability()

        # 搜尋案件
        cases = ctrl.get_cases()
        case = next((c for c in cases if c.case_id == case_id), None)

        if not case:
            raise HTTPException(status_code=404, detail=f"找不到案件: {case_id}")

        # 構建進度歷史
        from api.schemas.case_schemas import ProgressStageDetail

        progress_stages = []
        order = 0

        for stage_name, date in case.progress_stages.items():
            stage_detail = ProgressStageDetail(
                stage_name=stage_name,
                date=date,
                time=case.progress_times.get(stage_name) if hasattr(case, 'progress_times') else None,
                note=case.progress_notes.get(stage_name) if hasattr(case, 'progress_notes') else None,
                order=order
            )
            progress_stages.append(stage_detail)
            order += 1

        history = CaseProgressHistoryResponse(
            case_id=case.case_id,
            client=case.client,
            case_type=case.case_type,
            current_progress=case.progress,
            total_stages=len(progress_stages),
            progress_stages=progress_stages,
            last_updated=case.updated_date.isoformat() if case.updated_date else ""
        )

        print(f"📋 API請求: 取得案件 {case_id} 進度歷史，共 {history.total_stages} 個階段")
        return history

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件進度歷史 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.post("/progress/update", response_model=CaseProgressUpdateResponse)
async def update_case_progress(request: CaseProgressUpdateRequest):
    """更新案件進度"""
    try:
        ctrl = check_system_availability()

        # 找到案件
        cases = ctrl.get_cases()
        case = next((c for c in cases if c.case_id == request.case_id), None)

        if not case:
            raise HTTPException(status_code=404, detail=f"找不到案件: {request.case_id}")

        # 更新進度
        try:
            case.update_progress(
                new_progress=request.new_progress,
                progress_date=request.progress_date,
                note=request.note,
                time=request.time
            )

            # 儲存變更
            ctrl.save_cases()

            print(f"✅ 更新案件 {request.case_id} 進度: {request.new_progress}")

            return CaseProgressUpdateResponse(
                success=True,
                message=f"案件 {request.case_id} 進度已更新為：{request.new_progress}",
                case_id=request.case_id,
                new_progress=request.new_progress
            )

        except Exception as update_error:
            print(f"❌ 進度更新失敗: {update_error}")
            raise HTTPException(status_code=400, detail=f"進度更新失敗: {str(update_error)}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 更新案件進度 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

# ==================== 統計和查詢端點 ====================

@router.get("/statistics", response_model=CaseStatistics)
async def get_case_statistics():
    """取得案件統計資料"""
    try:
        ctrl = check_system_availability()

        cases = ctrl.get_cases()

        # 計算統計資料
        total_cases = len(cases)

        # 案件類型統計
        case_types = {}
        for case in cases:
            case_type = case.case_type
            case_types[case_type] = case_types.get(case_type, 0) + 1

        # 進度分布統計
        progress_distribution = {}
        for case in cases:
            progress = case.progress
            progress_distribution[progress] = progress_distribution.get(progress, 0) + 1

        # 律師統計
        lawyers = {}
        for case in cases:
            if case.lawyer:
                lawyers[case.lawyer] = lawyers.get(case.lawyer, 0) + 1

        # 法院統計
        courts = {}
        for case in cases:
            if case.court:
                courts[case.court] = courts.get(case.court, 0) + 1

        # 簡化的緊急案件統計
        urgent_keywords = ["開庭", "審理", "宣判", "調解"]
        urgent_cases = len([
            case for case in cases
            if any(keyword in case.progress for keyword in urgent_keywords)
        ])

        statistics = CaseStatistics(
            total_cases=total_cases,
            case_types=case_types,
            progress_distribution=progress_distribution,
            lawyers=lawyers,
            courts=courts,
            recent_cases=total_cases,  # 簡化處理
            urgent_cases=urgent_cases
        )

        print(f"📊 API請求: 取得案件統計，總計 {total_cases} 筆案件")
        return statistics

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件統計 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/types", response_model=List[str])
async def get_case_types():
    """取得所有案件類型"""
    try:
        ctrl = check_system_availability()

        cases = ctrl.get_cases()
        case_types = list(set(case.case_type for case in cases if case.case_type))

        print(f"📋 API請求: 取得案件類型，共 {len(case_types)} 種")
        return sorted(case_types)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件類型 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/lawyers", response_model=List[str])
async def get_lawyers():
    """取得所有律師列表"""
    try:
        ctrl = check_system_availability()

        cases = ctrl.get_cases()
        lawyers = list(set(case.lawyer for case in cases if case.lawyer))

        print(f"📋 API請求: 取得律師列表，共 {len(lawyers)} 位")
        return sorted(lawyers)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得律師列表 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@router.get("/fields/{field_name}/values", response_model=List[str])
async def get_field_unique_values(field_name: str = Path(..., description="欄位名稱")):
    """取得指定欄位的所有唯一值"""
    try:
        ctrl = check_system_availability()

        allowed_fields = ['case_type', 'lawyer', 'court', 'division', 'opposing_party', 'progress']
        if field_name not in allowed_fields:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的欄位名稱: {field_name}。支援的欄位: {', '.join(allowed_fields)}"
            )

        cases = ctrl.get_cases()
        values = set()

        for case in cases:
            if field_name == 'case_type':
                values.add(case.case_type)
            elif field_name == 'lawyer' and case.lawyer:
                values.add(case.lawyer)
            elif field_name == 'court' and case.court:
                values.add(case.court)
            elif field_name == 'division' and hasattr(case, 'division') and case.division:
                values.add(case.division)
            elif field_name == 'opposing_party' and hasattr(case, 'opposing_party') and case.opposing_party:
                values.add(case.opposing_party)
            elif field_name == 'progress':
                values.add(case.progress)

        result = sorted(list(values))
        print(f"📋 API請求: 取得 {field_name} 唯一值，共 {len(result)} 個")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得欄位唯一值 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

# ==================== 最終選擇端點 ====================

@router.post("/final-selection", response_model=FinalCaseSelectionResponse)
async def final_case_selection(request: FinalCaseSelectionRequest):
    """最終案件選擇 - 記錄用戶的最終選擇並返回詳細資料"""
    try:
        ctrl = check_system_availability()

        # 搜尋案件
        cases = ctrl.get_cases()
        case = next((c for c in cases if c.case_id == request.selected_case_id), None)

        if not case:
            raise HTTPException(status_code=404, detail=f"找不到案件: {request.selected_case_id}")

        # 建立回應
        response = FinalCaseSelectionResponse(
            selected_case=convert_case_data_to_response(case),
            user_id=request.user_id,
            success=True,
            message=f"已選擇案件 {request.selected_case_id}"
        )

        print(f"✅ 用戶 {request.user_id} 最終選擇案件: {request.selected_case_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 最終案件選擇 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")