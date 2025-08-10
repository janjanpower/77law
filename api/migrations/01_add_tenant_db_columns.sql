BEGIN;

ALTER TABLE login_users
  ADD COLUMN IF NOT EXISTS tenant_db_url   text,
  ADD COLUMN IF NOT EXISTS tenant_db_ready boolean DEFAULT FALSE;

COMMENT ON COLUMN login_users.tenant_db_url   IS '此事務所案件資料庫的連線字串（或留空，改存 config key）';
COMMENT ON COLUMN login_users.tenant_db_ready IS '該事務所案件庫是否已完成初始化（migrations）';

COMMIT;
