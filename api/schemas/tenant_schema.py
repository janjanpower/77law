# tenant_schema.py
from api.database import DATABASE_URL
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, func, text


def create_schema_and_tables(schema_name: str):
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()

    try:
        # 1. 建立 schema
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

        # 2. 初始化 metadata（綁定該 schema）
        metadata = MetaData(schema=schema_name)

        # 3. 定義該租戶 schema 內的資料表
        users_table = Table(
            "users", metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String, nullable=False),
            Column("email", String, nullable=True),
            Column("role", String, default="member"),
            Column("created_at", DateTime(timezone=True), server_default=func.now())
        )

        data_table = Table(
            "data_records", metadata,
            Column("id", Integer, primary_key=True),
            Column("user_id", Integer),
            Column("type", String),
            Column("content", String),
            Column("created_at", DateTime(timezone=True), server_default=func.now())
        )

        # 4. 在該 schema 下建立表格
        metadata.create_all(bind=engine)
        print(f"✅ 成功建立 schema: {schema_name} 和其表格")

    finally:
        connection.close()
