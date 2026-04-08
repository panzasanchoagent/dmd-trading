# Iteration Log: Trigger Portfolio Flow

**Started:** 2026-04-08
**Target:** Fix backend/frontend portfolio flow, remove remaining dummy behavior, and verify real DB-backed data paths.

---

## Loop 1 — Discovery / reproduction

### Changes Made
- Inspected backend portfolio reconstruction, router endpoints, and frontend portfolio page.
- Queried personal Supabase and Arete data directly.
- Reproduced live API failure on the existing localhost:8001 backend.

### Test Results
- Opened real backend endpoints: ✅
- Real DB data present: ✅
- Existing frontend-facing backend on :8001 failed portfolio fetch: ❌
- Actual trade dates in personal DB are real, not dummy: ✅

### Bugs Found
1. `backend/db.py` reads `os.getenv(...)` directly and never loads `backend/.env`, so portfolio endpoints fail whenever the server starts without exported shell env.
2. Frontend portfolio page fetches `http://localhost:8001/...` directly from the browser instead of using same-origin `/api/...`, making it brittle and easy to break.
3. Portfolio UI only renders open positions, so nav history / closed trades / performance wiring is not exercised end-to-end in the frontend.

### Fixes Applied
- Pending.

### Verification
- Backend works when env vars are manually exported before startup: ✅
- Existing default flow is still broken without that manual step: ✅ reproduced

### Time Spent
- ~20 minutes

---

## Loop 2 — Fixes + verification

### Changes Made
- Updated backend settings loading to resolve `backend/.env` from the file location, not the shell cwd.
- Switched DB clients to read credentials from `config.settings` before falling back to keychain.
- Fixed frontend API usage to hit same-origin `/api/...` routes.
- Fixed Next rewrite so `/api/:path*` correctly proxies to backend `/api/:path*`.
- Rebuilt the portfolio page to consume open positions, closed positions, performance, and NAV history with actual dates.

### Test Results
- Backend portfolio endpoints without manual env export: ✅
- `/api/portfolio/positions`: ✅
- `/api/portfolio/closed`: ✅
- `/api/portfolio/performance`: ✅
- `/api/portfolio/nav-history`: ✅
- Backend regression test (`python -m unittest test_portfolio_fallbacks.py`): ✅

### Bugs Found
1. The previous frontend rewrite dropped the `/api` prefix when proxying.
2. The previous portfolio page only exercised the positions endpoint, so the rest of the portfolio flow was effectively unwired in the UI.

### Fixes Applied
- Fixed env loading and DB credential sourcing.
- Fixed frontend proxy routing and portfolio data fetching.
- Added charts/tables for NAV, closed positions, and performance with real trade dates.

### Verification
- Reconstructed positions now show real `first_entry_date` / `last_trade_date` values from personal DB.
- Closed positions now surface actual `entry_date` / `exit_date` values.
- NAV history is generated end-to-end from seeded positions + trades, with fallback pricing when local `stock_ohlcv` is absent.

### Time Spent
- ~35 minutes
