# api/services/tenant_bootstrap.py
# 覆蓋整檔

import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from sqlalchemy import create_engine, text
from api.database import Base, DATABASE_URL
from api.models_cases import CaseRecord  # 讓 ORM 知道要建哪些索引/表

# ------------------ 工具 ------------------

def _schema_name(client_id: str) -> str:
    return f"client_{client_id}".strip()

def _compose_schema_url(base_url: str, schema: str) -> str:
    """
    在原連線字串上保留既有 query 參數（如 sslmode=require），
    並加入 options=-csearch_path=<schema>
    """
    if not base_url:
        raise RuntimeError("DATABASE_URL not configured")

    parts = urlsplit(base_url)
    qs = dict(parse_qsl(parts.query, keep_blank_values=True))
    qs["options"] = f"-csearch_path={schema}"
    new_query = urlencode(qs, doseq=True)

    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

def _set_search_path(engine, schema: str):
    with engine.begin() as cx:
        cx.execute(text(f"SET search_path TO {schema}"))

# ------------------ 建表 / 遷移 ------------------

def _ensure_case_records_sql_fallback(engine, schema: str):
    """
    先用 SQL 建出「你要的欄位」版本（若不存在）。
    欄位與 models_cases.py 對齊（僅包含你要的那幾個補欄位）。
    """
    with engine.begin() as cx:
        cx.execute(text(f"SET search_path TO {schema}"))
        cx.execute(text("""
            CREATE TABLE IF NOT EXISTS case_records (
                id BIGSERIAL PRIMARY KEY,
                client_id TEXT NOT NULL,
                case_id   TEXT NOT NULL,

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

                progress_stages JSONB NULL,
                progress_notes  JSONB NULL,
                progress_times  JSONB NULL,

                created_date TIMESTAMPTZ NULL,
                updated_date TIMESTAMPTZ NULL,

                uploaded_by TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                is_active   BOOLEAN NOT NULL DEFAULT TRUE,

                CONSTRAINT uq_case_records_client_case UNIQUE (client_id, case_id)
            );

            -- 基本索引，其他交給 ORM 完成
            CREATE INDEX IF NOT EXISTS idx_case_records_client ON case_records (client_id);
            CREATE INDEX IF NOT EXISTS idx_case_records_case   ON case_records (case_id);
        """))

def _migrate_case_records_columns(engine, schema: str):
    """
    安全可重複執行的遷移，補齊舊表欄位；不新增你沒有要的欄位。
    """
    alters = [
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS uploaded_by TEXT",
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        "ALTER TABLE case_records ADD COLUMN IF NOT EXISTS is_active  BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE case_records ALTER COLUMN case_type SET NOT NULL",
        "ALTER TABLE case_records ALTER COLUMN client    SET NOT NULL",
        "ALTER TABLE case_records ALTER COLUMN progress  SET NOT NULL",
    ]
    with engine.begin() as cx:
        cx.execute(text(f"SET search_path TO {schema}"))
        for sql in alters:
            cx.execute(text(sql))

    # 驗證確實存在
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

# ------------------ 對外主流程 ------------------

def ensure_tenant_schema(client_id: str) -> str:
    """
    建立/修復租戶 schema，並把 schema URL 寫回 login_users.tenant_db_url。
    流程：
      1) CREATE SCHEMA IF NOT EXISTS
      2) fallback 建表（若不存在）
      3) migrate 補欄位
      4) ORM 建索引/約束
      5) 回寫 login_users.tenant_db_url
    回傳：schema_url
    """
    schema = _schema_name(client_id)
    base_url = os.getenv("DATABASE_URL", DATABASE_URL)
    if not base_url:
        raise RuntimeError("DATABASE_URL not configured")

    # 先確保 schema 存在（在 root 連線）
    root_engine = create_engine(base_url, pool_pre_ping=True)
    with root_engine.begin() as cx:
        cx.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    # 建出指向該 schema 的連線
    schema_url = _compose_schema_url(base_url, schema)
    tenant_engine = create_engine(schema_url, pool_pre_ping=True)

    # 全程鎖定 search_path
    _set_search_path(tenant_engine, schema)

    # 1) 先建「你要的欄位」版本表
    _ensure_case_records_sql_fallback(tenant_engine, schema)

    # 2) 立即補欄位（舊表補齊，新表無害）
    _migrate_case_records_columns(tenant_engine, schema)

    # 3) ORM 建索引/約束（此時欄位已存在）
    _set_search_path(tenant_engine, schema)
    Base.metadata.create_all(bind=tenant_engine, tables=[CaseRecord.__table__])

    # 4) 回寫 URL 到 login_users（用 client_id 當 key）
    with root_engine.begin() as cx:
        cx.execute(
            text("""
                UPDATE login_users
                SET tenant_db_url = :u
                WHERE client_id = :cid
            """),
            {"u": schema_url, "cid": client_id}
        )

    # 讓你在 log 看得見（可留可拿掉）
    print(f"[tenant] schema={schema}")
    print(f"[tenant] schema_url={schema_url}")

    return schema_url
