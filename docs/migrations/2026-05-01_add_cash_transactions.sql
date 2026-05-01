-- External cash deposits and withdrawals should be tracked separately from trades.
-- This keeps portfolio funding flows distinct from actual asset buy/sell activity.

CREATE TABLE IF NOT EXISTS cash_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    asset VARCHAR(20) NOT NULL,
    flow_type VARCHAR(20) NOT NULL,
    amount DECIMAL(20, 8) NOT NULL CHECK (amount > 0),
    executed_at TIMESTAMPTZ NOT NULL,
    source_platform VARCHAR(50),
    reference VARCHAR(100),
    notes TEXT,
    tags VARCHAR(50)[],

    signed_amount DECIMAL(20, 8) GENERATED ALWAYS AS (
        CASE WHEN flow_type = 'WITHDRAWAL' THEN -amount ELSE amount END
    ) STORED
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'cash_transactions_flow_type_allowed_values'
    ) THEN
        ALTER TABLE cash_transactions
        ADD CONSTRAINT cash_transactions_flow_type_allowed_values
        CHECK (flow_type IN ('DEPOSIT', 'WITHDRAWAL'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_cash_transactions_asset ON cash_transactions(asset);
CREATE INDEX IF NOT EXISTS idx_cash_transactions_executed_at ON cash_transactions(executed_at DESC);

ALTER TABLE cash_transactions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'cash_transactions'
          AND policyname = 'Allow all'
    ) THEN
        CREATE POLICY "Allow all" ON cash_transactions FOR ALL USING (true);
    END IF;
END $$;
