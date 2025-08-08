# -*- coding: utf-8 -*-
"""
api/routes/case_upload_routes.py
案件上傳 API 路由 - 處理客戶端案件資料上傳
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

# 導入資料庫相關
try:
    from api.database import get_control_db
    from api.models_cases import CaseRecord, UploadLog
    from api.models_control import LoginUser  # 用於驗證客戶端
except ImportError as e:
    print(f"⚠️ 導入資料庫模組失敗: {e}")
    # 提供備用導入
    pass

router = APIRouter()

# ==================== Pydantic 模型 ====================

class CaseUploadRequest(BaseModel):
    """案件上傳請求模型"""
    case_data: Dict[str, Any] = Field(..., description="案件資料")
    client_info: Dict[str, str] = Field(..., description="客戶端資訊")

class CaseUploadResponse(BaseModel):
    """案件上傳回應模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="回應訊息")
    case_id: Optional[str] = Field(None, description="案件編號")
    upload_id: Optional[int] = Field(None, description="上傳記錄ID")

class BatchUploadRequest(BaseModel):
    """批次上傳請求模型"""
    cases: List[Dict[str, Any]] = Field(..., description="案件資料列表")
    client_info: Dict[str, str] = Field(..., description="客戶端資訊")

class BatchUploadResponse(BaseModel):
    """批次上傳回應模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="回應訊息")
    total_cases: int = Field(..., description="總案件數")
    success_count: int = Field(..., description="成功數量")
    failed_count: int = Field(..., description="失敗數量")
    success_rate: float = Field(..., description="成功率")
    failed_cases: List[str] = Field(..., description="失敗的案件編號")

# ==================== API 端點 ====================

@router.post("/api/cases/upload", response_model=CaseUploadResponse)
def upload_single_case(
    request: CaseUploadRequest,
    db: Session = Depends(get_control_db)
):
    """
    上傳單個案件資料

    Args:
        request: 案件上傳請求
        db: 資料庫會話

    Returns:
        CaseUploadResponse: 上傳結果
    """
    try:
        print(f"🔍 收到案件上傳請求: {request.case_data.get('case_id')}")

        # 驗證客戶端資訊
        client_id = request.client_info.get('client_id')
        if not client_id:
            raise HTTPException(status_code=400, detail="缺少客戶端ID")

        # 檢查客戶端是否存在
        client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=401, detail="客戶端不存在或未授權")

        # 檢查案件是否已存在
        existing_case = db.query(CaseRecord).filter(
            CaseRecord.client_id == client_id,
            CaseRecord.case_id == request.case_data.get('case_id'),
            CaseRecord.is_deleted == False
        ).first()

        if existing_case:
            # 更新現有案件
            case_record = _update_case_record(existing_case, request.case_data, request.client_info)
            action = "更新"
        else:
            # 建立新案件記錄
            case_record = CaseRecord.from_case_data(request.case_data, request.client_info)
            db.add(case_record)
            action = "新增"

        db.commit()

        print(f"✅ 案件{action}成功: {case_record.case_id}")

        return CaseUploadResponse(
            success=True,
            message=f"案件{action}成功",
            case_id=case_record.case_id,
            upload_id=case_record.id
        )

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        print(f"❌ 資料庫完整性錯誤: {e}")
        raise HTTPException(status_code=400, detail="資料重複或格式錯誤")
    except Exception as e:
        db.rollback()
        print(f"❌ 上傳案件失敗: {e}")
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")

@router.post("/api/cases/batch-upload", response_model=BatchUploadResponse)
def upload_batch_cases(
    request: BatchUploadRequest,
    db: Session = Depends(get_control_db)
):
    """
    批次上傳案件資料

    Args:
        request: 批次上傳請求
        db: 資料庫會話

    Returns:
        BatchUploadResponse: 批次上傳結果
    """
    try:
        print(f"🚀 收到批次上傳請求: {len(request.cases)} 筆案件")

        # 驗證客戶端資訊
        client_id = request.client_info.get('client_id')
        if not client_id:
            raise HTTPException(status_code=400, detail="缺少客戶端ID")

        # 檢查客戶端是否存在
        client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=401, detail="客戶端不存在或未授權")

        total_cases = len(request.cases)
        success_count = 0
        failed_count = 0
        failed_cases = []

        # 記錄上傳開始
        upload_log = UploadLog(
            client_id=client_id,
            client_name=request.client_info.get('client_name', ''),
            total_cases=total_cases,
            success_count=0,
            failed_count=0,
            upload_status="processing"
        )
        db.add(upload_log)
        db.commit()  # 先提交日誌記錄

        # 逐筆處理案件
        for case_data in request.cases:
            try:
                case_id = case_data.get('case_id')

                # 檢查案件是否已存在
                existing_case = db.query(CaseRecord).filter(
                    CaseRecord.client_id == client_id,
                    CaseRecord.case_id == case_id,
                    CaseRecord.is_deleted == False
                ).first()

                if existing_case:
                    # 更新現有案件
                    _update_case_record(existing_case, case_data, request.client_info)
                else:
                    # 建立新案件記錄
                    case_record = CaseRecord.from_case_data(case_data, request.client_info)
                    db.add(case_record)

                success_count += 1
                print(f"✅ 案件處理成功: {case_id}")

            except Exception as e:
                failed_count += 1
                failed_cases.append(case_id or "未知")
                print(f"❌ 案件處理失敗: {case_id} - {e}")
                continue

        # 計算成功率
        success_rate = (success_count / total_cases * 100) if total_cases > 0 else 0

        # 更新上傳日誌
        upload_log.success_count = success_count
        upload_log.failed_count = failed_count
        upload_log.success_rate = f"{success_rate:.1f}%"
        upload_log.upload_status = "completed"
        if failed_cases:
            upload_log.error_details = {"failed_cases": failed_cases}

        db.commit()

        print(f"📊 批次上傳完成: 成功 {success_count}, 失敗 {failed_count}")

        return BatchUploadResponse(
            success=failed_count == 0,
            message=f"批次上傳完成: 成功 {success_count} 筆, 失敗 {failed_count} 筆",
            total_cases=total_cases,
            success_count=success_count,
            failed_count=failed_count,
            success_rate=success_rate,
            failed_cases=failed_cases
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ 批次上傳失敗: {e}")
        raise HTTPException(status_code=500, detail=f"批次上傳失敗: {str(e)}")

@router.get("/api/cases/list/{client_id}")
def get_client_cases(
    client_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_control_db)
):
    """
    取得客戶端的案件列表

    Args:
        client_id: 客戶端ID
        skip: 跳過數量
        limit: 限制數量
        db: 資料庫會話

    Returns:
        案件列表
    """
    try:
        # 驗證客戶端
        client = db.query(LoginUser).filter(LoginUser.client_id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="客戶端不存在")

        # 查詢案件
        cases = db.query(CaseRecord).filter(
            CaseRecord.client_id == client_id,
            CaseRecord.is_deleted == False
        ).offset(skip).limit(limit).all()

        return {
            "success": True,
            "total_count": len(cases),
            "cases": [case.to_dict() for case in cases]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢案件失敗: {e}")
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

@router.get("/api/cases/upload-logs/{client_id}")
def get_upload_logs(
    client_id: str,
    limit: int = 20,
    db: Session = Depends(get_control_db)
):
    """
    取得上傳日誌

    Args:
        client_id: 客戶端ID
        limit: 限制數量
        db: 資料庫會話

    Returns:
        上傳日誌列表
    """
    try:
        logs = db.query(UploadLog).filter(
            UploadLog.client_id == client_id
        ).order_by(UploadLog.upload_time.desc()).limit(limit).all()

        return {
            "success": True,
            "logs": [log.to_dict() for log in logs]
        }

    except Exception as e:
        print(f"❌ 查詢上傳日誌失敗: {e}")
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

# ==================== 輔助函數 ====================

def _update_case_record(existing_case: CaseRecord, case_data: Dict[str, Any], client_info: Dict[str, str]):
    """更新現有案件記錄"""
    existing_case.case_type = case_data.get('case_type', existing_case.case_type)
    existing_case.client = case_data.get('client', existing_case.client)
    existing_case.lawyer = case_data.get('lawyer', existing_case.lawyer)
    existing_case.legal_affairs = case_data.get('legal_affairs', existing_case.legal_affairs)
    existing_case.progress = case_data.get('progress', existing_case.progress)
    existing_case.case_reason = case_data.get('case_reason', existing_case.case_reason)
    existing_case.case_number = case_data.get('case_number', existing_case.case_number)
    existing_case.opposing_party = case_data.get('opposing_party', existing_case.opposing_party)
    existing_case.court = case_data.get('court', existing_case.court)
    existing_case.division = case_data.get('division', existing_case.division)
    existing_case.progress_date = case_data.get('progress_date', existing_case.progress_date)
    existing_case.progress_stages = case_data.get('progress_stages', existing_case.progress_stages)
    existing_case.progress_notes = case_data.get('progress_notes', existing_case.progress_notes)
    existing_case.progress_times = case_data.get('progress_times', existing_case.progress_times)
    existing_case.last_modified = datetime.utcnow()

    return existing_case