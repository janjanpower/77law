#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
健康檢查路由模組
提供系統狀態檢查和監控功能
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import sys
import os

# 添加專案根目錄到路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 嘗試導入psutil用於系統監控
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# 導入schemas
from api.schemas.line_schemas import SystemStatusResponse

# 導入控制器檢查
try:
    from controllers.case_controller import CaseController
    CONTROLLER_AVAILABLE = True
except ImportError:
    CONTROLLER_AVAILABLE = False

# 建立路由器
router = APIRouter()

# 全域變數
controller = None
user_conversations = {}  # 引用自其他模組的對話狀態

def get_controller():
    """取得控制器實例"""
    global controller
    if controller is None and CONTROLLER_AVAILABLE:
        try:
            controller = CaseController()
        except Exception as e:
            print(f"❌ 健康檢查：控制器初始化失敗 - {e}")
    return controller

def check_module_availability():
    """檢查各模組可用性"""
    modules_status = {}

    # 檢查控制器
    modules_status['case_controller'] = CONTROLLER_AVAILABLE

    # 檢查模型
    try:
        from models.case_model import CaseData
        modules_status['case_model'] = True
    except ImportError:
        modules_status['case_model'] = False

    # 檢查工具模組
    try:
        from utils.folder_management import FolderManager
        modules_status['folder_management'] = True
    except ImportError:
        modules_status['folder_management'] = False

    # 檢查邏輯層
    try:
        from api.logic.webhook_logic import WebhookLogic
        modules_status['webhook_logic'] = True
    except ImportError:
        modules_status['webhook_logic'] = False

    return modules_status

def get_system_info():
    """取得系統資源資訊"""
    try:
        # 基本系統資訊
        info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": os.cpu_count()
        }

        # 如果psutil可用，添加更多資訊
        if PSUTIL_AVAILABLE:
            try:
                info.update({
                    "memory_usage": psutil.virtual_memory().percent,
                    "cpu_usage": psutil.cpu_percent(interval=1),
                    "disk_usage": psutil.disk_usage('/').percent
                })
            except Exception as e:
                info["psutil_error"] = str(e)
        else:
            info["note"] = "psutil不可用，系統監控功能受限"

        return info
    except Exception as e:
        return {"error": str(e)}

# ==================== 健康檢查端點 ====================

@router.get("/health", response_model=SystemStatusResponse)
async def health_check():
    """基本健康檢查端點"""
    try:
        # 檢查控制器
        ctrl = get_controller()
        total_cases = 0

        if ctrl:
            try:
                cases = ctrl.get_cases()
                total_cases = len(cases)
            except Exception as e:
                print(f"⚠️ 取得案件數量失敗: {e}")

        # 檢查模組狀態
        modules_status = check_module_availability()

        # 計算活躍對話數 (如果可以存取)
        active_conversations = len(user_conversations)

        # 系統功能列表
        features = ["對話查詢", "案件詳細資料", "進度管理", "統計分析"]
        if modules_status.get('webhook_logic', False):
            features.append("智慧對話")

        response = SystemStatusResponse(
            status="healthy" if CONTROLLER_AVAILABLE else "degraded",
            total_cases=total_cases,
            active_conversations=active_conversations,
            features=features,
            modules_status=modules_status
        )

        return response

    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
        return SystemStatusResponse(
            status="error",
            total_cases=0,
            active_conversations=0,
            features=[],
            modules_status={"error": str(e)}
        )

@router.get("/health/detailed")
async def detailed_health_check():
    """詳細健康檢查端點"""
    try:
        # 基本檢查
        basic_health = await health_check()

        # 詳細系統資訊
        system_info = get_system_info()

        # 控制器詳細檢查
        controller_status = {
            "available": CONTROLLER_AVAILABLE,
            "initialized": controller is not None,
            "data_accessible": False,
            "case_count": 0
        }

        if controller:
            try:
                cases = controller.get_cases()
                controller_status["data_accessible"] = True
                controller_status["case_count"] = len(cases)
            except Exception as e:
                controller_status["error"] = str(e)

        # 資料夾結構檢查
        folder_status = {
            "base_folder_exists": False,
            "case_types_available": [],
            "writable": False
        }

        try:
            if controller:
                # 檢查基礎資料夾
                import os
                from config.settings import AppConfig

                data_folder = os.path.dirname(controller.data_file)
                folder_status["base_folder_exists"] = os.path.exists(data_folder)
                folder_status["writable"] = os.access(data_folder, os.W_OK) if os.path.exists(data_folder) else False

                # 檢查案件類型資料夾
                for case_type, folder_name in AppConfig.CASE_TYPE_FOLDERS.items():
                    case_type_path = os.path.join(data_folder, folder_name)
                    if os.path.exists(case_type_path):
                        folder_status["case_types_available"].append(case_type)
        except Exception as e:
            folder_status["error"] = str(e)

        # API端點檢查
        api_endpoints = {
            "webhook_available": True,  # 如果這個端點能執行，webhook就是可用的
            "case_api_available": True,
            "health_api_available": True
        }

        return {
            "basic_health": basic_health.dict(),
            "system_info": system_info,
            "controller_status": controller_status,
            "folder_status": folder_status,
            "api_endpoints": api_endpoints,
            "timestamp": datetime.now().isoformat(),
            "uptime_check": "API正在運行"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"詳細健康檢查失敗: {str(e)}")

@router.get("/health/quick")
async def quick_health_check():
    """快速健康檢查端點 - 用於監控"""
    try:
        status = "ok"
        issues = []

        # 快速檢查控制器
        if not CONTROLLER_AVAILABLE:
            status = "warning"
            issues.append("控制器模組不可用")

        # 快速檢查案件數據
        case_count = 0
        if controller:
            try:
                cases = controller.get_cases()
                case_count = len(cases)
            except:
                status = "error"
                issues.append("無法存取案件數據")

        return {
            "status": status,
            "case_count": case_count,
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "case_count": 0,
            "issues": [f"健康檢查失敗: {str(e)}"],
            "timestamp": datetime.now().isoformat()
        }

# ==================== 系統資訊端點 ====================

@router.get("/info")
async def system_info():
    """取得系統資訊"""
    try:
        # 模組狀態
        modules = check_module_availability()

        # API版本資訊
        version_info = {
            "api_version": "2.0.0",
            "architecture": "modular",
            "description": "LINE BOT案件管理API系統",
            "features": [
                "模組化架構",
                "LINE Bot整合",
                "案件管理",
                "進度追蹤",
                "統計分析"
            ]
        }

        # 配置資訊 (不包含敏感資料)
        config_info = {
            "environment": "development",  # 或從環境變數讀取
            "debug_mode": True,  # 或從設定讀取
            "api_prefix": "/api"
        }

        return {
            "version": version_info,
            "modules": modules,
            "config": config_info,
            "system": get_system_info(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得系統資訊失敗: {str(e)}")

@router.get("/status")
async def api_status():
    """API狀態端點 - 簡化版健康檢查"""
    return {
        "api": "running",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "webhook": "/webhook/line",
            "cases": "/api/cases",
            "health": "/health"
        }
    }

# ==================== 監控端點 ====================

@router.get("/metrics")
async def get_metrics():
    """取得系統指標 - 用於監控"""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "api_version": "2.0.0",
            "status": "running"
        }

        # 案件相關指標
        if controller:
            try:
                cases = controller.get_cases()
                metrics.update({
                    "total_cases": len(cases),
                    "case_types": len(set(case.case_type for case in cases)),
                    "active_lawyers": len(set(case.lawyer for case in cases if case.lawyer))
                })
            except Exception as e:
                metrics["case_metrics_error"] = str(e)

        # 對話相關指標
        metrics["active_conversations"] = len(user_conversations)

        # 系統資源指標
        if PSUTIL_AVAILABLE:
            try:
                metrics.update({
                    "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                    "cpu_usage_percent": psutil.cpu_percent(interval=0.1)
                })
            except Exception as e:
                metrics["system_metrics_error"] = str(e)
        else:
            metrics["system_metrics"] = "不可用 (psutil未安裝)"

        return metrics

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得指標失敗: {str(e)}")

# ==================== 測試端點 ====================

@router.get("/test/connectivity")
async def test_connectivity():
    """測試連接性"""
    return {
        "api_accessible": True,
        "timestamp": datetime.now().isoformat(),
        "message": "API連接正常"
    }

@router.get("/test/database")
async def test_database_connection():
    """測試資料庫連接 (目前為檔案系統)"""
    try:
        if not controller:
            return {
                "database_accessible": False,
                "error": "控制器不可用",
                "timestamp": datetime.now().isoformat()
            }

        # 嘗試讀取案件數據
        cases = controller.get_cases()

        return {
            "database_accessible": True,
            "case_count": len(cases),
            "timestamp": datetime.now().isoformat(),
            "message": "資料存取正常"
        }

    except Exception as e:
        return {
            "database_accessible": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/test/echo")
async def echo_test(data: dict):
    """回音測試端點"""
    return {
        "echo": data,
        "timestamp": datetime.now().isoformat(),
        "message": "回音測試成功"
    }