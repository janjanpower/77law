# api/services/tenant_bootstrap.py
# 建議：整份覆蓋你現有檔案

import os
from sqlalchemy import create_engine, text
from api.database import Base, DATABASE_URL
from api.models_cases import CaseRecord  # 需要載入，讓 ORM 知道要建哪些索引/約束


def _compose_schema_url(base_url: str, schema: str) -> str:
    """
    將 Heroku PG 的 DATABASE_URL 加上 search_path，指向指定 schema。
    """
    if not base_url:
        raise RuntimeError("DATABASE_URL not configured")
    if "options=" in base_url and "search_path" in base_url:
        return base_url  # 已有設定就不動
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}options=-csearch_path%3D{schema}"


def _ensure_case_records_sql_fallback(engine, schema: str):
    # 確保動作都在目標 schema
    with engine.begin() as cx:
        cx.execute(text(f"SET search_path TO {schema}"))
        cx.execute(text("""
            CREATE TABLE IF NOT EXISTS case_records (
                id BIGSERIAL PRIMARY KEY,
                client_id TEXT NOT NULL,
                case_id   TEXT NOT NULL,

                -- 與 models_cases.py 對齊的欄位
                case_type TEXT NOT NULL,
                client    TEXT NOT NULL,
                lawyer    TEXT,
                legal_affairs TEXT,

                progress  TEXT NOT NULL DEFAULT '待處理',
                case_reason TEXT,
                case_number TEXT,
                opposing_party TEXT,
                court     TEXT,
                division  TEXT,
                progress_date TEXT,

                -- JSON 欄位（允許 NULL，與 model 對齊）
                progress_stages JSONB NULL,
                progress_notes  JSONB NULL,
                progress_times  JSONB NULL,

                -- 舊系統時間戳（允許 NULL）
                created_date TIMESTAMPTZ NULL,
                updated_date TIMESTAMPTZ NULL,

                -- 必要補欄位（與 model 對齊）
                uploaded_by TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                is_active   BOOLEAN NOT NULL DEFAULT TRUE,

                CONSTRAINT uq_case_records_client_case UNIQUE (client_id, case_id)
            );

            -- 基本索引（其餘交給 ORM 建立）
            CREATE INDEX IF NOT EXISTS idx_case_records_client ON case_records (client_id);
            CREATE INDEX IF NOT EXISTS idx_case_records_case   ON case_records (case_id);
        """))

def _migrate_case_records_columns(engine, schema: str):
    # 安全可重複執行的遷移，確保舊表欄位補齊且不多
    alters = [
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS uploaded_by TEXT",
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS is_active  BOOLEAN NOT NULL DEFAULT TRUE",

        # JSON 欄位允許 NULL，就不強制 DEFAULT；但如果你想預設空物件可解除註解：
        # \"ALTER TABLE case_records ALTER COLUMN progress_stages SET DEFAULT '{}'::jsonb\",
        # \"ALTER TABLE case_records ALTER COLUMN progress_notes  SET DEFAULT '{}'::jsonb\",
        # \"ALTER TABLE case_records ALTER COLUMN progress_times  SET DEFAULT '{}'::jsonb\",

        "ALTER TABLE case_records ALTER COLUMN case_type SET NOT NULL",
        "ALTER TABLE case_records ALTER COLUMN client    SET NOT NULL",
        "ALTER TABLE case_records ALTER COLUMN progress  SET NOT NULL",
    ]
    with engine.begin() as cx:
        cx.execute(text(f"SET search_path TO {schema}"))
        for sql in alters:
            cx.execute(text(sql))

    # 驗證 created_at 存在
    with engine.connect() as cx:
        cx.execute(text(f"SET search_path TO {schema}"))
        cols = cx.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'case_records'
        """)).scalars().all()
    if "created_at" not in cols:
        raise RuntimeError(f"[migrate] created_at still missing in {schema}. Actual columns: {cols}")

def ensure_tenant_schema(client_id: str) -> str:
    """
    建立/修復租戶 schema 的正確流程（只影響新註冊）：
      1) 建立 schema（若不存在）
      2) 以 SQL fallback 先建表（若不存在）
      3) 立刻做欄位遷移補齊
      4) 最後交給 ORM 建索引/約束（此時欄位已存在，不會再報 created_at 缺失）

    回傳該租戶可用的 DB 連線字串（含 search_path）。
    """
    schema = f"client_{client_id}".strip()
    base_url = os.getenv("DATABASE_URL", DATABASE_URL)
    if not base_url:
        raise RuntimeError("DATABASE_URL not configured")

    # 1) 先確保 schema 存在
    root_engine = create_engine(base_url, pool_pre_ping=True)
    with root_engine.begin() as cx:
        cx.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    # 2) 切到該 schema 的 engine
    schema_url = _compose_schema_url(base_url, schema)
    tenant_engine = create_engine(schema_url, pool_pre_ping=True)

    # 3) 先用 SQL 建最小正確表
    _ensure_case_records_sql_fallback(tenant_engine)

    # 4) 立刻做欄位/預設遷移（舊表補齊，新表無害）
    _migrate_case_records_columns(tenant_engine)

    # 5) 最後才讓 ORM 建索引/約束（此時欄位齊全，不會噴錯）
    Base.metadata.create_all(bind=tenant_engine, tables=[CaseRecord.__table__])

    return schema_url
