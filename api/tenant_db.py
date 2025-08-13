from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TENANT_DATABASES = {
    # 範例: "1234": "postgresql://user:pass@host/dbname"
}

@lru_cache(maxsize=None)
def get_tenant_engine(client_id: str):
    if client_id not in TENANT_DATABASES:
        raise ValueError(f"Unknown client_id: {client_id}")
    engine = create_engine(TENANT_DATABASES[client_id])
    return engine

def get_tenant_session(client_id: str):
    engine = get_tenant_engine(client_id)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()
