-- Add trade category classification for imported and manual trades
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS category VARCHAR(50);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'trades_category_allowed_values'
    ) THEN
        ALTER TABLE trades
        ADD CONSTRAINT trades_category_allowed_values
        CHECK (category IS NULL OR category IN ('TradFi', 'Crypto - Hyperliquid', 'Crypto - Spot'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_trades_category ON trades(category);
