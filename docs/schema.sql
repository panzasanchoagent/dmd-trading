-- ============================================================================
-- TRIGGER - Personal Database Schema
-- ============================================================================
-- Run this in your Personal Supabase project (not Arete!)
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE PORTFOLIO TABLES
-- ============================================================================

-- Starting Positions (Portfolio Snapshot)
-- This is your baseline - trades are applied on top of this
CREATE TABLE IF NOT EXISTS starting_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Position info
    asset VARCHAR(20) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    avg_entry_price DECIMAL(20, 8),
    snapshot_date DATE NOT NULL,
    
    -- Computed
    cost_basis_usd DECIMAL(20, 2) GENERATED ALWAYS AS (quantity * avg_entry_price) STORED,
    
    -- Metadata
    notes TEXT,
    
    UNIQUE(asset, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_starting_positions_asset ON starting_positions(asset);
CREATE INDEX IF NOT EXISTS idx_starting_positions_date ON starting_positions(snapshot_date);

-- ============================================================================
-- TRADES
-- ============================================================================

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Core trade data
    asset VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity DECIMAL(20, 8) NOT NULL CHECK (quantity > 0),
    price DECIMAL(20, 8) NOT NULL CHECK (price > 0),
    quote_currency VARCHAR(10) DEFAULT 'USD',
    executed_at TIMESTAMPTZ NOT NULL,
    
    -- Cash flow (negative for buys, positive for sells)
    cash_flow DECIMAL(20, 2) GENERATED ALWAYS AS (
        CASE 
            WHEN side = 'BUY' THEN -(quantity * price)
            WHEN side = 'SELL' THEN (quantity * price)
        END
    ) STORED,
    
    -- Trade metadata
    trade_type VARCHAR(20) CHECK (trade_type IN ('entry', 'add', 'trim', 'exit', 'stop_loss', 'rebalance')),
    strategy VARCHAR(50),
    timeframe VARCHAR(20) CHECK (timeframe IN ('day_trade', 'swing', 'position', 'core')),
    
    -- Risk management
    planned_entry DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    position_size_pct DECIMAL(5, 2),
    
    -- Context
    entry_rationale TEXT,
    thesis_id UUID,
    
    -- Source tracking (for CSV imports)
    source VARCHAR(50) DEFAULT 'manual',
    source_trade_id VARCHAR(100),
    
    -- Fees
    commission DECIMAL(20, 8) DEFAULT 0,
    fees DECIMAL(20, 8) DEFAULT 0,
    
    -- Tags
    tags TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_trades_asset ON trades(asset);
CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at);
CREATE INDEX IF NOT EXISTS idx_trades_source ON trades(source);

-- ============================================================================
-- ASSET MAPPING
-- ============================================================================

CREATE TABLE IF NOT EXISTS asset_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    asset VARCHAR(20) NOT NULL UNIQUE,
    asset_class VARCHAR(50) NOT NULL CHECK (asset_class IN ('Crypto', 'Stocks', 'Commodities', 'Cash')),
    sector VARCHAR(50) NOT NULL CHECK (sector IN (
        'DeFi', 
        'Decentralised AI', 
        'Crypto Majors', 
        'Crypto Equities',
        'AI Equities', 
        'Financials',
        'Energy', 
        'Precious Metals',
        'Commodity Miners',
        'Stablecoin',
        'USD'
    )),
    
    -- Optional metadata
    full_name VARCHAR(200),
    description TEXT,
    coingecko_id VARCHAR(100),
    yahoo_ticker VARCHAR(20),
    
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- JOURNAL ENTRIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    entry_date DATE NOT NULL UNIQUE,
    
    -- Pre-market
    market_outlook TEXT,
    planned_actions TEXT,
    risk_appetite VARCHAR(20) CHECK (risk_appetite IN ('aggressive', 'normal', 'defensive')),
    
    -- End of day
    what_happened TEXT,
    what_went_well TEXT,
    what_went_poorly TEXT,
    lessons_learned TEXT,
    
    -- Emotional state
    emotional_state TEXT,
    energy_level INT CHECK (energy_level BETWEEN 1 AND 5),
    focus_level INT CHECK (focus_level BETWEEN 1 AND 5),
    
    -- Links
    trade_ids UUID[],
    principle_violations UUID[]
);

CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON journal_entries(entry_date);

-- ============================================================================
-- PRINCIPLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS principles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) CHECK (category IN ('risk', 'entry', 'exit', 'sizing', 'psychology')),
    rule_type VARCHAR(20) DEFAULT 'soft' CHECK (rule_type IN ('hard', 'soft')),
    
    -- Quantifiable rules
    quantifiable BOOLEAN DEFAULT FALSE,
    metric VARCHAR(100),
    threshold DECIMAL(20, 8),
    
    -- Tracking
    priority INT DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    times_followed INT DEFAULT 0,
    times_violated INT DEFAULT 0,
    last_violated_at TIMESTAMPTZ,
    
    active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- POST MORTEMS
-- ============================================================================

CREATE TABLE IF NOT EXISTS post_mortems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    trade_ids UUID[] NOT NULL,
    asset VARCHAR(20) NOT NULL,
    
    -- Results
    result VARCHAR(20) CHECK (result IN ('win', 'loss', 'breakeven')),
    pnl DECIMAL(20, 2),
    pnl_pct DECIMAL(10, 4),
    
    -- Scores (1-5)
    entry_quality INT CHECK (entry_quality BETWEEN 1 AND 5),
    exit_quality INT CHECK (exit_quality BETWEEN 1 AND 5),
    sizing_quality INT CHECK (sizing_quality BETWEEN 1 AND 5),
    thesis_quality INT CHECK (thesis_quality BETWEEN 1 AND 5),
    
    -- Reflection
    what_went_well TEXT,
    what_went_poorly TEXT,
    would_do_differently TEXT,
    key_lesson TEXT,
    
    -- Patterns
    emotional_factors TEXT[],
    execution_errors TEXT[],
    principles_followed UUID[],
    principles_violated UUID[],
    
    -- AI feedback
    ai_feedback TEXT,
    ai_generated_at TIMESTAMPTZ
);

-- ============================================================================
-- COACH SESSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS coach_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    session_type VARCHAR(50) CHECK (session_type IN ('pre_trade', 'post_trade', 'weekly_review', 'ad_hoc')),
    trade_ids UUID[],
    
    -- Conversation stored as JSONB array
    messages JSONB DEFAULT '[]'::jsonb,
    
    -- Summary
    key_insights TEXT[],
    action_items TEXT[],
    
    -- Model info
    model_used VARCHAR(100),
    tokens_used INT
);

-- ============================================================================
-- PATTERNS (Detected trading patterns)
-- ============================================================================

CREATE TABLE IF NOT EXISTS patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    pattern_type VARCHAR(50) NOT NULL,    -- 'positive', 'negative', 'neutral'
    pattern_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Evidence
    trade_ids UUID[],
    occurrence_count INT DEFAULT 1,
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    last_detected_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Impact
    avg_pnl_when_present DECIMAL(10, 2),
    win_rate_when_present DECIMAL(5, 2),
    
    -- AI analysis
    ai_recommendation TEXT,
    ai_analyzed_at TIMESTAMPTZ,
    
    active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- ROW LEVEL SECURITY (Optional but recommended)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE starting_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE principles ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_mortems ENABLE ROW LEVEL SECURITY;
ALTER TABLE coach_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE patterns ENABLE ROW LEVEL SECURITY;

-- Create policies for anon access (adjust based on your needs)
-- For a personal DB, you might want to allow full access to authenticated users

CREATE POLICY "Allow all operations" ON starting_positions FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON trades FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON asset_mapping FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON journal_entries FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON principles FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON post_mortems FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON coach_sessions FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON patterns FOR ALL USING (true);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to calculate current positions
CREATE OR REPLACE FUNCTION get_current_positions()
RETURNS TABLE (
    asset VARCHAR(20),
    quantity DECIMAL(20, 8),
    avg_entry_price DECIMAL(20, 8),
    cost_basis DECIMAL(20, 2),
    trade_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH starting AS (
        SELECT 
            sp.asset,
            sp.quantity as start_qty,
            sp.avg_entry_price as start_price,
            sp.cost_basis_usd as start_cost
        FROM starting_positions sp
        WHERE sp.snapshot_date = (SELECT MAX(snapshot_date) FROM starting_positions)
    ),
    trade_totals AS (
        SELECT 
            t.asset,
            SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE -t.quantity END) as net_qty,
            SUM(CASE WHEN t.side = 'BUY' THEN t.quantity * t.price ELSE 0 END) as buy_cost,
            SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE 0 END) as buy_qty,
            COUNT(*) as num_trades
        FROM trades t
        GROUP BY t.asset
    )
    SELECT 
        COALESCE(s.asset, tt.asset) as asset,
        COALESCE(s.start_qty, 0) + COALESCE(tt.net_qty, 0) as quantity,
        CASE 
            WHEN (COALESCE(s.start_qty, 0) + COALESCE(tt.buy_qty, 0)) > 0 
            THEN (COALESCE(s.start_cost, 0) + COALESCE(tt.buy_cost, 0)) / 
                 (COALESCE(s.start_qty, 0) + COALESCE(tt.buy_qty, 0))
            ELSE 0
        END as avg_entry_price,
        COALESCE(s.start_cost, 0) + COALESCE(tt.buy_cost, 0) as cost_basis,
        COALESCE(tt.num_trades, 0) as trade_count
    FROM starting s
    FULL OUTER JOIN trade_totals tt ON s.asset = tt.asset
    WHERE (COALESCE(s.start_qty, 0) + COALESCE(tt.net_qty, 0)) > 0;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA (Comment out in production)
-- ============================================================================

-- Uncomment below to insert sample asset mappings
/*
INSERT INTO asset_mapping (asset, asset_class, sector, full_name) VALUES
-- Crypto Majors
('BTC', 'Crypto', 'Crypto Majors', 'Bitcoin'),
('ETH', 'Crypto', 'Crypto Majors', 'Ethereum'),
('SOL', 'Crypto', 'Crypto Majors', 'Solana'),

-- DeFi
('AAVE', 'Crypto', 'DeFi', 'Aave'),
('UNI', 'Crypto', 'DeFi', 'Uniswap'),
('MKR', 'Crypto', 'DeFi', 'Maker'),
('CRV', 'Crypto', 'DeFi', 'Curve'),
('HYPE', 'Crypto', 'DeFi', 'Hyperliquid'),

-- Decentralised AI
('TAO', 'Crypto', 'Decentralised AI', 'Bittensor'),
('RNDR', 'Crypto', 'Decentralised AI', 'Render'),
('FET', 'Crypto', 'Decentralised AI', 'Fetch.ai'),

-- Stablecoins
('USDC', 'Crypto', 'Stablecoin', 'USD Coin'),
('USDT', 'Crypto', 'Stablecoin', 'Tether'),

-- AI Equities
('NVDA', 'Stocks', 'AI Equities', 'NVIDIA'),
('AMD', 'Stocks', 'AI Equities', 'Advanced Micro Devices'),
('MSFT', 'Stocks', 'AI Equities', 'Microsoft'),
('GOOG', 'Stocks', 'AI Equities', 'Alphabet'),

-- Crypto Equities
('MSTR', 'Stocks', 'Crypto Equities', 'MicroStrategy'),
('COIN', 'Stocks', 'Crypto Equities', 'Coinbase'),
('MARA', 'Stocks', 'Crypto Equities', 'Marathon Digital'),

-- Financials
('JPM', 'Stocks', 'Financials', 'JPMorgan Chase'),
('GS', 'Stocks', 'Financials', 'Goldman Sachs'),

-- Precious Metals
('GLD', 'Commodities', 'Precious Metals', 'SPDR Gold Trust'),
('SLV', 'Commodities', 'Precious Metals', 'iShares Silver Trust'),

-- Energy
('USO', 'Commodities', 'Energy', 'United States Oil Fund'),
('BNO', 'Commodities', 'Energy', 'Brent Oil Fund'),
('UNG', 'Commodities', 'Energy', 'United States Natural Gas Fund'),

-- Cash
('USD', 'Cash', 'USD', 'US Dollar'),
('Cash', 'Cash', 'USD', 'Cash')

ON CONFLICT (asset) DO NOTHING;
*/
