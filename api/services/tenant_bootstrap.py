# api/services/tenant_bootstrap.py
import os
import urllib.parse
import psycopg2
from psycopg2 import sql

DATABASE_URL = os.getenv("DATABASE_URL")

def _compose_schema_url(base_url: str, schema: str) -> str:
    # 在連線字串後面加上 search_path
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}options={urllib.parse.quote('-c search_path='+schema)}"

def ensure_tenant_schema(client_id: str) -> str:
    """建立 tenant 專屬 schema + 基本表；回傳專屬連線字串（含 search_path）。"""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")

    schema = f"tenant_{client_id}"
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # 建 schema（若不存在）
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))

    # 在該 schema 建立你需要的基本表（示範一張 cases 表；你再按需擴充）
    cur.execute(sql.SQL("""
        CREATE TABLE IF NOT EXISTS {}.cases (
            id SERIAL PRIMARY KEY,
            case_no TEXT NOT NULL,
            title TEXT,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """).format(sql.Identifier(schema)))

    # 也可以在這裡執行更多初始化（索引、view、函式…）

    cur.close()
    conn.close()

    return _compose_schema_url(DATABASE_URL, schema)
