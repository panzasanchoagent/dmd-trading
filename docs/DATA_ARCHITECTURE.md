# Trigger - Data Architecture

## Overview

Trigger uses a **dual-database architecture**:
- **Personal DB** (read/write): All trading data you own and control
- **Arete DB** (read-only): Market data and research context only

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TRIGGER DATA FLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐        ┌──────────────────────┐          │
│  │    PERSONAL DB       │        │      ARETE DB        │          │
│  │    (Read/Write)      │        │    (Read-Only)       │          │
│  ├──────────────────────┤        ├──────────────────────┤          │
│  │ • starting_positions │        │ • cmc_asset_data     │ ← Prices │
│  │ • trades             │        │ • stock_ohlcv        │          │
│  │ • asset_mapping      │        │ • notes              │ ← Research│
│  │ • journal_entries    │        │ • theses             │          │
│  │ • principles         │        │ • predictions        │          │
│  │ • post_mortems       │        │ • note_topics        │          │
│  │ • coach_sessions     │        │ • note_links         │          │
│  │ • patterns           │        └──────────────────────┘          │
│  └──────────────────────┘                                           │
│            │                              │                          │
│            └──────────────┬───────────────┘                          │
│                           ▼                                          │
│                  ┌─────────────────┐                                 │
│                  │ TRIGGER BACKEND │                                 │
│                  │ (Computes NAV,  │                                 │
│                  │  positions,     │                                 │
│                  │  attribution)   │                                 │
│                  └─────────────────┘                                 │
│                           │                                          │
│                           ▼                                          │
│                  ┌─────────────────┐                                 │
│                  │ TRIGGER FRONTEND│                                 │
│                  │ (Charts, Tables)│                                 │
│                  └─────────────────┘                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Arete DB - Allowed Tables (READ ONLY)

⚠️ **STRICT ALLOWLIST** — Trigger may ONLY read from these tables:

### Price Data
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `cmc_asset_data` | Crypto prices (daily) | `symbol`, `date`, `price`, `market_cap`, `volume` |
| `stock_ohlcv` | Stocks, commodities, ETFs | `symbol`, `date`, `open`, `high`, `low`, `close`, `volume` |

### Research Context
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `notes` | Research notes | `id`, `title`, `content`, `created_at`, `topics` |
| `theses` | Investment theses | `id`, `asset`, `thesis`, `conviction`, `status` |
| `predictions` | Market predictions | `id`, `prediction`, `target_date`, `outcome` |
| `note_topics` | Topic tags | `note_id`, `topic` |
| `note_links` | Note connections | `source_id`, `target_id` |

### ❌ NEVER READ FROM:
- `arete_liquid_trades` — Arete's trades, not yours
- `arete_portfolio_starting_positions` — Arete's positions
- `app_users` — User data
- Any `arete_*` prefixed table (except if explicitly added above)
- Any quantitative/proprietary tables

---

## Personal DB - Tables (READ/WRITE)

### Core Portfolio Tables

#### `starting_positions`
Initial portfolio snapshot. This is your baseline — trades are applied on top.

```sql
CREATE TABLE starting_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Position info
    asset VARCHAR(20) NOT NULL,           -- 'BTC', 'ETH', 'AAPL', 'Cash'
    quantity DECIMAL(20, 8) NOT NULL,     -- Units held
    avg_entry_price DECIMAL(20, 8),       -- Your cost basis per unit
    snapshot_date DATE NOT NULL,          -- Date this snapshot represents
    
    -- Optional
    cost_basis_usd DECIMAL(20, 2),        -- Total cost basis (computed)
    notes TEXT,
    
    UNIQUE(asset, snapshot_date)
);
```

#### `trades`
All trades from any source (manual, IBKR, Hyperliquid, etc.)

```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Core trade data
    asset VARCHAR(20) NOT NULL,           -- 'BTC', 'AAPL', 'GLD'
    side VARCHAR(10) NOT NULL,            -- 'BUY' or 'SELL'
    quantity DECIMAL(20, 8) NOT NULL,     -- Units traded
    price DECIMAL(20, 8) NOT NULL,        -- Execution price
    quote_currency VARCHAR(10) DEFAULT 'USD',
    executed_at TIMESTAMPTZ NOT NULL,     -- When trade occurred
    
    -- Cash flow (computed: side=BUY → negative, side=SELL → positive)
    cash_flow DECIMAL(20, 2),
    
    -- Trade metadata
    trade_type VARCHAR(20),               -- 'entry', 'add', 'trim', 'exit', 'stop_loss'
    strategy VARCHAR(50),                 -- 'thesis_driven', 'momentum', 'scalp'
    timeframe VARCHAR(20),                -- 'day_trade', 'swing', 'position'
    
    -- Risk management
    planned_entry DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    position_size_pct DECIMAL(5, 2),      -- % of portfolio
    
    -- Context
    entry_rationale TEXT,
    thesis_id UUID,                       -- Link to thesis
    source VARCHAR(50),                   -- 'manual', 'ibkr', 'hyperliquid'
    source_trade_id VARCHAR(100),         -- External reference
    
    -- Fees
    commission DECIMAL(20, 8) DEFAULT 0,
    fees DECIMAL(20, 8) DEFAULT 0,
    
    -- Tags
    tags TEXT[]
);

CREATE INDEX idx_trades_asset ON trades(asset);
CREATE INDEX idx_trades_executed_at ON trades(executed_at);
```

#### `asset_mapping`
Categorization for allocation analysis.

```sql
CREATE TABLE asset_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    asset VARCHAR(20) NOT NULL UNIQUE,    -- 'BTC', 'AAPL', 'GLD'
    asset_class VARCHAR(50) NOT NULL,     -- 'Crypto', 'Stocks', 'Commodities', 'Cash'
    sector VARCHAR(50) NOT NULL,          -- 'DeFi', 'AI Equities', 'Precious Metals'
    
    -- Optional metadata
    full_name VARCHAR(200),               -- 'Bitcoin', 'Apple Inc.'
    description TEXT,
    coingecko_id VARCHAR(100),            -- For API lookups
    yahoo_ticker VARCHAR(20),             -- For stock data
    
    is_active BOOLEAN DEFAULT TRUE
);
```

**Asset Class Values:**
- `Crypto`
- `Stocks`
- `Commodities`
- `Cash`

**Sector Values:**
- `DeFi`
- `Decentralised AI`
- `Crypto Majors`
- `Crypto Equities`
- `AI Equities`
- `Financials`
- `Energy`
- `Precious Metals`
- `Commodity Miners`
- `Stablecoin`
- `USD`

### Supporting Tables

#### `journal_entries`
Daily trading journal.

```sql
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    entry_date DATE NOT NULL UNIQUE,
    
    -- Pre-market
    market_outlook TEXT,
    planned_actions TEXT,
    risk_appetite VARCHAR(20),            -- 'aggressive', 'normal', 'defensive'
    
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
```

#### `principles`
Trading rules and principles.

```sql
CREATE TABLE principles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50),                 -- 'risk', 'entry', 'exit', 'sizing', 'psychology'
    rule_type VARCHAR(20) DEFAULT 'soft', -- 'hard', 'soft'
    
    -- Quantifiable rules
    quantifiable BOOLEAN DEFAULT FALSE,
    metric VARCHAR(100),                  -- e.g., 'max_position_size_pct'
    threshold DECIMAL(20, 8),             -- e.g., 10 (for 10%)
    
    -- Tracking
    priority INT DEFAULT 5,
    times_followed INT DEFAULT 0,
    times_violated INT DEFAULT 0,
    last_violated_at TIMESTAMPTZ,
    
    active BOOLEAN DEFAULT TRUE
);
```

#### `post_mortems`
Trade analysis after close.

```sql
CREATE TABLE post_mortems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    trade_ids UUID[] NOT NULL,
    asset VARCHAR(20) NOT NULL,
    
    -- Results
    result VARCHAR(20),                   -- 'win', 'loss', 'breakeven'
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
```

---

## Position Calculation Logic

The core algorithm (replicated from LiquidPortfolioJobs):

```python
def calculate_current_positions(starting_positions, trades, prices):
    """
    Calculate current positions by applying trades to starting positions.
    
    1. Load starting positions (snapshot)
    2. For each trade:
       - BUY: Add quantity, subtract cash
       - SELL: Subtract quantity, add cash
    3. Get current prices
    4. Calculate values and metrics
    """
    
    # Initialize from starting positions
    positions = {}
    for pos in starting_positions:
        positions[pos.asset] = {
            'quantity': pos.quantity,
            'cost_basis': pos.quantity * pos.avg_entry_price,
            'avg_entry': pos.avg_entry_price
        }
    
    # Apply trades chronologically
    for trade in sorted(trades, key=lambda t: t.executed_at):
        asset = trade.asset
        
        if asset not in positions:
            positions[asset] = {'quantity': 0, 'cost_basis': 0, 'avg_entry': 0}
        
        if trade.side == 'BUY':
            # Update average entry price
            old_qty = positions[asset]['quantity']
            old_cost = positions[asset]['cost_basis']
            new_cost = trade.quantity * trade.price
            
            positions[asset]['quantity'] += trade.quantity
            positions[asset]['cost_basis'] += new_cost
            positions[asset]['avg_entry'] = (
                positions[asset]['cost_basis'] / positions[asset]['quantity']
                if positions[asset]['quantity'] > 0 else 0
            )
            
            # Reduce cash
            positions['Cash']['quantity'] -= (trade.quantity * trade.price)
            
        elif trade.side == 'SELL':
            positions[asset]['quantity'] -= trade.quantity
            # Proportionally reduce cost basis
            if positions[asset]['quantity'] > 0:
                positions[asset]['cost_basis'] *= (
                    positions[asset]['quantity'] / 
                    (positions[asset]['quantity'] + trade.quantity)
                )
            else:
                positions[asset]['cost_basis'] = 0
            
            # Add to cash
            positions['Cash']['quantity'] += (trade.quantity * trade.price)
    
    # Get current prices and calculate values
    for asset, pos in positions.items():
        if asset == 'Cash':
            pos['current_price'] = 1.0
        else:
            pos['current_price'] = get_price(asset, prices)
        
        pos['current_value'] = pos['quantity'] * pos['current_price']
        pos['unrealized_pnl'] = pos['current_value'] - pos['cost_basis']
        pos['unrealized_pnl_pct'] = (
            (pos['unrealized_pnl'] / pos['cost_basis'] * 100)
            if pos['cost_basis'] > 0 else 0
        )
    
    return positions
```

---

## Benchmarks

Trigger compares portfolio performance against:

| Benchmark | Source Table | Symbol |
|-----------|--------------|--------|
| Bitcoin | `cmc_asset_data` | `BTC` |
| S&P 500 | `stock_ohlcv` | `SPX` or `SPY` |
| Gold | `stock_ohlcv` | `GLD` |

All benchmarks normalized to 100 at portfolio start date for comparison chart.

---

## Data Flow Summary

```
USER INPUT                    PERSONAL DB                 COMPUTED
───────────                   ──────────                  ────────
                                   │
Starting positions  ───────►  starting_positions
(one-time upload)                  │
                                   │
                                   ▼
Trades              ───────►  trades  ──────────────►  Current Positions
(manual + CSV)                     │                   (quantity per asset)
                                   │
                                   ▼
                              asset_mapping ─────────►  Allocation Breakdown
                                                       (by class/sector)
                                   │
                                   ▼
                              ARETE DB (prices) ─────►  NAV & P&L
                              - cmc_asset_data          - Daily NAV
                              - stock_ohlcv             - Performance attribution
                                                        - Benchmark comparison
```
