-- Trading Journal Personal Database Schema
-- Supabase (PostgreSQL)

-- ============================================
-- TRADES
-- Core trade log - manual entry, minimal friction
-- ============================================
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Trade details
    asset VARCHAR(20) NOT NULL,               -- BTC, ETH, SOL, etc.
    side VARCHAR(10) NOT NULL,                -- BUY, SELL
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quote_currency VARCHAR(10) DEFAULT 'USD',
    source_platform VARCHAR(50),             -- ibkr, manual, etc.
    
    -- Timing
    executed_at TIMESTAMPTZ NOT NULL,
    
    -- Classification
    trade_type VARCHAR(20),                   -- entry, add, trim, exit, stop_loss
    strategy VARCHAR(50),                     -- thesis_driven, momentum, scalp, mean_reversion
    timeframe VARCHAR(20),                    -- day_trade, swing, position
    
    -- Context links (to Arete DB - just store IDs for reference)
    thesis_id UUID,                           -- Link to Arete theses table
    note_ids UUID[],                          -- Links to Arete notes
    
    -- Execution quality
    planned_entry DECIMAL(20, 8),             -- What price you wanted
    slippage_pct DECIMAL(10, 4),              -- Calculated: (actual - planned) / planned * 100
    
    -- Risk management
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    position_size_pct DECIMAL(10, 4),         -- % of portfolio
    
    -- Notes
    entry_rationale TEXT,                     -- Quick note on why
    tags VARCHAR(50)[],
    
    -- Computed (updated by triggers/jobs)
    cash_flow DECIMAL(20, 8) GENERATED ALWAYS AS (
        CASE WHEN side = 'BUY' THEN -quantity * price 
             ELSE quantity * price END
    ) STORED
);

CREATE INDEX idx_trades_asset ON trades(asset);
CREATE INDEX idx_trades_executed_at ON trades(executed_at DESC);
CREATE INDEX idx_trades_strategy ON trades(strategy);
CREATE INDEX idx_trades_source_platform ON trades(source_platform);

-- ============================================
-- POSITIONS
-- Computed from trades - current holdings
-- ============================================
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    asset VARCHAR(20) NOT NULL UNIQUE,
    quantity DECIMAL(20, 8) NOT NULL,
    avg_entry_price DECIMAL(20, 8),
    total_cost_basis DECIMAL(20, 8),
    first_entry_date TIMESTAMPTZ,
    last_trade_date TIMESTAMPTZ,
    number_of_trades INT,
    
    -- Live data (updated by job)
    current_price DECIMAL(20, 8),
    current_value DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    unrealized_pnl_pct DECIMAL(10, 4),
    
    -- Classification
    position_type VARCHAR(20),                -- core, trading, speculative
    target_allocation_pct DECIMAL(10, 4)
);

CREATE INDEX idx_positions_asset ON positions(asset);

-- ============================================
-- CLOSED POSITIONS
-- Historical closed trades with P&L
-- ============================================
CREATE TABLE closed_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    asset VARCHAR(20) NOT NULL,
    
    -- Entry
    entry_date TIMESTAMPTZ,
    avg_entry_price DECIMAL(20, 8),
    total_bought DECIMAL(20, 8),
    entry_cost_basis DECIMAL(20, 8),
    
    -- Exit
    exit_date TIMESTAMPTZ,
    avg_exit_price DECIMAL(20, 8),
    total_sold DECIMAL(20, 8),
    exit_proceeds DECIMAL(20, 8),
    
    -- P&L
    realized_pnl DECIMAL(20, 8),
    realized_pnl_pct DECIMAL(10, 4),
    
    -- Stats
    holding_period_days INT,
    number_of_trades INT,
    
    -- Classification
    strategy VARCHAR(50),
    win_loss VARCHAR(10)                      -- win, loss, breakeven
);

CREATE INDEX idx_closed_positions_exit_date ON closed_positions(exit_date DESC);
CREATE INDEX idx_closed_positions_strategy ON closed_positions(strategy);

-- ============================================
-- JOURNAL ENTRIES
-- Daily trading reflections
-- ============================================
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    entry_date DATE NOT NULL UNIQUE,          -- One per day
    
    -- Pre-market
    market_outlook TEXT,                      -- What do I expect today?
    planned_actions TEXT,                     -- What will I do?
    risk_appetite VARCHAR(20),                -- aggressive, normal, defensive
    
    -- End of day
    what_happened TEXT,                       -- What actually happened
    what_went_well TEXT,
    what_went_poorly TEXT,
    lessons_learned TEXT,
    
    -- Emotional state
    emotional_state VARCHAR(20),              -- calm, anxious, greedy, fearful, neutral
    energy_level INT CHECK (energy_level BETWEEN 1 AND 5),
    focus_level INT CHECK (focus_level BETWEEN 1 AND 5),
    
    -- Links
    trade_ids UUID[],                         -- Trades made today
    principle_violations UUID[]               -- Rules I broke
);

CREATE INDEX idx_journal_entries_date ON journal_entries(entry_date DESC);

-- ============================================
-- PRINCIPLES
-- Trading rules and beliefs
-- ============================================
CREATE TABLE principles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50),                     -- risk, entry, exit, sizing, psychology
    
    -- Rule specifics
    rule_type VARCHAR(20),                    -- hard (never break), soft (guideline)
    quantifiable BOOLEAN DEFAULT FALSE,
    metric VARCHAR(100),                      -- e.g., "max_position_size_pct"
    threshold DECIMAL(20, 8),                 -- e.g., 5.0 (for 5%)
    
    -- Tracking
    times_followed INT DEFAULT 0,
    times_violated INT DEFAULT 0,
    last_violated_at TIMESTAMPTZ,
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 5                    -- 1-10, higher = more important
);

CREATE INDEX idx_principles_category ON principles(category);
CREATE INDEX idx_principles_active ON principles(active);

-- ============================================
-- CHECKLISTS
-- Pre-trade verification
-- ============================================
CREATE TABLE checklists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    checklist_type VARCHAR(30),               -- pre_trade, position_review, exit
    
    -- Items stored as JSONB for flexibility
    items JSONB NOT NULL,                     -- [{text, required, category}]
    
    active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- POST MORTEMS
-- Detailed trade analysis
-- ============================================
CREATE TABLE post_mortems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Link to trade(s)
    trade_ids UUID[] NOT NULL,                -- Can cover multiple related trades
    asset VARCHAR(20) NOT NULL,
    
    -- Outcome
    result VARCHAR(20),                       -- win, loss, breakeven
    pnl DECIMAL(20, 8),
    pnl_pct DECIMAL(10, 4),
    
    -- Analysis
    entry_quality INT CHECK (entry_quality BETWEEN 1 AND 5),
    exit_quality INT CHECK (exit_quality BETWEEN 1 AND 5),
    sizing_quality INT CHECK (sizing_quality BETWEEN 1 AND 5),
    thesis_quality INT CHECK (thesis_quality BETWEEN 1 AND 5),
    
    -- Reflection
    what_went_well TEXT,
    what_went_poorly TEXT,
    would_do_differently TEXT,
    key_lesson TEXT,
    
    -- Pattern identification
    emotional_factors VARCHAR(50)[],          -- fomo, fear, greed, patience, impatience
    execution_errors VARCHAR(50)[],           -- early_entry, late_exit, oversized, undersized
    
    -- Links to principles
    principles_followed UUID[],
    principles_violated UUID[],
    
    -- AI coach feedback
    ai_feedback TEXT,
    ai_generated_at TIMESTAMPTZ
);

CREATE INDEX idx_post_mortems_asset ON post_mortems(asset);
CREATE INDEX idx_post_mortems_result ON post_mortems(result);

-- ============================================
-- PATTERNS
-- Recurring behaviors identified by AI
-- ============================================
CREATE TABLE patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    pattern_type VARCHAR(30),                 -- strength, weakness, neutral
    category VARCHAR(50),                     -- timing, sizing, emotion, entry, exit
    
    -- Evidence
    supporting_trade_ids UUID[],
    occurrence_count INT DEFAULT 1,
    first_identified_at TIMESTAMPTZ,
    last_occurred_at TIMESTAMPTZ,
    
    -- Impact
    estimated_pnl_impact DECIMAL(20, 8),      -- How much this pattern costs/earns
    severity VARCHAR(20),                     -- critical, high, medium, low
    
    -- Status
    acknowledged BOOLEAN DEFAULT FALSE,
    being_addressed BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE,
    
    -- AI metadata
    ai_identified BOOLEAN DEFAULT TRUE,
    confidence_score DECIMAL(5, 4)            -- 0-1
);

CREATE INDEX idx_patterns_type ON patterns(pattern_type);
CREATE INDEX idx_patterns_category ON patterns(category);

-- ============================================
-- EXECUTION COACH SESSIONS
-- AI coaching conversation history
-- ============================================
CREATE TABLE coach_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    session_type VARCHAR(30),                 -- pre_trade, post_trade, weekly_review, ad_hoc
    
    -- Context
    trade_ids UUID[],
    position_snapshot JSONB,                  -- Portfolio state at session time
    
    -- Conversation
    messages JSONB NOT NULL,                  -- [{role, content, timestamp}]
    
    -- Outcomes
    key_insights TEXT[],
    action_items TEXT[],
    principles_reinforced UUID[],
    
    -- Metadata
    model_used VARCHAR(100),
    tokens_used INT
);

CREATE INDEX idx_coach_sessions_type ON coach_sessions(session_type);
CREATE INDEX idx_coach_sessions_created ON coach_sessions(created_at DESC);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER update_trades_updated_at
    BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_journal_entries_updated_at
    BEFORE UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_principles_updated_at
    BEFORE UPDATE ON principles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_patterns_updated_at
    BEFORE UPDATE ON patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- RLS POLICIES
-- Single user, but good practice
-- ============================================
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE closed_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE principles ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklists ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_mortems ENABLE ROW LEVEL SECURITY;
ALTER TABLE patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE coach_sessions ENABLE ROW LEVEL SECURITY;

-- For now, allow all authenticated (anon key) access
-- Can tighten later if needed
CREATE POLICY "Allow all" ON trades FOR ALL USING (true);
CREATE POLICY "Allow all" ON positions FOR ALL USING (true);
CREATE POLICY "Allow all" ON closed_positions FOR ALL USING (true);
CREATE POLICY "Allow all" ON journal_entries FOR ALL USING (true);
CREATE POLICY "Allow all" ON principles FOR ALL USING (true);
CREATE POLICY "Allow all" ON checklists FOR ALL USING (true);
CREATE POLICY "Allow all" ON post_mortems FOR ALL USING (true);
CREATE POLICY "Allow all" ON patterns FOR ALL USING (true);
CREATE POLICY "Allow all" ON coach_sessions FOR ALL USING (true);
