#!/usr/bin/env python3
"""
Mark expired paid tenants as inactive (tenant_status = FALSE).
Use with Heroku Scheduler: `python expire_tenants.py`
Requires env: DATABASE_URL
"""
from pathlib import Path
import os, sys
from datetime import datetime
from contextlib import closing
from pathlib import Path
import os
from dotenv import load_dotenv  # 這行是關鍵，剛剛漏了

# 載入專案根目錄的 .env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

print(f"✅ 已載入 DATABASE_URL: {DATABASE_URL}")


try:
    import psycopg2
except Exception as e:
    print("ERROR: psycopg2 is required. Add it to requirements.txt", file=sys.stderr)
    raise

SQL = '''
UPDATE login_users
SET tenant_status = FALSE
WHERE plan_type <> 'unpaid'
  AND tenant_status = TRUE
  AND paid_until IS NOT NULL
  AND now() >= paid_until;
'''

def main():
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        print('ERROR: DATABASE_URL not set', file=sys.stderr)
        sys.exit(1)
    try:
        with closing(psycopg2.connect(dsn)) as conn:
            conn.autocommit = True
            with closing(conn.cursor()) as cur:
                cur.execute(SQL)
                print(f'[{datetime.utcnow().isoformat()}Z] expired tenants updated:', cur.rowcount)
    except Exception as e:
        print('ERROR:', e, file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
