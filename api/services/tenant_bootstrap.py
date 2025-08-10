# api/services/tenant_bootstrap.py
import os
import re
import urllib.parse
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, text
from api.database import Base
from models.case_records import CaseRecord  # 依你實際位置調整匯入

DATABASE_URL = os.getenv("DATABASE_URL")

_slug_re = re.compile(r"[^a-z0-9_]+")

def _schema_name_from_client_id(client_id: str) -> str:
    s = client_id.strip().lower().replace("-", "_")
    s = _slug_re.sub("_", s)
    s = s.strip("_")
    if not s:
        s = "x"
    return f"tenant_{s}"

def _compose_schema_url(base_url: str, schema: str) -> str:
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}options={urllib.parse.quote('-c search_path=' + schema)}"

def ensure_tenant_schema(client_id: str) -> str:
    """
    建立租戶 schema，並建立 case_records 表
    更新 login_users.tenant_db_url
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")

    schema = _schema_name_from_client_id(client_id)

    # 1) 用 psycopg2 建 schema（若不存在）
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
    cur.close()
    conn.close()

    # 2) 用 SQLAlchemy 建表（與主系統一致）
    schema_url = _compose_schema_url(DATABASE_URL, schema)
    engine = create_engine(schema_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine, tables=[CaseRecord.__table__])

    # 3) 更新 login_users.tenant_db_url
    main_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with main_engine.begin() as main_conn:
        main_conn.execute(
            text("UPDATE login_users SET tenant_db_url=:url WHERE client_id=:cid"),
            {"url": schema_url, "cid": client_id}
        )

    print(f"✅ Schema {schema} 建立完成，tenant_db_url 已更新為 {schema_url}")
    return schema_url
