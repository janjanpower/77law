BEGIN;

-- 把舊欄位資料（若還在）補到新欄位
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'login_users' AND column_name = 'teanat_status'
  ) THEN
    UPDATE login_users
    SET tenant_status = COALESCE(tenant_status, teanat_status);
  END IF;
END $$;

-- 設定 is_active 預設 False（強開手動控制）
ALTER TABLE login_users
  ALTER COLUMN is_active SET DEFAULT FALSE;
UPDATE login_users SET is_active = FALSE WHERE is_active IS NULL;

-- 若仍存在舊欄位 teanat_status，可安全移除
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'login_users' AND column_name = 'teanat_status'
  ) THEN
    ALTER TABLE login_users DROP COLUMN teanat_status;
  END IF;
END $$;

COMMIT;
