-- api/migrations/db_fix_login_users_plan_with_check.sql
-- 目的：
-- 1) 統一 plan_type 值
-- 2) 將 plan_type 轉為 ENUM（下拉）
-- 3) 依 plan_type 自動連動 tenant_status（unpaid→FALSE，其餘→TRUE）
-- 4) 加 CHECK 確保一致性
-- 5) 移除舊欄位 teanat_status（如仍存在）

BEGIN;

-- [A] 清資料為唯一鍵，避免轉型/檢核失敗
UPDATE login_users SET plan_type = 'unpaid'
WHERE plan_type IS NULL OR trim(plan_type::text) = '' OR lower(plan_type::text) IN ('未付費');

UPDATE login_users SET plan_type = 'basic_5'
WHERE lower(plan_type::text) IN ('基礎方案(5人)','basic','basic_5','standard');

UPDATE login_users SET plan_type = 'pro_10'
WHERE lower(plan_type::text) IN ('進階方案(10人)','pro','pro_10');

UPDATE login_users SET plan_type = 'team_20'
WHERE lower(plan_type::text) IN ('多人方案(20人)','team','team_20');

UPDATE login_users SET plan_type = 'unlimited'
WHERE lower(plan_type::text) IN ('無上限','unlimited');

-- [B] 建 ENUM（若尚未存在）
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan_type_enum') THEN
    CREATE TYPE plan_type_enum AS ENUM ('unpaid','basic_5','pro_10','team_20','unlimited');
  END IF;
END $$;

-- [C] 欄位轉為 ENUM + 預設值
ALTER TABLE login_users
  ALTER COLUMN plan_type TYPE plan_type_enum USING (plan_type::plan_type_enum),
  ALTER COLUMN plan_type SET DEFAULT 'unpaid',
  ALTER COLUMN plan_type SET NOT NULL;

-- [D] 確保 tenant_status 欄位存在且為 boolean NOT NULL（用 TRUE/FALSE，不用 NULL）
ALTER TABLE login_users
  ADD COLUMN IF NOT EXISTS tenant_status boolean;

UPDATE login_users
SET tenant_status = CASE
  WHEN lower(plan_type::text) = 'unpaid' THEN FALSE
  ELSE TRUE
END
WHERE tenant_status IS NULL;

ALTER TABLE login_users
  ALTER COLUMN tenant_status SET DEFAULT FALSE,
  ALTER COLUMN tenant_status SET NOT NULL;

-- [E] 依 plan_type 自動連動 tenant_status
CREATE OR REPLACE FUNCTION set_tenant_status_by_plan()
RETURNS TRIGGER AS $$
BEGIN
  IF lower(NEW.plan_type::text) = 'unpaid' THEN
    NEW.tenant_status := FALSE;
  ELSE
    NEW.tenant_status := TRUE;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_login_users_plan_sync ON login_users;
CREATE TRIGGER trg_login_users_plan_sync
BEFORE INSERT OR UPDATE OF plan_type ON login_users
FOR EACH ROW
EXECUTE FUNCTION set_tenant_status_by_plan();

-- [F] 檢核：plan_type 與 tenant_status 一致性
ALTER TABLE login_users DROP CONSTRAINT IF EXISTS chk_login_users_plan_tenant_align;
ALTER TABLE login_users
ADD CONSTRAINT chk_login_users_plan_tenant_align
CHECK (
  (lower(plan_type::text) = 'unpaid' AND tenant_status = FALSE)
  OR
  (lower(plan_type::text) <> 'unpaid' AND tenant_status = TRUE)
);

-- [G] 若仍有舊欄位 teanat_status，安全移除
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='login_users' AND column_name='teanat_status'
  ) THEN
    ALTER TABLE login_users DROP COLUMN teanat_status;
  END IF;
END $$;

COMMIT;
