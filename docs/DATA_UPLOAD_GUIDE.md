# Trigger - Data Upload Guide

## Quick Start

### Step 1: Set Up Personal Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Name it something like "trigger-trading-journal"
3. Save your project URL and anon key

### Step 2: Run the Schema

1. In Supabase Dashboard, go to **SQL Editor**
2. Copy the contents of `docs/SCHEMA.sql`
3. Run it to create all tables

### Step 3: Configure Trigger Backend

Update `backend/.env`:
```env
PERSONAL_SUPABASE_URL=https://your-project.supabase.co
PERSONAL_SUPABASE_KEY=your-anon-key

# Arete DB (read-only for prices/research)
ARETE_SUPABASE_URL=https://goptgqfllyutklnyjvoj.supabase.co
# Use keychain for Arete key: supabase-arete-anon
```

---

## Uploading Data

### 1. Asset Mapping (Do First!)

Before uploading positions or trades, set up your asset mappings so allocations work correctly.

#### Option A: Supabase Dashboard

1. Go to **Table Editor** → `asset_mapping`
2. Click **Insert Row**
3. Fill in:
   - `asset`: Symbol (e.g., "BTC", "AAPL")
   - `asset_class`: One of: Crypto, Stocks, Commodities, Cash
   - `sector`: See list below
   - `full_name`: Human-readable name (optional)

#### Option B: SQL Insert

```sql
INSERT INTO asset_mapping (asset, asset_class, sector, full_name) VALUES
-- Crypto
('BTC', 'Crypto', 'Crypto Majors', 'Bitcoin'),
('ETH', 'Crypto', 'Crypto Majors', 'Ethereum'),
('AAVE', 'Crypto', 'DeFi', 'Aave'),
('TAO', 'Crypto', 'Decentralised AI', 'Bittensor'),

-- Stocks
('NVDA', 'Stocks', 'AI Equities', 'NVIDIA'),
('MSTR', 'Stocks', 'Crypto Equities', 'MicroStrategy'),

-- Commodities
('GLD', 'Commodities', 'Precious Metals', 'SPDR Gold Trust'),
('BNO', 'Commodities', 'Energy', 'Brent Oil Fund'),

-- Cash
('Cash', 'Cash', 'USD', 'Cash'),
('USD', 'Cash', 'USD', 'US Dollar');
```

#### Sector Reference

| Asset Class | Available Sectors |
|-------------|-------------------|
| Crypto | DeFi, Decentralised AI, Crypto Majors, Crypto Equities, Stablecoin |
| Stocks | AI Equities, Crypto Equities, Financials, Commodity Miners |
| Commodities | Energy, Precious Metals |
| Cash | USD, Stablecoin |

---

### 2. Starting Positions

These are your initial holdings — the baseline from which all trades are applied.

#### Format

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `asset` | text | ✓ | Symbol (must exist in asset_mapping) |
| `quantity` | decimal | ✓ | Number of units |
| `avg_entry_price` | decimal | | Your cost basis per unit |
| `snapshot_date` | date | ✓ | Date of this snapshot |
| `notes` | text | | Any notes |

#### Option A: Supabase Dashboard

1. Go to **Table Editor** → `starting_positions`
2. Insert rows for each position

#### Option B: SQL Insert

```sql
INSERT INTO starting_positions (asset, quantity, avg_entry_price, snapshot_date, notes) VALUES
-- Crypto holdings
('BTC', 0.5, 45000, '2026-04-01', 'Core position'),
('ETH', 5.0, 2200, '2026-04-01', 'Core position'),
('AAVE', 100, 180, '2026-04-01', 'DeFi exposure'),

-- Stock holdings
('NVDA', 50, 450, '2026-04-01', 'AI exposure'),

-- Commodities
('GLD', 100, 175, '2026-04-01', 'Gold hedge'),

-- Cash
('Cash', 50000, 1, '2026-04-01', 'USD cash balance');
```

#### Option C: CSV Upload

1. Create a CSV file (`positions.csv`):
```csv
asset,quantity,avg_entry_price,snapshot_date,notes
BTC,0.5,45000,2026-04-01,Core position
ETH,5.0,2200,2026-04-01,Core position
Cash,50000,1,2026-04-01,USD cash balance
```

2. In Supabase Dashboard → Table Editor → `starting_positions`
3. Click **Import data from CSV**
4. Upload your file

---

### 3. Trades

#### Manual Entry Format

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `asset` | text | ✓ | Symbol |
| `side` | text | ✓ | 'BUY' or 'SELL' |
| `quantity` | decimal | ✓ | Units traded |
| `price` | decimal | ✓ | Execution price |
| `executed_at` | timestamp | ✓ | When trade happened |
| `trade_type` | text | | entry, add, trim, exit, stop_loss |
| `strategy` | text | | thesis_driven, momentum, scalp |
| `timeframe` | text | | day_trade, swing, position, core |
| `entry_rationale` | text | | Why you took this trade |
| `source` | text | | manual, ibkr, hyperliquid |

#### Option A: SQL Insert

```sql
INSERT INTO trades (asset, side, quantity, price, executed_at, trade_type, strategy, source) VALUES
('BTC', 'BUY', 0.1, 65000, '2026-04-02 10:30:00+00', 'add', 'thesis_driven', 'manual'),
('ETH', 'SELL', 2, 3200, '2026-04-02 14:15:00+00', 'trim', 'rebalance', 'manual');
```

#### Option B: CSV Import (Manual Trades)

Create `trades_manual.csv`:
```csv
asset,side,quantity,price,executed_at,trade_type,strategy,source,entry_rationale
BTC,BUY,0.1,65000,2026-04-02T10:30:00Z,add,thesis_driven,manual,Adding on dip
ETH,SELL,2,3200,2026-04-02T14:15:00Z,trim,rebalance,manual,Taking profits
```

---

### 4. IBKR CSV Import

*Awaiting sample CSV from David — transformation script to be created*

IBKR exports typically include:
- Trade date/time
- Symbol
- Side (BOT/SLD)
- Quantity
- Price
- Commission
- Net proceeds

The transformation script will:
1. Map BOT → BUY, SLD → SELL
2. Parse IBKR date format
3. Extract symbol from IBKR format
4. Calculate cash flow
5. Set source = 'ibkr'

**Placeholder location:** `backend/scripts/transform_ibkr.py`

---

### 5. Principles

#### Format

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | text | ✓ | Short name |
| `description` | text | ✓ | Full explanation |
| `category` | text | | risk, entry, exit, sizing, psychology |
| `rule_type` | text | | 'hard' (never break) or 'soft' (guidelines) |
| `priority` | int | | 1-10 (10 = most important) |
| `quantifiable` | bool | | Can it be measured? |
| `metric` | text | | What to measure |
| `threshold` | decimal | | The limit/target |

#### Example Principles

```sql
INSERT INTO principles (title, description, category, rule_type, priority, quantifiable, metric, threshold) VALUES
-- Risk Management (Hard Rules)
('Max Position Size', 'Never allocate more than 10% of portfolio to a single position', 'sizing', 'hard', 10, true, 'position_size_pct', 10),
('Stop Loss Required', 'Every trade must have a defined stop loss before entry', 'risk', 'hard', 10, false, NULL, NULL),
('Max Daily Loss', 'Stop trading if daily loss exceeds 3% of portfolio', 'risk', 'hard', 9, true, 'daily_loss_pct', 3),

-- Entry Rules (Soft Guidelines)
('Thesis Required', 'Document why you are taking the trade before entry', 'entry', 'soft', 8, false, NULL, NULL),
('Wait for Setup', 'Do not chase - wait for the setup to come to you', 'entry', 'soft', 7, false, NULL, NULL),
('Avoid FOMO', 'If you missed the move, wait for the next one', 'psychology', 'soft', 8, false, NULL, NULL),

-- Exit Rules
('Partial Profits', 'Take partial profits at 2R and 3R', 'exit', 'soft', 7, true, 'r_multiple', 2),
('Trailing Stop', 'Move stop to breakeven after 1.5R', 'exit', 'soft', 6, true, 'r_multiple', 1.5),

-- Psychology
('No Revenge Trading', 'After a loss, take a 30 minute break before next trade', 'psychology', 'hard', 9, false, NULL, NULL),
('Sleep on Decisions', 'For positions >5% of portfolio, wait 24 hours before entry', 'psychology', 'soft', 7, true, 'position_size_pct', 5);
```

#### Tracking Principle Compliance

When logging a trade or post-mortem, reference principles:

```sql
-- Update principle tracking after following it
UPDATE principles 
SET times_followed = times_followed + 1
WHERE id = 'principle-uuid';

-- Update after violating it
UPDATE principles 
SET times_violated = times_violated + 1,
    last_violated_at = NOW()
WHERE id = 'principle-uuid';
```

---

## Verification Queries

After uploading, verify your data:

```sql
-- Check starting positions
SELECT * FROM starting_positions ORDER BY cost_basis_usd DESC;

-- Check trades
SELECT * FROM trades ORDER BY executed_at DESC LIMIT 20;

-- Check asset mappings
SELECT * FROM asset_mapping ORDER BY asset_class, sector, asset;

-- Calculate current positions
SELECT * FROM get_current_positions();

-- Check unmapped assets (should return empty if all mapped)
SELECT DISTINCT t.asset 
FROM trades t 
LEFT JOIN asset_mapping am ON t.asset = am.asset
WHERE am.asset IS NULL;
```

---

## Next Steps

Once data is uploaded:

1. **Test the API**: Start the backend and hit `/api/portfolio/positions`
2. **Check the dashboard**: The Portfolio tab should now show real data
3. **Set up CSV imports**: Send me IBKR/other CSV samples for transformation scripts

---

## Troubleshooting

### "Asset not found in mapping"
→ Add the asset to `asset_mapping` table first

### "Foreign key violation"
→ Ensure referenced IDs (thesis_id, etc.) exist

### "Cash balance seems wrong"
→ Check that Cash is in starting_positions and trades correctly calculate cash_flow

### "Prices not showing"
→ Verify the asset symbol matches exactly in Arete's `cmc_asset_data` or `stock_ohlcv`
