-- Add provenance field for imported trades
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS source_platform VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_trades_source_platform ON trades(source_platform);
