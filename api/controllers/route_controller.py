#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一路由控制層
管理所有路由的載入、註冊和監控（精簡修正版）
- 僅載入仍存在的路由：case_upload、api_routes（/api/auth）
- 提供 api_routes 檔名含空白 "api_routes .py" 的 fallback
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI
from importlib import util as importlib_util
from pathlib import Path

# 盡力載入進階路由管理器（可選）
try:
    from api.logic.route_manager import RouteManagerLogic, setup_routes_with_retry
    ROUTE_MANAGER_AVAILABLE = False
except Exception:
    ROUTE_MANAGER_AVAILABLE = False

# 確保 import 路徑
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class RouteController:
    """統一路由控制器"""

    def __init__(self, app: FastAPI, database_url: Optional[str] = None) -> None:
        self.app = app
        self.database_url = database_url
        self.initialization_time = datetime.now()
        self.routes_status: Dict[str, Any] = {}

        print("=" * 50)
        print("🎛️ 統一路由控制器初始化")
        print(f"📍 專案根目錄: {PROJECT_ROOT}")
        print(f"🔗 資料庫: {'已設定' if self.database_url else '未設定'}")
        print(f"🧰 路由管理器: {'可用' if ROUTE_MANAGER_AVAILABLE else '不可用'}")
        print("=" * 50)

    # ----------------------------
    # Public API
    # ----------------------------
    def initialize_all_routes(self) -> Dict[str, Any]:
        """初始化所有路由"""
        if ROUTE_MANAGER_AVAILABLE:
            try:
                print("🚀 使用進階路由管理器載入路由...")
                self.routes_status = setup_routes_with_retry(self.app, self.database_url)
                return self.routes_status
            except Exception as e:
                print(f"⚠️ 進階路由管理器失敗，改用手動模式: {e}")

        # 備用：手動路由載入
        self.routes_status = self._manual_route_loading()
        return self.routes_status

    def create_system_endpoints(self) -> None:
        """建立系統監控端點"""

        @self.app.get("/api/system/status")
        async def get_system_status() -> Dict[str, Any]:
            """取得系統狀態"""
            return {
                "timestamp": datetime.now().isoformat(),
                "initialization_time": self.initialization_time.isoformat(),
                "database_configured": bool(self.database_url),
                "routes_status": self.routes_status,
                "uptime_seconds": (datetime.now() - self.initialization_time).total_seconds(),
            }

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _manual_route_loading(self) -> Dict[str, Any]:
        """手動路由載入（精簡，只載入仍存在的路由）"""
        print("🔧 執行手動路由載入...")

        loaded_routes: Dict[str, bool] = {}
        route_errors: Dict[str, str] = {}

        routes_config: list[Dict[str, Any]] = []

        # 僅在 DB 已設定時載入需要資料庫的路由
        if self.database_url:
            routes_config.extend([
                {
                    "name": "case_upload",
                    "module": "api.routes.case_upload_routes",
                    "prefix": "",
                    "tags": ["案件管理"],
                    "require_db": True
                },
                {
                    "name": "auth",
                    "module": "api.routes.api_routes",  # 改為 api_routes
                    "prefix": "/api/auth",
                    "tags": ["認證系統"],
                    "require_db": True
                },
            ])
        else:
            print("⚠️ 未設定資料庫，跳過需 DB 的路由載入")

        # 逐一載入
        for config in routes_config:
            if config.get("require_db") and not self.database_url:
                loaded_routes[config["name"]] = False
                route_errors[config["name"]] = "需要資料庫但未設定"
                print(f"⚠️ 跳過 {config['name']}（需要資料庫）")
                continue

            success, error = self._load_single_route(config)
            loaded_routes[config["name"]] = success
            if not success and error:
                route_errors[config["name"]] = error

        status: Dict[str, Any] = {
            "routes": loaded_routes,
            "errors": route_errors,
            "total_loaded": sum(1 for v in loaded_routes.values() if v),
            "total_attempted": len(routes_config),
            "loading_method": "manual",
        }
        print(f"✅ 手動路由載入完成：{status}")
        return status

    def _load_single_route(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """載入單一路由"""
        route_name: str = config["name"]
        module_path: str = config["module"]
        prefix: str = config.get("prefix", "")
        tags = config.get("tags", None)

        print(f"🔄 載入 {route_name} 路由...")

        try:
            router = None

            if module_path == "api.routes.api_routes":
                # 先嘗試正常 import
                try:
                    module = __import__(module_path, fromlist=["router"])
                    router = getattr(module, "router", None)
                except Exception:
                    # fallback：嘗試載入檔名含空白的 "api_routes .py"
                    routes_dir = Path(__file__).parent.parent / "routes"
                    weird = routes_dir / "api_routes .py"  # 注意檔名有空白
                    if weird.exists():
                        spec = importlib_util.spec_from_file_location("api_routes_fallback", str(weird))
                        m = importlib_util.module_from_spec(spec)
                        assert spec and spec.loader
                        spec.loader.exec_module(m)
                        router = getattr(m, "router", None)

            else:
                module = __import__(module_path, fromlist=["router"])
                router = getattr(module, "router", None)

            if router is None:
                raise RuntimeError(f"{module_path} 未找到 'router'")

            # 註冊進 FastAPI
            if tags is not None:
                self.app.include_router(router, prefix=prefix, tags=tags)
            else:
                self.app.include_router(router, prefix=prefix)

            print(f"✅ {route_name} 載入完成")
            return True, None

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            print(f"❌ {route_name} 路由載入失敗: {error_msg}")
            return False, error_msg


def setup_unified_routes(app: FastAPI, database_url: Optional[str]) -> Dict[str, Any]:
    """工廠方法：建立控制器並初始化路由，回傳狀態"""
    controller = RouteController(app, database_url)
    status = controller.initialize_all_routes()
    controller.create_system_endpoints()
    return status
