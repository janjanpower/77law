#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化資料庫表格
"""

from api.database import Base, engine
from api.models_control import LoginUser, TenantUser

if __name__ == "__main__":
    print("🚀 開始建立資料表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 資料表建立完成")
