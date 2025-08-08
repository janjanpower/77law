#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
案件詳細資料 API 控制層與邏輯層
為現有的 api.py 添加案件詳細資料查詢功能
基於現有架構，不破壞原有功能
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field


app = FastAPI()

# ==================== 第二步：在現有資料模型後添加新的資料模型 ====================

class DetailedCaseResponse(BaseModel):
    """增強的案件詳細資料回應模型 - 包含案號、對造、股別等"""
    case_id: str = Field(..., description="案件編號")
    case_type: str = Field(..., description="案件類型")
    client: str = Field(..., description="當事人姓名")
    lawyer: Optional[str] = Field(default=None, description="委任律師")
    legal_affairs: Optional[str] = Field(default=None, description="法務人員")
    progress: str = Field(..., description="當前進度")

    # 🔥 新增：詳細資訊欄位
    case_reason: Optional[str] = Field(default=None, description="案由")
    case_number: Optional[str] = Field(default=None, description="案號")
    opposing_party: Optional[str] = Field(default=None, description="對造")
    court: Optional[str] = Field(default=None, description="負責法院")
    division: Optional[str] = Field(default=None, description="負責股別")

    # 🔥 新增：進度相關的詳細資訊
    progress_date: Optional[str] = Field(default=None, description="當前進度日期")
    progress_stages: Dict[str, str] = Field(default_factory=dict, description="進度階段與日期記錄")
    progress_notes: Dict[str, str] = Field(default_factory=dict, description="各階段備註")
    progress_times: Dict[str, str] = Field(default_factory=dict, description="各階段時間")

    created_date: str = Field(..., description="建立日期")
    updated_date: str = Field(..., description="更新日期")
    folder_info: Optional[Dict[str, Any]] = Field(default=None, description="案件資料夾資訊")

class DetailedCaseListResponse(BaseModel):
    """詳細案件列表回應模型"""
    total_count: int = Field(..., description="總案件數")
    cases: List[DetailedCaseResponse] = Field(..., description="案件列表")
    search_criteria: Optional[Dict[str, Any]] = Field(default=None, description="搜尋條件")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="查詢時間")

class CaseProgressUpdateRequest(BaseModel):
    """案件進度更新請求模型"""
    case_id: str = Field(..., description="案件編號")
    new_progress: str = Field(..., description="新進度")
    progress_date: Optional[str] = Field(default=None, description="進度日期")
    note: Optional[str] = Field(default=None, description="備註")
    time: Optional[str] = Field(default=None, description="時間")

class ProgressStageDetail(BaseModel):
    """進度階段詳細資訊"""
    stage_name: str = Field(..., description="階段名稱")
    stage_date: str = Field(..., description="階段日期")
    stage_time: Optional[str] = Field(default=None, description="階段時間")
    stage_note: Optional[str] = Field(default=None, description="階段備註")

class CaseProgressHistoryResponse(BaseModel):
    """案件進度歷史回應模型"""
    case_id: str = Field(..., description="案件編號")
    client: str = Field(..., description="當事人")
    current_progress: str = Field(..., description="當前進度")
    progress_history: List[ProgressStageDetail] = Field(..., description="進度歷史清單")
    total_stages: int = Field(..., description="總階段數")

# ==================== 第三步：在全域變數區域添加 ====================

# 在現有的全域變數（controller = None, user_conversations = {}, case_detail_logic = None）後添加：
enhanced_case_detail_logic = None  # 新增：增強案件詳細資料邏輯層

# ==================== 第四步：添加增強邏輯層類別 ====================

class EnhancedCaseDetailLogic:
    """增強的案件詳細資料邏輯層"""

    def __init__(self, case_controller):
        """初始化邏輯層"""
        self.controller = case_controller
        print("✅ 增強案件詳細資料邏輯層初始化完成")

    def convert_case_to_detailed_response(self, case_data) -> DetailedCaseResponse:
        """將CaseData轉換為DetailedCaseResponse"""
        try:
            # 取得資料夾資訊
            folder_info = None
            try:
                if hasattr(self.controller, 'folder_manager'):
                    folder_info = {
                        'has_folder': True,
                        'folder_path': f"案件資料夾/{case_data.case_type}/{case_data.case_id}_{case_data.client}"
                    }
            except Exception as e:
                print(f"取得資料夾資訊失敗: {e}")

            return DetailedCaseResponse(
                case_id=case_data.case_id,
                case_type=case_data.case_type,
                client=case_data.client,
                lawyer=case_data.lawyer,
                legal_affairs=case_data.legal_affairs,
                progress=case_data.progress,

                # 🔥 詳細資訊欄位
                case_reason=getattr(case_data, 'case_reason', None),
                case_number=getattr(case_data, 'case_number', None),
                opposing_party=getattr(case_data, 'opposing_party', None),
                court=getattr(case_data, 'court', None),
                division=getattr(case_data, 'division', None),

                # 🔥 進度相關詳細資訊
                progress_date=getattr(case_data, 'progress_date', None),
                progress_stages=getattr(case_data, 'progress_stages', {}),
                progress_notes=getattr(case_data, 'progress_notes', {}),
                progress_times=getattr(case_data, 'progress_times', {}),

                created_date=case_data.created_date.isoformat(),
                updated_date=case_data.updated_date.isoformat(),
                folder_info=folder_info
            )
        except Exception as e:
            print(f"轉換案件資料失敗: {e}")
            raise

    def get_detailed_case_by_id(self, case_id: str) -> Optional[DetailedCaseResponse]:
        """取得指定案件的詳細資料"""
        try:
            case = self.controller.get_case_by_id(case_id)
            if not case:
                return None

            return self.convert_case_to_detailed_response(case)
        except Exception as e:
            print(f"取得案件詳細資料失敗: {e}")
            return None

    def get_all_detailed_cases(self) -> DetailedCaseListResponse:
        """取得所有案件的詳細資料"""
        try:
            all_cases = self.controller.get_cases()
            detailed_cases = []

            for case in all_cases:
                try:
                    detailed_case = self.convert_case_to_detailed_response(case)
                    detailed_cases.append(detailed_case)
                except Exception as e:
                    print(f"轉換案件 {case.case_id} 失敗: {e}")
                    continue

            return DetailedCaseListResponse(
                total_count=len(detailed_cases),
                cases=detailed_cases
            )
        except Exception as e:
            print(f"取得所有案件詳細資料失敗: {e}")
            return DetailedCaseListResponse(total_count=0, cases=[])

    def search_detailed_cases(self, keyword: str = None, case_type: str = None,
                             lawyer: str = None, court: str = None,
                             division: str = None, opposing_party: str = None) -> DetailedCaseListResponse:
        """搜尋案件並返回詳細資料"""
        try:
            all_cases = self.controller.get_cases()
            filtered_cases = []

            # 建立搜尋條件
            search_criteria = {}
            if keyword:
                search_criteria['keyword'] = keyword
            if case_type:
                search_criteria['case_type'] = case_type
            if lawyer:
                search_criteria['lawyer'] = lawyer
            if court:
                search_criteria['court'] = court
            if division:
                search_criteria['division'] = division
            if opposing_party:
                search_criteria['opposing_party'] = opposing_party

            for case in all_cases:
                match = True

                # 關鍵字搜尋
                if keyword:
                    keyword_lower = keyword.lower()
                    if not any([
                        keyword_lower in case.case_id.lower(),
                        keyword_lower in case.client.lower(),
                        keyword_lower in (case.lawyer or '').lower(),
                        keyword_lower in (getattr(case, 'case_reason', '') or '').lower(),
                        keyword_lower in (getattr(case, 'case_number', '') or '').lower(),
                        keyword_lower in (getattr(case, 'opposing_party', '') or '').lower()
                    ]):
                        match = False

                # 案件類型過濾
                if case_type and case.case_type != case_type:
                    match = False

                # 律師過濾
                if lawyer and case.lawyer != lawyer:
                    match = False

                # 法院過濾
                if court and getattr(case, 'court', None) != court:
                    match = False

                # 股別過濾
                if division and getattr(case, 'division', None) != division:
                    match = False

                # 對造過濾
                if opposing_party and getattr(case, 'opposing_party', None) != opposing_party:
                    match = False

                if match:
                    try:
                        detailed_case = self.convert_case_to_detailed_response(case)
                        filtered_cases.append(detailed_case)
                    except Exception as e:
                        print(f"轉換搜尋結果案件 {case.case_id} 失敗: {e}")
                        continue

            return DetailedCaseListResponse(
                total_count=len(filtered_cases),
                cases=filtered_cases,
                search_criteria=search_criteria
            )
        except Exception as e:
            print(f"搜尋案件詳細資料失敗: {e}")
            return DetailedCaseListResponse(total_count=0, cases=[], search_criteria={})

    def get_case_progress_history(self, case_id: str) -> Optional[CaseProgressHistoryResponse]:
        """取得案件進度歷史"""
        try:
            case = self.controller.get_case_by_id(case_id)
            if not case:
                return None

            progress_history = []

            # 取得進度階段資料
            progress_stages = getattr(case, 'progress_stages', {})
            progress_notes = getattr(case, 'progress_notes', {})
            progress_times = getattr(case, 'progress_times', {})

            # 將進度階段轉換為清單並排序
            for stage_name, stage_date in progress_stages.items():
                progress_detail = ProgressStageDetail(
                    stage_name=stage_name,
                    stage_date=stage_date,
                    stage_time=progress_times.get(stage_name),
                    stage_note=progress_notes.get(stage_name)
                )
                progress_history.append(progress_detail)

            # 按日期排序
            progress_history.sort(key=lambda x: x.stage_date)

            return CaseProgressHistoryResponse(
                case_id=case.case_id,
                client=case.client,
                current_progress=case.progress,
                progress_history=progress_history,
                total_stages=len(progress_history)
            )
        except Exception as e:
            print(f"取得案件進度歷史失敗: {e}")
            return None

    def update_case_progress(self, request: CaseProgressUpdateRequest) -> bool:
        """更新案件進度"""
        try:
            case = self.controller.get_case_by_id(request.case_id)
            if not case:
                return False

            # 更新進度
            case.update_progress(
                new_progress=request.new_progress,
                progress_date=request.progress_date,
                note=request.note,
                time=request.time
            )

            # 儲存變更
            return self.controller.save_cases()
        except Exception as e:
            print(f"更新案件進度失敗: {e}")
            return False

    def get_unique_values(self, field_name: str) -> List[str]:
        """取得指定欄位的唯一值清單"""
        try:
            all_cases = self.controller.get_cases()
            values = set()

            for case in all_cases:
                if field_name == 'case_type':
                    values.add(case.case_type)
                elif field_name == 'lawyer':
                    if case.lawyer:
                        values.add(case.lawyer)
                elif field_name == 'court':
                    court = getattr(case, 'court', None)
                    if court:
                        values.add(court)
                elif field_name == 'division':
                    division = getattr(case, 'division', None)
                    if division:
                        values.add(division)
                elif field_name == 'opposing_party':
                    opposing_party = getattr(case, 'opposing_party', None)
                    if opposing_party:
                        values.add(opposing_party)
                elif field_name == 'progress':
                    values.add(case.progress)

            return sorted(list(values))
        except Exception as e:
            print(f"取得 {field_name} 唯一值失敗: {e}")
            return []

# ==================== 第五步：添加邏輯層初始化函數 ====================

def get_enhanced_case_detail_logic():
    """取得增強案件詳細資料邏輯層"""
    global enhanced_case_detail_logic
    if enhanced_case_detail_logic is None and MODULES_OK:
        try:
            ctrl = get_controller()
            enhanced_case_detail_logic = EnhancedCaseDetailLogic(ctrl)
            print("✅ 增強案件詳細資料邏輯層初始化成功")
        except Exception as e:
            print(f"❌ 增強案件詳細資料邏輯層初始化失敗: {e}")
            raise
    return enhanced_case_detail_logic

# ==================== 第六步：添加所有新的API端點 ====================

@app.get("/api/cases/{case_id}/detailed", response_model=DetailedCaseResponse)
def get_detailed_case(case_id: str = Path(..., description="案件編號")):
    """取得指定案件的完整詳細資料（包含案號、對造、股別等）"""
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        enhanced_logic = get_enhanced_case_detail_logic()
        detail = enhanced_logic.get_detailed_case_by_id(case_id)

        if not detail:
            raise HTTPException(status_code=404, detail=f"找不到案件: {case_id}")

        print(f"📋 API請求: 取得案件 {case_id} 詳細資料")
        return detail

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件詳細資料 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.get("/api/cases/all/detailed", response_model=DetailedCaseListResponse)
def get_all_detailed_cases():
    """取得所有案件的完整詳細資料"""
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        enhanced_logic = get_enhanced_case_detail_logic()
        result = enhanced_logic.get_all_detailed_cases()

        print(f"📋 API請求: 取得所有案件詳細資料，共 {result.total_count} 筆")
        return result

    except Exception as e:
        print(f"❌ 取得所有案件詳細資料 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.get("/api/cases/search/detailed", response_model=DetailedCaseListResponse)
def search_detailed_cases(
    keyword: Optional[str] = Query(None, description="關鍵字搜尋"),
    case_type: Optional[str] = Query(None, description="案件類型"),
    lawyer: Optional[str] = Query(None, description="律師"),
    court: Optional[str] = Query(None, description="法院"),
    division: Optional[str] = Query(None, description="股別"),
    opposing_party: Optional[str] = Query(None, description="對造")
):
    """搜尋案件並返回完整詳細資料（支援案號、對造、股別等進階搜尋）"""
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        enhanced_logic = get_enhanced_case_detail_logic()
        result = enhanced_logic.search_detailed_cases(
            keyword=keyword,
            case_type=case_type,
            lawyer=lawyer,
            court=court,
            division=division,
            opposing_party=opposing_party
        )

        search_params = {k: v for k, v in {
            'keyword': keyword, 'case_type': case_type,
            'lawyer': lawyer, 'court': court,
            'division': division, 'opposing_party': opposing_party
        }.items() if v is not None}

        print(f"📋 API請求: 搜尋案件詳細資料，條件: {search_params}，結果: {result.total_count} 筆")
        return result

    except Exception as e:
        print(f"❌ 搜尋案件詳細資料 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.get("/api/cases/{case_id}/progress-history", response_model=CaseProgressHistoryResponse)
def get_case_progress_history(case_id: str = Path(..., description="案件編號")):
    """取得案件進度歷史（包含各階段日期、時間、備註）"""
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        enhanced_logic = get_enhanced_case_detail_logic()
        history = enhanced_logic.get_case_progress_history(case_id)

        if not history:
            raise HTTPException(status_code=404, detail=f"找不到案件: {case_id}")

        print(f"📋 API請求: 取得案件 {case_id} 進度歷史，共 {history.total_stages} 個階段")
        return history

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得案件進度歷史 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.post("/api/cases/progress/update")
def update_case_progress(request: CaseProgressUpdateRequest):
    """更新案件進度（包含日期、時間、備註）"""
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        enhanced_logic = get_enhanced_case_detail_logic()
        success = enhanced_logic.update_case_progress(request)

        if not success:
            raise HTTPException(status_code=404, detail=f"找不到案件或更新失敗: {request.case_id}")

        print(f"✅ 更新案件 {request.case_id} 進度: {request.new_progress}")
        return {
            "success": True,
            "message": f"案件 {request.case_id} 進度已更新為：{request.new_progress}",
            "case_id": request.case_id,
            "new_progress": request.new_progress
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 更新案件進度 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

@app.get("/api/cases/fields/{field_name}/values", response_model=List[str])
def get_field_unique_values(field_name: str = Path(..., description="欄位名稱")):
    """取得指定欄位的所有唯一值（支援：case_type, lawyer, court, division, opposing_party, progress）"""
    try:
        if not MODULES_OK:
            raise HTTPException(status_code=503, detail="系統模組不可用")

        allowed_fields = ['case_type', 'lawyer', 'court', 'division', 'opposing_party', 'progress']
        if field_name not in allowed_fields:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的欄位名稱: {field_name}。支援的欄位: {', '.join(allowed_fields)}"
            )

        enhanced_logic = get_enhanced_case_detail_logic()
        values = enhanced_logic.get_unique_values(field_name)

        print(f"📋 API請求: 取得 {field_name} 唯一值，共 {len(values)} 個")
        return values

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 取得欄位唯一值 API 錯誤: {e}")
        raise HTTPException(status_code=500, detail="系統錯誤")

# ==================== 第七步：修改 main 區塊 ====================

# 在現有的 if __name__ == "__main__": 區塊中，在 uvicorn.run 之前添加：

"""
if __name__ == "__main__":
    if MODULES_OK:
        try:
            ctrl = get_controller()

            # 原有的邏輯層初始化
            detail_logic = get_case_detail_logic()
            setup_case_detail_endpoints(app, ctrl, detail_logic)
            print("✅ 原有案件詳細資料 API 端點設置完成")

            # 🔥 新增：增強邏輯層初始化
            enhanced_logic = get_enhanced_case_detail_logic()
            print("✅ 增強案件詳細資料 API 端點設置完成")

        except Exception as e:
            print(f"❌ 設置 API 端點失敗: {e}")

    # 原有的 uvicorn.run 程式碼
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
"""

# ==================== 完整的API端點列表 ====================

"""
🔥 新增的API端點清單：

1. GET /api/cases/{case_id}/detailed
   ✅ 取得指定案件的完整詳細資料
   ✅ 包含：案號、對造、股別、進度階段、日期、備註

2. GET /api/cases/all/detailed
   ✅ 取得所有案件的完整詳細資料

3. GET /api/cases/search/detailed
   ✅ 進階搜尋案件（支援案號、對造、股別等欄位搜尋）
   ✅ 查詢參數：keyword, case_type, lawyer, court, division, opposing_party

4. GET /api/cases/{case_id}/progress-history
   ✅ 取得案件進度歷史
   ✅ 包含：各階段日期、時間、備註

5. POST /api/cases/progress/update
   ✅ 更新案件進度
   ✅ 支援：日期、時間、備註同時更新

6. GET /api/cases/fields/{field_name}/values
   ✅ 取得欄位唯一值清單
   ✅ 支援欄位：case_type, lawyer, court, division, opposing_party, progress

🎯 使用方式：
1. 將上述程式碼按順序添加到現有的 api.py 檔案中
2. 重新啟動 API 服務器
3. 新的端點將自動可用，不會影響現有功能

📋 測試範例：
- GET https://law-controller-4a92b3cfcb5d.herokuapp.com/api/cases/113001/detail
- GET https://law-controller-4a92b3cfcb5d.herokuapp.com/api/cases/search/detail
- GET http://localhost:8000/api/cases/113001/progress-history
- GET http://localhost:8000/api/cases/fields/division/values
"""