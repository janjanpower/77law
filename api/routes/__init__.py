#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Routes 模組
統一管理所有API路由
"""

# 匯出
__all__ = [
    "available_routers",
]

# 路由註冊函數
def register_routes(app):
    """
    註冊所有可用的路由到FastAPI應用程式

    Args:
        app: FastAPI應用程式實例
    """
    registered_count = 0

    for route_name, router, prefix in available_routers:
        try:
            # 決定標籤
            tags = [route_name.title()]

            # 註冊路由
            app.include_router(router, prefix=prefix, tags=tags)
            print(f"✅ 路由註冊成功: {route_name} ({prefix})")
            registered_count += 1

        except Exception as e:
            print(f"❌ 路由註冊失敗: {route_name} - {e}")

    print(f"📋 總計註冊 {registered_count} 個路由模組")
    return registered_count

