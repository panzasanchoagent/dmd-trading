# Trading Journal

Personal trading execution system with AI coaching.

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│     Arete DB        │     │    Personal DB      │
│    (READ only)      │     │   (READ/WRITE)      │
│                     │     │                     │
│  • notes            │     │  • trades           │
│  • theses           │     │  • journal_entries  │
│  • research_items   │     │  • principles       │
│  • tweets           │     │  • post_mortems     │
│  • cmc_asset_data   │     │  • patterns         │
│  • predictions      │     │  • checklists       │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
           └─────────────┬─────────────┘
                         ▼
              ┌─────────────────────┐
              │   Trading Journal   │
              │      Backend        │
              │   (FastAPI:8001)    │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Trading Journal   │
              │      Frontend       │
              │  (Next.js:3001)     │
              └─────────────────────┘
```

## Core Features

### 1. Trade Journal
- Manual trade entry (quick form, minimal friction)
- Entry/exit prices, position size, asset
- Auto-calculate P&L from Arete price data
- Tags: thesis-driven, momentum, scalp, etc.

### 2. Portfolio Accounting
- Current positions with live P&L
- Historical closed positions
- Exposure by asset/sector
- Reconstructed locally from `positions` (starting inventory) + `trades` (transactional deltas)

### 3. Execution Principles
- Codified trading rules
- Pre-trade checklists (position size, risk, thesis)
- Rule violations tracking

### 4. Post-Mortems
- Structured reflection after each trade
- What went well / poorly
- Emotional state, timing, sizing assessment
- Links to relevant notes/theses from Arete

### 5. Pattern Detection
- AI identifies recurring mistakes
- Emotional triggers (FOMO, fear, overconfidence)
- Time-of-day patterns
- Position sizing patterns

### 6. AI Execution Coach
- Reviews trades against principles
- Challenges sizing decisions
- Connects trades to theses
- Identifies pattern violations

## Tech Stack

- **Frontend:** Next.js 14 (App Router)
- **Backend:** FastAPI + Python 3.11
- **Personal DB:** Supabase (separate project)
- **Arete DB:** Supabase (read-only via anon key)
- **AI:** Claude via OpenClaw/Venice

## Ports

| Service | Port |
|---------|------|
| Frontend | 3001 |
| Backend | 8001 |

## Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Windows + OneDrive note

If you open this repo from a OneDrive-synced Windows path, Next.js can crash during startup with `EINVAL ... readlink ... frontend\\.next\\...` on generated files like `interception-route-rewrite-manifest.js`.

The project now auto-cleans `frontend/.next` before `npm run dev`, `npm run build`, or `npm run start` when it detects `Windows + OneDrive`, which clears the immediate stale-artifact failure mode.

That is only a guardrail. The durable fix is to keep the working repo outside OneDrive sync, or mark the whole project as fully local and exclude `.next`/`node_modules` from sync if possible.

## Database

Personal DB schema in `docs/schema.sql`
Arete connection is read-only (uses existing anon key).

### Clarified portfolio architecture

- `positions` = starting positions / opening inventory seed
- `trades` = transactional changes after the seed date
- `/api/portfolio/positions` = reconstructed current holdings from both tables
- `/api/portfolio/closed` = reconstructed historical closed cycles from both tables
- `/api/portfolio/nav-history` = daily NAV, requires local `stock_ohlcv(symbol, date, close)` data

Exact seed SQL template: `docs/sql/starting_positions_template.sql`

### Trade ingestion scripts

```bash
cd backend

# Transform IBKR export to normalized JSON
python scripts/trade_ingestion.py ibkr /path/to/ibkr.csv --output /tmp/ibkr_trades.json

# Transform the manual template format
python scripts/trade_ingestion.py manual scripts/manual_trade_template.csv --output /tmp/manual_trades.json

# Upload normalized trades to the personal Supabase DB
python scripts/upload_trades.py /tmp/ibkr_trades.json
```

If the personal DB has not yet been migrated, apply `docs/migrations/2026-04-08_add_source_platform_to_trades.sql` first.

## Development Status

- [ ] Personal Supabase project setup
- [ ] Backend scaffold
- [ ] Frontend scaffold  
- [ ] Trade entry form
- [ ] Portfolio view (from dashboards logic)
- [ ] Journal entries
- [ ] Principles/checklists
- [ ] Post-mortems
- [ ] AI coach integration
- [ ] Pattern detection
