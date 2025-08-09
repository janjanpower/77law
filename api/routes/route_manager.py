#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由管理邏輯層
統一管理所有路由的載入、註冊和錯誤處理邏輯
"""

import os
import sys
import importlib
from typing import Dict, Tuple, Optional, Any
from fastapi import APIRouter, FastAPI
from datetime import datetime

class RouteManagerLogic:
    """路由管理邏輯類"""

    def __init__(self):
        self.loaded_routes: Dict[str, bool] = {}
        self.route_errors: Dict[str, str] = {}
        self.project_root = self._get_project_root()
        self._setup_paths()

    def _get_project_root(self) -> str:
        """取得專案根目錄"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 從 api/logic/ 往上兩層到專案根目錄
        return os.path.dirname(os.path.dirname(current_dir))

    def _setup_paths(self):
        """設定Python路徑"""
        paths_to_add = [
            self.project_root,
            os.path.join(self.project_root, "api"),
            os.path.join(self.project_root, "controllers"),
            os.path.join(self.project_root, "models"),
            os.path.join(self.project_root, "utils"),
        ]

        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)

    def safe_import_router(self, module_path: str, router_name: str = "router") -> Tuple[Optional[APIRouter], Optional[str]]:
        """
        安全導入路由器

        Args:
            module_path: 模組路徑
            router_name: 路由器名稱

        Returns:
            Tuple[APIRouter或None, 錯誤訊息或None]
        """
        try:
            # 清除模組快取
            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])

            # 嘗試多種導入方式
            router = None

            # 方式1: 直接導入
            try:
                module = importlib.import_module(module_path)
                router = getattr(module, router_name)
            except (ImportError, AttributeError):
                pass

            # 方式2: 嘗試相對導入
            if not router and module_path.startswith("routes."):
                try:
                    relative_path = f"api.{module_path}"
                    module = importlib.import_module(relative_path)
                    router = getattr(module, router_name)
                except (ImportError, AttributeError):
                    pass

            # 方式3: 嘗試從根目錄導入
            if not router:
                try:
                    full_path = f"api.routes.{module_path.split('.')[-1]}"
                    module = importlib.import_module(full_path)
                    router = getattr(module, router_name)
                except (ImportError, AttributeError):
                    pass

            if router:
                return router, None
            else:
                return None, f"無法找到路由器 '{router_name}' 在模組 '{module_path}'"

        except Exception as e:
            return None, f"導入錯誤: {str(e)}"

    def register_router(self, app: FastAPI, router: APIRouter, prefix: str = "", tags: list = None) -> bool:
        """
        註冊路由器到FastAPI應用程式

        Args:
            app: FastAPI應用程式實例
            router: 要註冊的路由器
            prefix: 路由前綴
            tags: 路由標籤

        Returns:
            bool: 註冊是否成功
        """
        try:
            if tags is None:
                tags = []

            app.include_router(router, prefix=prefix, tags=tags)
            return True
        except Exception as e:
            self.route_errors[f"{prefix}_{tags}"] = str(e)
            return False

    def load_and_register_route(self, app: FastAPI, module_path: str, route_name: str,
                               prefix: str = "", tags: list = None, router_name: str = "router") -> bool:
        """
        載入並註冊單一路由

        Args:
            app: FastAPI應用程式實例
            module_path: 模組路徑
            route_name: 路由名稱（用於記錄）
            prefix: 路由前綴
            tags: 路由標籤
            router_name: 路由器變數名稱

        Returns:
            bool: 是否成功載入並註冊
        """
        print(f"🔄 嘗試載入 {route_name} 路由...")

        router, error = self.safe_import_router(module_path, router_name)

        if router:
            if self.register_router(app, router, prefix, tags or [route_name]):
                self.loaded_routes[route_name] = True
                print(f"✅ {route_name} 路由載入成功")
                return True
            else:
                self.loaded_routes[route_name] = False
                error_msg = self.route_errors.get(f"{prefix}_{tags}", "註冊失敗")
                print(f"❌ {route_name} 路由註冊失敗: {error_msg}")
                return False
        else:
            self.loaded_routes[route_name] = False
            self.route_errors[route_name] = error
            print(f"⚠️ {route_name} 路由載入失敗: {error}")
            return False

    def load_all_routes(self, app: FastAPI, database_url: str = None) -> Dict[str, bool]:
        """
        載入所有路由

        Args:
            app: FastAPI應用程式實例
            database_url: 資料庫URL（某些路由需要資料庫）

        Returns:
            Dict[str, bool]: 各路由的載入狀態
        """
        # # 定義路由配置
        # route_configs = [
        #     {
        #         "module_path": "routes.webhook_routes",
        #         "route_name": "webhook",
        #         "prefix": "/webhook",
        #         "tags": ["Webhook"],
        #         "require_db": False
        #     },
        #     {
        #         "module_path": "routes.health_routes",
        #         "route_name": "health",
        #         "prefix": "",
        #         "tags": ["健康檢查"],
        #         "require_db": False
        #     }
        # ]

        # 需要資料庫的路由
        if database_url:
            db_routes = [
                {
                    "module_path": "routes.case_upload_routes",
                    "route_name": "case_upload",
                    "prefix": "",
                    "tags": ["案件管理"],
                    "require_db": True
                },
                {
                    "module_path": "routes.auth_routes",
                    "route_name": "auth",
                    "prefix": "/api/auth",
                    "tags": ["認證系統"],
                    "require_db": True
                },
                {
                    "module_path": "routes.api_routes",
                    "route_name": "auth_api",
                    "prefix": "/api/auth",
                    "tags": ["認證API"],
                    "require_db": True
                },
                {
                    "module_path": "routes.login_routes",
                    "route_name": "login",
                    "prefix": "/api/login",
                    "tags": ["登入"],
                    "require_db": True
                }
            ]
            route_configs.extend(db_routes)

        # 載入所有路由
        for config in route_configs:
            if config.get("require_db", False) and not database_url:
                print(f"⚠️ 跳過 {config['route_name']} 路由（需要資料庫）")
                self.loaded_routes[config["route_name"]] = False
                continue

            self.load_and_register_route(
                app=app,
                module_path=config["module_path"],
                route_name=config["route_name"],
                prefix=config["prefix"],
                tags=config["tags"]
            )

        return self.loaded_routes

    def get_status(self) -> Dict[str, Any]:
        """取得路由管理狀態"""
        return {
            "timestamp": datetime.now().isoformat(),
            "loaded_routes": self.loaded_routes,
            "route_errors": self.route_errors,
            "total_loaded": sum(self.loaded_routes.values()),
            "total_attempted": len(self.loaded_routes),
            "success_rate": sum(self.loaded_routes.values()) / len(self.loaded_routes) if self.loaded_routes else 0
        }

    def create_status_endpoint(self, app: FastAPI):
        """創建路由狀態檢查端點"""
        @app.get("/api/system/routes")
        async def get_routes_status():
            """取得路由載入狀態"""
            return self.get_status()

    def create_fallback_routes(self, app: FastAPI):
        """創建備用路由（當主要路由載入失敗時）"""
        fallback_router = APIRouter()

        @fallback_router.get("/test")
        def test_endpoint():
            return {
                "message": "備用路由測試端點",
                "timestamp": datetime.now().isoformat(),
                "status": "fallback_active"
            }

        @fallback_router.get("/status")
        def fallback_status():
            return {
                "message": "系統運行中，但部分功能可能不可用",
                "loaded_routes": self.loaded_routes,
                "errors": self.route_errors
            }

        app.include_router(fallback_router, prefix="/api/fallback", tags=["備用功能"])
        print("✅ 備用路由已創建")


class RouterRetryLogic:
    """路由重試邏輯"""

    def __init__(self, route_manager: RouteManagerLogic):
        self.route_manager = route_manager
        self.retry_count = 0
        self.max_retries = 3

    def retry_failed_routes(self, app: FastAPI, database_url: str = None) -> Dict[str, bool]:
        """重試載入失敗的路由"""
        if self.retry_count >= self.max_retries:
            print(f"⚠️ 已達到最大重試次數 ({self.max_retries})")
            return self.route_manager.loaded_routes

        self.retry_count += 1
        print(f"🔄 第 {self.retry_count} 次重試載入失敗的路由...")

        failed_routes = [name for name, loaded in self.route_manager.loaded_routes.items() if not loaded]

        if not failed_routes:
            print("✅ 沒有需要重試的路由")
            return self.route_manager.loaded_routes

        print(f"🎯 重試路由: {', '.join(failed_routes)}")

        # 重新載入失敗的路由
        return self.route_manager.load_all_routes(app, database_url)


# 工廠函數
def create_route_manager() -> RouteManagerLogic:
    """創建路由管理器實例"""
    return RouteManagerLogic()

def setup_routes_with_retry(app: FastAPI, database_url: str = None) -> Dict[str, Any]:
    """
    設定路由並提供重試機制

    Args:
        app: FastAPI應用程式實例
        database_url: 資料庫URL

    Returns:
        Dict: 載入結果和狀態
    """
    route_manager = create_route_manager()
    retry_logic = RouterRetryLogic(route_manager)

    # 第一次載入
    print("🚀 開始載入路由...")
    loaded_routes = route_manager.load_all_routes(app, database_url)

    # 如果有失敗的路由，嘗試重試
    failed_routes = [name for name, loaded in loaded_routes.items() if not loaded]
    if failed_routes:
        print(f"⚠️ 發現 {len(failed_routes)} 個失敗的路由，準備重試...")
        loaded_routes = retry_logic.retry_failed_routes(app, database_url)

    # 創建狀態端點
    route_manager.create_status_endpoint(app)

    # 如果仍有失敗的路由，創建備用路由
    still_failed = [name for name, loaded in loaded_routes.items() if not loaded]
    if still_failed:
        print(f"⚠️ 仍有 {len(still_failed)} 個路由載入失敗，創建備用路由...")
        route_manager.create_fallback_routes(app)

    return route_manager.get_status()