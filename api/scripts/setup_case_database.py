#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_case_database.py (修正版)
建立案件資料庫表格的腳本 - 修正模組導入問題
"""

import os
import sys
from datetime import datetime



def setup_case_database():
    """建立案件資料庫表格"""
    try:
        print("🚀 開始建立案件資料庫表格...")
        DATABASE_URL = "postgresql://uekiogttp3k83o:p185ab9eb7a3e51077a51d9cba099beefce0c5351ed9d3d3f073f6b573c406fdc@cer3tutrbi7n1t.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/debg6ra63vhnin"
        os.environ["DATABASE_URL"] = DATABASE_URL
        print("✅ 資料庫URL已設定")

        # 設定Python路徑
        current_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.join(current_dir, 'api')
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)

        print(f"✅ Python路徑設定完成: {current_dir}")

        # 導入必要套件
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker, declarative_base
            from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Index
            print("✅ SQLAlchemy 套件導入成功")
        except ImportError as e:
            print(f"❌ SQLAlchemy 導入失敗: {e}")
            print("請執行: pip install sqlalchemy psycopg2-binary")
            return False

        # 建立 Base
        Base = declarative_base()

        # 🔥 直接在這裡定義模型（避免模組導入問題）
        class CaseRecord(Base):
            """案件記錄資料表"""
            __tablename__ = "case_records"

            # 主鍵
            id = Column(Integer, primary_key=True, index=True, autoincrement=True)

            # 案件基本資訊
            case_id = Column(String(50), nullable=False, index=True, comment="案件編號")
            case_type = Column(String(20), nullable=False, index=True, comment="案件類型")
            client = Column(String(100), nullable=False, index=True, comment="當事人姓名")
            lawyer = Column(String(100), nullable=True, index=True, comment="委任律師")
            legal_affairs = Column(String(100), nullable=True, comment="法務人員")

            # 案件詳細資訊
            progress = Column(String(50), nullable=False, index=True, comment="當前進度")
            case_reason = Column(Text, nullable=True, comment="案由")
            case_number = Column(String(100), nullable=True, index=True, comment="案號")
            opposing_party = Column(String(200), nullable=True, comment="對造")
            court = Column(String(100), nullable=True, index=True, comment="負責法院")
            division = Column(String(50), nullable=True, comment="負責股別")
            progress_date = Column(String(20), nullable=True, comment="進度日期")

            # JSON 欄位儲存複雜資料
            progress_stages = Column(JSON, nullable=True, comment="進度階段記錄")
            progress_notes = Column(JSON, nullable=True, comment="進度備註")
            progress_times = Column(JSON, nullable=True, comment="進度時間")

            # 系統資訊
            client_id = Column(String(50), nullable=False, index=True, comment="事務所ID")
            client_name = Column(String(200), nullable=False, comment="事務所名稱")
            uploaded_by = Column(String(100), nullable=False, comment="上傳者")

            # 時間戳記
            created_date = Column(DateTime, nullable=True, comment="原始建立日期")
            updated_date = Column(DateTime, nullable=True, comment="原始更新日期")
            upload_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="上傳時間")
            last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="最後修改時間")

            # 狀態欄位
            is_active = Column(Boolean, default=True, nullable=False, comment="是否啟用")
            is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已刪除")

            # 建立索引
            __table_args__ = (
                Index('idx_client_case', 'client_id', 'case_id'),
                Index('idx_client_type', 'client_id', 'case_type'),
                Index('idx_client_lawyer', 'client_id', 'lawyer'),
                Index('idx_upload_time', 'upload_time'),
                Index('idx_progress', 'progress'),
            )

        class UploadLog(Base):
            """上傳日誌資料表"""
            __tablename__ = "upload_logs"

            id = Column(Integer, primary_key=True, index=True)
            client_id = Column(String(50), nullable=False, index=True, comment="事務所ID")
            client_name = Column(String(200), nullable=False, comment="事務所名稱")
            upload_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="上傳時間")
            total_cases = Column(Integer, nullable=False, comment="總案件數")
            success_count = Column(Integer, nullable=False, comment="成功數量")
            failed_count = Column(Integer, nullable=False, comment="失敗數量")
            success_rate = Column(String(10), nullable=True, comment="成功率")
            upload_status = Column(String(20), default="completed", comment="上傳狀態")
            error_details = Column(JSON, nullable=True, comment="錯誤詳情")

            # 建立索引
            __table_args__ = (
                Index('idx_client_upload_time', 'client_id', 'upload_time'),
            )

        # 建立引擎
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        engine = create_engine(DATABASE_URL, echo=True)
        print("✅ 資料庫引擎建立成功")

        # 建立所有表格
        print("📋 開始建立表格...")
        Base.metadata.create_all(bind=engine)

        print("✅ 案件資料庫表格建立完成！")

        # 驗證表格是否建立成功
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # 測試查詢
            result = db.execute(text("SELECT COUNT(*) FROM case_records"))
            count = result.scalar()
            print(f"📊 case_records 表格驗證成功，目前有 {count} 筆記錄")

            result = db.execute(text("SELECT COUNT(*) FROM upload_logs"))
            count = result.scalar()
            print(f"📊 upload_logs 表格驗證成功，目前有 {count} 筆記錄")

        except Exception as e:
            print(f"⚠️ 表格驗證時發生錯誤: {e}")
        finally:
            db.close()

        print("\n🎉 案件資料庫設定完成！")
        print("\n📋 已建立的表格：")
        print("  • case_records - 案件記錄表")
        print("  • upload_logs - 上傳日誌表")

        print("\n🔧 接下來需要：")
        print("  1. 在 API 中新增案件上傳路由")
        print("  2. 修改客戶端上傳器的 API 端點")
        print("  3. 測試上傳功能")

        return True

    except ImportError as e:
        print(f"❌ 導入套件失敗: {e}")
        print("💡 請先安裝必要的套件：")
        print("   pip install sqlalchemy psycopg2-binary")
        return False

    except Exception as e:
        print(f"❌ 建立資料庫失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def add_sample_data():
    """新增範例資料（可選）"""
    try:
        print("\n🔧 新增測試資料...")

        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            DATABASE_URL = "postgresql://uekiogttp3k83o:p185ab9eb7a3e51077a51d9cba099beefce0c5351ed9d3d3f073f6b573c406fdc@cer3tutrbi7n1t.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/debg6ra63vhnin"
            os.environ["DATABASE_URL"] = DATABASE_URL

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 直接使用SQL插入測試資料
        sample_sql = """
        INSERT INTO case_records (
            case_id, case_type, client, lawyer, progress, case_reason,
            client_id, client_name, uploaded_by, created_date, updated_date
        ) VALUES
        ('TEST001', '民事', '測試當事人A', '測試律師', '起訴', '測試案由',
         'test_client_001', '測試法律事務所', 'test_user', NOW(), NOW()),
        ('TEST002', '刑事', '測試當事人B', '測試律師', '偵查', '測試刑事案由',
         'test_client_001', '測試法律事務所', 'test_user', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING;
        """

        from sqlalchemy import text
        db.execute(text(sample_sql))
        db.commit()
        print(f"✅ 已新增測試資料")

        db.close()
        return True

    except Exception as e:
        print(f"❌ 新增測試資料失敗: {e}")
        return False

def show_database_info():
    """顯示資料庫資訊"""
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            DATABASE_URL = "postgresql://uekiogttp3k83o:p185ab9eb7a3e51077a51d9cba099beefce0c5351ed9d3d3f073f6b573c406fdc@cer3tutrbi7n1t.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/debg6ra63vhnin"
            os.environ["DATABASE_URL"] = DATABASE_URL

        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        print("\n📊 資料庫統計資訊：")

        # 查詢案件記錄數量
        try:
            result = db.execute(text("SELECT COUNT(*) FROM case_records"))
            case_count = result.scalar()
            print(f"  • 案件記錄總數: {case_count}")

            # 按類型統計
            result = db.execute(text("SELECT case_type, COUNT(*) FROM case_records WHERE is_deleted = false GROUP BY case_type"))
            type_stats = result.fetchall()
            for case_type, count in type_stats:
                print(f"    - {case_type}: {count} 筆")

            # 按事務所統計
            result = db.execute(text("SELECT client_name, COUNT(*) FROM case_records WHERE is_deleted = false GROUP BY client_name"))
            client_stats = result.fetchall()
            for client_name, count in client_stats:
                print(f"    - {client_name}: {count} 筆")

        except Exception as e:
            print(f"  ⚠️ 查詢案件統計失敗: {e}")

        # 查詢上傳日誌數量
        try:
            result = db.execute(text("SELECT COUNT(*) FROM upload_logs"))
            log_count = result.scalar()
            print(f"  • 上傳日誌總數: {log_count}")

        except Exception as e:
            print(f"  ⚠️ 查詢上傳日誌失敗: {e}")

        db.close()

    except Exception as e:
        print(f"❌ 查詢資料庫資訊失敗: {e}")

if __name__ == "__main__":
    """主程式入口"""
    print("🗄️  案件資料庫設定工具 (修正版)")
    print("=" * 50)

    print("請選擇操作:")
    print("1. 建立案件資料庫表格")
    print("2. 新增測試資料")
    print("3. 顯示資料庫資訊")
    print("4. 退出")

    while True:
        try:
            choice = input("\n請選擇 (1-4): ").strip()

            if choice == "1":
                setup_case_database()
                break
            elif choice == "2":
                add_sample_data()
                break
            elif choice == "3":
                show_database_info()
                break
            elif choice == "4":
                print("👋 再見！")
                break
            else:
                print("❌ 請輸入 1-4 的數字")

        except KeyboardInterrupt:
            print("\n👋 程式已中斷")
            break
        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
            break