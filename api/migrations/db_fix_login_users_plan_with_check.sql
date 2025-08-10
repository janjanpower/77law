-- db_fix_login_users_plan_with_check.sql
-- 修正 login_users 的 plan_type / teanat_status 並立即檢查結果

BEGIN;

-- 舊資料補齊：空值或空白 -> unpaid
UPDATE login_users SET plan_type = 'unpaid'
WHERE plan_type IS NULL OR trim(plan_type) = '';

-- unpaid -> teanat_status = NULL；非 unpaid -> TRUE
UPDATE login_users SET teanat_status = NULL WHERE lower(plan_type) = 'unpaid';
UPDATE login_users SET teanat_status = TRUE
 WHERE lower(plan_type) <> 'unpaid' AND teanat_status IS DISTINCT FROM TRUE;

-- 防呆檢查（避免 unpaid 卻被設為 TRUE）
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='chk_login_users_plan_teanat') THEN
    ALTER TABLE login_users
      ADD CONSTRAINT chk_login_users_plan_teanat
      CHECK (NOT (lower(plan_type) = 'unpaid' AND teanat_status IS TRUE));
  END IF;
END $$;

COMMIT;

-- 驗證結果
TABLE (
    SELECT plan_type, teanat_status, COUNT(*) AS count
    FROM login_users
    GROUP BY plan_type, teanat_status
    ORDER BY plan_type
);
