#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
統一路由控制層
管理所有路由的載入、註冊和監控
"""

import os
import sys
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime

# 確保路徑設定
current_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(api_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from api.logic.route_manager import RouteManagerLogic, setup_routes_with_retry
    ROUTE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 無法導入路由管理邏輯: {e}")
    ROUTE_MANAGER_AVAILABLE = False


class UnifiedRouteController:
    """統一路由控制器"""

    def __init__(self, app: FastAPI, database_url: str = None):
        self.app = app
        self.database_url = database_url
        self.route_manager = None
        self.initialization_time = datetime.now()
        self.routes_status: Dict[str, Any] = {}

        # 初始化路由管理器
        if ROUTE_MANAGER_AVAILABLE:
            self.route_manager = RouteManagerLogic()

        # 記錄初始化資訊
        self._log_initialization()

    def _log_initialization(self):
        """記錄初始化資訊"""
        print("=" * 50)
        print("🎛️ 統一路由控制器初始化")
        print(f"📍 專案根目錄: {project_root}")
        print(f"🔗 資料庫: {'已設定' if self.database_url else '未設定'}")
        print(f"🧰 路由管理器: {'可用' if ROUTE_MANAGER_AVAILABLE else '不可用'}")
        print("=" * 50)

    def initialize_all_routes(self) -> Dict[str, Any]:
        """
        初始化所有路由

        Returns:
            Dict: 初始化結果
        """
        if not ROUTE_MANAGER_AVAILABLE:
            return self._manual_route_loading()

        try:
            print("🚀 使用進階路由管理器載入路由...")
            self.routes_status = setup_routes_with_retry(self.app, self.database_url)
            return self.routes_status

        except Exception as e:
            print(f"❌ 進階路由管理器失敗: {e}")
            print("🔄 切換到手動路由載入...")
            return self._manual_route_loading()

    def _manual_route_loading(self) -> Dict[str, Any]:
        """
        手動路由載入（備用方案）

        Returns:
            Dict: 載入結果
        """
        print("🔧 執行手動路由載入...")

        loaded_routes = {}
        route_errors = {}

        # 定義要載入的路由
        routes_config = [
            {
                "name": "webhook",
                "module": "api.routes.webhook_routes",
                "prefix": "/webhook",
                "tags": ["Webhook"],
                "require_db": False
            },
            {
                "name": "health",
                "module": "api.routes.health_routes",
                "prefix": "",
                "tags": ["健康檢查"],
                "require_db": False
            }
        ]

        # 需要資料庫的路由
        if self.database_url:
            db_routes = [
                {
                    "name": "case_upload",
                    "module": "api.routes.case_upload_routes",
                    "prefix": "",
                    "tags": ["案件管理"],
                    "require_db": True
                },
                {
                    "name": "auth",
                    "module": "api.routes.auth_routes",
                    "prefix": "/api/auth",
                    "tags": ["認證系統"],
                    "require_db": True
                }
            ]
            routes_config.extend(db_routes)

        # 逐一載入路由
        for config in routes_config:
            if config.get("require_db", False) and not self.database_url:
                loaded_routes[config["name"]] = False
                route_errors[config["name"]] = "需要資料庫但未設定"
                print(f"⚠️ 跳過 {config['name']} 路由（需要資料庫）")
                continue

            success, error = self._load_single_route(config)
            loaded_routes[config["name"]] = success
            if error:
                route_errors[config["name"]] = error

        self.routes_status = {
            "timestamp": datetime.now().isoformat(),
            "loaded_routes": loaded_routes,
            "route_errors": route_errors,
            "total_loaded": sum(loaded_routes.values()),
            "total_attempted": len(loaded_routes),
            "loading_method": "manual"
        }

        return self.routes_status

    def _load_single_route(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        載入單一路由

        Args:
            config: 路由配置

        Returns:
            tuple: (成功與否, 錯誤訊息)
        """
        route_name = config["name"]
        module_path = config["module"]

        print(f"🔄 載入 {route_name} 路由...")

        try:
            # 嘗試導入模組
            import importlib
            module = importlib.import_module(module_path)
            router = getattr(module, "router")

            # 註冊路由
            self.app.include_router(
                router,
                prefix=config.get("prefix", ""),
                tags=config.get("tags", [])
            )

            print(f"✅ {route_name} 路由載入成功")
            return True, None

        except ImportError as e:
            error_msg = f"模組導入失敗: {e}"
            print(f"❌ {route_name} 路由載入失敗: {error_msg}")
            return False, error_msg

        except AttributeError as e:
            error_msg = f"找不到router屬性: {e}"
            print(f"❌ {route_name} 路由載入失敗: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"未知錯誤: {e}"
            print(f"❌ {route_name} 路由載入失敗: {error_msg}")
            return False, error_msg

    def create_system_endpoints(self):
        """創建系統管理端點"""

        @self.app.get("/api/system/status")
        async def get_system_status():
            """取得系統狀態"""
            return {
                "timestamp": datetime.now().isoformat(),
                "initialization_time": self.initialization_time.isoformat(),
                "database_configured": self.database_url is not None,
                "routes_status": self.routes_status,
                "uptime_seconds": (datetime.now() - self.initialization_time).total_seconds()
            }

        @self.app.get("/api/system/routes")
        async def get_routes_info():
            """取得路由資訊"""
            if self.routes_status:
                return self.routes_status
            else:
                return {
                    "error": "路由狀態尚未初始化",
                    "timestamp": datetime.now().isoformat()
                }

        @self.app.post("/api/system/reload-routes")
        async def reload_routes():
            """重新載入路由（開發用）"""
            try:
                print("🔄 重新載入路由...")
                new_status = self.initialize_all_routes()
                return {
                    "success": True,
                    "message": "路由重載完成",
                    "status": new_status,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        print("✅ 系統管理端點已創建")

    def create_fallback_endpoints(self):
        """創建備用端點"""
        from fastapi import APIRouter

        fallback_router = APIRouter()

        @fallback_router.get("/ping")
        def ping():
            """簡單的ping端點"""
            return {
                "message": "pong",
                "timestamp": datetime.now().isoformat(),
                "status": "alive"
            }

        @fallback_router.get("/info")
        def system_info():
            """系統資訊端點"""
            return {
                "title": "法律案件管理系統 API",
                "version": "3.2.1",
                "status": "running",
                "routes_loaded": self.routes_status.get("total_loaded", 0),
                "database": "configured" if self.database_url else "not_configured",
                "timestamp": datetime.now().isoformat()
            }

        @fallback_router.get("/routes-debug")
        def routes_debug():
            """路由除錯資訊"""
            return {
                "routes_status": self.routes_status,
                "python_path": sys.path[:5],  # 只顯示前5個路徑
                "current_directory": os.getcwd(),
                "project_root": project_root,
                "timestamp": datetime.now().isoformat()
            }

        # 註冊備用路由
        self.app.include_router(fallback_router, prefix="/api/fallback", tags=["備用功能"])
        print("✅ 備用端點已創建")

    def get_loading_summary(self) -> str:
        """取得載入摘要"""
        if not self.routes_status:
            return "路由尚未初始化"

        total_loaded = self.routes_status.get("total_loaded", 0)
        total_attempted = self.routes_status.get("total_attempted", 0)

        if total_attempted == 0:
            return "沒有嘗試載入任何路由"

        success_rate = (total_loaded / total_attempted) * 100

        summary = f"路由載入完成: {total_loaded}/{total_attempted} ({success_rate:.1f}%)"

        if total_loaded == total_attempted:
            summary += " ✅ 全部成功"
        elif total_loaded > 0:
            summary += " ⚠️ 部分成功"
        else:
            summary += " ❌ 全部失敗"

        return summary


def create_and_setup_routes(app: FastAPI, database_url: str = None) -> UnifiedRouteController:
    """
    創建並設定統一路由控制器

    Args:
        app: FastAPI應用程式實例
        database_url: 資料庫URL

    Returns:
        UnifiedRouteController: 路由控制器實例
    """
    # 創建控制器
    controller = UnifiedRouteController(app, database_url)

    # 初始化路由
    print("🚀 開始初始化路由系統...")
    controller.initialize_all_routes()

    # 創建系統端點
    controller.create_system_endpoints()

    # 創建備用端點
    controller.create_fallback_endpoints()

    # 顯示載入摘要
    print("\n" + "=" * 60)
    print("📊 路由載入摘要:")
    print(controller.get_loading_summary())

    if controller.routes_status.get("route_errors"):
        print("\n❌ 載入失敗的路由:")
        for route_name, error in controller.routes_status["route_errors"].items():
            print(f"   • {route_name}: {error}")

    print("=" * 60 + "\n")

    return controller


# 簡化的工廠函數
def quick_setup_routes(app: FastAPI, database_url: str = None) -> Dict[str, Any]:
    """
    快速設定路由（簡化版本）

    Args:
        app: FastAPI應用程式實例
        database_url: 資料庫URL

    Returns:
        Dict: 載入狀態
    """
    controller = create_and_setup_routes(app, database_url)
    return controller.routes_status