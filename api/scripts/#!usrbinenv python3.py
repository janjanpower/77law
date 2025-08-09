#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建案件資料庫腳本
確保資料庫結構完全匹配本地 case_model.py
"""

import os
import sys
from datetime import datetime

# 資料庫連線設定
DATABASE_URL = "postgresql://uekiogttp3k83o:p185ab9eb7a3e51077a51d9cba099beefce0c5351ed9d3d3f073f6b573c406fdc@cer3tutrbi7n1t.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/debg6ra63vhnin"

def rebuild_database():
    """重建資料庫"""
    try:
        print("🚀 開始重建案件資料庫...")
        print(f"📅 執行時間: {datetime.now()}")

        # 設定環境變數
        os.environ["DATABASE_URL"] = DATABASE_URL

        # 導入必要模組
        from sqlalchemy import create_engine, text, MetaData
        from sqlalchemy.orm import sessionmaker

        # 修正 Heroku PostgreSQL URL 格式
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        # 建立引擎
        engine = create_engine(db_url, echo=True)
        SessionLocal = sessionmaker(bind=engine)

        print("✅ 資料庫連線建立成功")

        # 建立會話
        db = SessionLocal()

        try:
            # 1. 刪除現有表格（如果存在）
            print("\n🗑️ 刪除現有表格...")
            drop_sql = """
            DROP TABLE IF EXISTS case_records CASCADE;
            """
            db.execute(text(drop_sql))
            db.commit()
            print("✅ 現有表格已刪除")

            # 2. 創建新的 case_records 表格 - 完全匹配 case_model.py
            print("\n📋 建立新的 case_records 表格...")
            create_table_sql = """
            CREATE TABLE case_records (
                -- 主鍵
                id SERIAL PRIMARY KEY,

                -- 必要識別欄位
                client_id VARCHAR(50) NOT NULL,
                case_id VARCHAR(100) NOT NULL,

                -- 基本案件資訊（完全匹配 case_model.py）
                case_type VARCHAR(50),        -- 案件類型（刑事/民事）
                client VARCHAR(100),          -- 當事人
                lawyer VARCHAR(100),          -- 委任律師
                legal_affairs VARCHAR(100),   -- 法務
                progress VARCHAR(50) DEFAULT '待處理',  -- 進度追蹤

                -- 詳細資訊欄位
                case_reason TEXT,             -- 案由
                case_number VARCHAR(100),     -- 案號
                opposing_party VARCHAR(100),  -- 對造
                court VARCHAR(100),           -- 負責法院
                division VARCHAR(50),         -- 負責股別
                progress_date VARCHAR(20),    -- 當前進度的日期

                -- JSON 欄位 - 進度追蹤
                progress_stages JSONB DEFAULT '{}',  -- 進度階段記錄 {階段: 日期}
                progress_notes JSONB DEFAULT '{}',   -- 進度階段備註 {階段: 備註}
                progress_times JSONB DEFAULT '{}',   -- 進度階段時間 {階段: 時間}

                -- 時間戳記（匹配 case_model.py）
                created_date TIMESTAMP,      -- 對應 case_model.py 的 created_date
                updated_date TIMESTAMP,      -- 對應 case_model.py 的 updated_date

                -- 建立時間
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """

            db.execute(text(create_table_sql))
            db.commit()
            print("✅ case_records 表格建立成功")

            # 3. 建立索引
            print("\n🔍 建立索引...")
            index_sql = """
            -- 主要查詢索引
            CREATE INDEX idx_case_records_client_id ON case_records(client_id);
            CREATE INDEX idx_case_records_case_id ON case_records(case_id);
            CREATE INDEX idx_case_records_client_case ON case_records(client_id, case_id);

            -- 查詢優化索引
            CREATE INDEX idx_case_records_case_type ON case_records(case_type);
            CREATE INDEX idx_case_records_progress ON case_records(progress);
            CREATE INDEX idx_case_records_lawyer ON case_records(lawyer);
            CREATE INDEX idx_case_records_created_at ON case_records(created_at);

            -- 唯一約束（確保同一事務所內案件編號唯一）
            CREATE UNIQUE INDEX uk_case_records_client_case ON case_records(client_id, case_id);
            """

            for sql in index_sql.strip().split(';'):
                if sql.strip():
                    db.execute(text(sql.strip() + ';'))
            db.commit()
            print("✅ 索引建立成功")

            # 4. 驗證表格結構
            print("\n🔍 驗證表格結構...")
            verify_sql = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'case_records'
            ORDER BY ordinal_position;
            """

            result = db.execute(text(verify_sql))
            columns = result.fetchall()

            print(f"📊 case_records 表格包含 {len(columns)} 個欄位:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"  - {col[0]}: {col[1]} {nullable}{default}")

            # 5. 檢查必要欄位
            expected_fields = [
                'id', 'client_id', 'case_id', 'case_type', 'client', 'lawyer',
                'legal_affairs', 'progress', 'case_reason', 'case_number',
                'opposing_party', 'court', 'division', 'progress_date',
                'progress_stages', 'progress_notes', 'progress_times',
                'created_date', 'updated_date', 'created_at', 'updated_at'
            ]

            actual_fields = [col[0] for col in columns]
            missing_fields = [field for field in expected_fields if field not in actual_fields]

            if missing_fields:
                print(f"⚠️ 缺少欄位: {missing_fields}")
            else:
                print("✅ 所有必要欄位都已建立")

            # 6. 插入測試資料
            print("\n🧪 插入測試資料...")
            test_sql = """
            INSERT INTO case_records (
                client_id, case_id, case_type, client, lawyer, progress,
                case_reason, progress_stages, progress_notes, progress_times,
                created_date, updated_date
            ) VALUES (
                'test_rebuild',
                'REBUILD_TEST_001',
                '測試案件',
                '重建測試當事人',
                '測試律師',
                '待處理',
                '資料庫重建測試',
                '{"待處理": "2025-01-01"}'::jsonb,
                '{"待處理": "系統重建測試"}'::jsonb,
                '{"待處理": "09:00"}'::jsonb,
                NOW(),
                NOW()
            );
            """

            db.execute(text(test_sql))
            db.commit()

            # 驗證測試資料
            count_sql = "SELECT COUNT(*) FROM case_records WHERE client_id = 'test_rebuild';"
            count = db.execute(text(count_sql)).scalar()
            print(f"✅ 測試資料插入成功，共 {count} 筆")

            # 清理測試資料
            cleanup_sql = "DELETE FROM case_records WHERE client_id = 'test_rebuild';"
            db.execute(text(cleanup_sql))
            db.commit()
            print("✅ 測試資料清理完成")

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

        print("\n🎉 資料庫重建完成！")
        print("\n📋 完成的工作:")
        print("  ✅ 刪除舊的 case_records 表格")
        print("  ✅ 建立新的 case_records 表格（匹配 case_model.py）")
        print("  ✅ 建立查詢索引和唯一約束")
        print("  ✅ 驗證表格結構")
        print("  ✅ 測試資料插入和查詢")

        print("\n🔧 接下來請：")
        print("  1. 測試客戶端上傳功能")
        print("  2. 檢查 API 日誌確認無 500 錯誤")
        print("  3. 查詢資料庫確認資料正確寫入")

        return True

    except Exception as e:
        print(f"\n❌ 資料庫重建失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_current_structure():
    """顯示當前資料庫結構"""
    try:
        print("🔍 查詢當前資料庫結構...")

        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # 檢查表格是否存在
        check_table_sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'case_records'
        );
        """

        exists = db.execute(text(check_table_sql)).scalar()

        if exists:
            print("✅ case_records 表格存在")

            # 顯示欄位結構
            structure_sql = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'case_records'
            ORDER BY ordinal_position;
            """

            result = db.execute(text(structure_sql))
            columns = result.fetchall()

            print(f"\n📊 當前表格結構 ({len(columns)} 個欄位):")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"  - {col[0]}: {col[1]} {nullable}{default}")

            # 顯示記錄數量
            count_sql = "SELECT COUNT(*) FROM case_records;"
            count = db.execute(text(count_sql)).scalar()
            print(f"\n📈 目前記錄數量: {count} 筆")

        else:
            print("❌ case_records 表格不存在")

        db.close()

    except Exception as e:
        print(f"❌ 查詢失敗: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🗄️ 案件資料庫重建工具")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_current_structure()
    else:
        print("\n⚠️ 注意：此操作將完全重建 case_records 表格")
        print("⚠️ 所有現有資料將被刪除！")

        confirm = input("\n是否繼續？ (輸入 'YES' 確認): ")
        if confirm == "YES":
            success = rebuild_database()
            if success:
                print(f"\n🎉 重建成功！時間: {datetime.now()}")
                sys.exit(0)
            else:
                print(f"\n❌ 重建失敗！時間: {datetime.now()}")
                sys.exit(1)
        else:
            print("❌ 操作已取消")
            sys.exit(0)