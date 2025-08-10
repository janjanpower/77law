BEGIN;

-- 付費時間欄位
ALTER TABLE login_users
  ADD COLUMN IF NOT EXISTS paid_from  timestamptz,
  ADD COLUMN IF NOT EXISTS paid_until timestamptz;

-- 觸發函式：plan_type 變更時自動設定付費區間與 tenant_status
CREATE OR REPLACE FUNCTION set_billing_and_tenant_status()
RETURNS TRIGGER AS $$
BEGIN
  -- unpaid：視為未開通
  IF lower(NEW.plan_type::text) = 'unpaid' THEN
    NEW.tenant_status := FALSE;
    NEW.paid_from  := NULL;
    NEW.paid_until := NULL;
    RETURN NEW;
  END IF;

  -- 若是 INSERT 或 plan_type 有變更，起算一年
  IF TG_OP = 'INSERT' OR (OLD.plan_type IS DISTINCT FROM NEW.plan_type) THEN
    NEW.paid_from  := COALESCE(NEW.paid_from, now());
    NEW.paid_until := NEW.paid_from + interval '1 year';
  ELSE
    NEW.paid_from  := COALESCE(NEW.paid_from,  OLD.paid_from);
    NEW.paid_until := COALESCE(NEW.paid_until, OLD.paid_until);
  END IF;

  -- 依是否過期設定 tenant_status
  IF NEW.paid_until IS NOT NULL AND now() < NEW.paid_until THEN
    NEW.tenant_status := TRUE;
  ELSE
    NEW.tenant_status := FALSE;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 掛在 plan_type 上（INSERT / UPDATE OF plan_type）
DROP TRIGGER IF EXISTS trg_login_users_plan_billing ON login_users;
CREATE TRIGGER trg_login_users_plan_billing
BEFORE INSERT OR UPDATE OF plan_type ON login_users
FOR EACH ROW
EXECUTE FUNCTION set_billing_and_tenant_status();

-- 檢核：plan_type 與 tenant_status 一致
ALTER TABLE login_users DROP CONSTRAINT IF EXISTS chk_login_users_plan_tenant_align;
ALTER TABLE login_users
ADD CONSTRAINT chk_login_users_plan_tenant_align
CHECK (
  (lower(plan_type::text) = 'unpaid' AND tenant_status = FALSE)
  OR
  (lower(plan_type::text) <> 'unpaid' AND tenant_status = TRUE)
);

-- 批次用索引
CREATE INDEX IF NOT EXISTS idx_login_users_paid_until_active
ON login_users (paid_until)
WHERE tenant_status = TRUE AND plan_type <> 'unpaid';

COMMIT;
