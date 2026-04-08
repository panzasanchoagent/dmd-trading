"""
Database clients for Trading Journal.
Dual database architecture:
- Personal DB (read/write): trades, journal, principles, patterns, coach sessions
- Arete DB (read-only): market data, theses, notes for context
"""

import os
import subprocess
from functools import lru_cache
from typing import Optional
import logging

from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass


def get_keychain_password(service: str, account: str) -> Optional[str]:
    """Retrieve password from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        logger.warning(f"Failed to retrieve keychain password: {service}/{account}")
        return None


class PersonalDB:
    """
    Personal Supabase database client.
    Read/write access for all trading journal data.
    """
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        if self._client is None:
            url = os.getenv("PERSONAL_SUPABASE_URL", "") or settings.personal_supabase_url
            key = os.getenv("PERSONAL_SUPABASE_KEY", "") or settings.personal_supabase_key
            
            # Try keychain if env vars/settings not set
            if not url or not key:
                url = url or get_keychain_password("supabase-trading-journal", "url") or ""
                key = key or get_keychain_password("supabase-trading-journal-anon", "trading-journal") or ""
            
            if not url or not key:
                raise DatabaseError(
                    "Personal Supabase credentials not found. "
                    "Set PERSONAL_SUPABASE_URL and PERSONAL_SUPABASE_KEY env vars."
                )
            
            self._client = create_client(url, key)
        return self._client
    
    # ============================================
    # TRADES
    # ============================================
    
    async def create_trade(self, trade_data: dict) -> dict:
        """Create a new trade."""
        result = self.client.table("trades").insert(trade_data).execute()
        if not result.data:
            raise DatabaseError("Failed to create trade")
        return result.data[0]
    
    async def get_trade(self, trade_id: str) -> Optional[dict]:
        """Get a single trade by ID."""
        result = self.client.table("trades").select("*").eq("id", trade_id).execute()
        return result.data[0] if result.data else None
    
    async def list_trades(
        self,
        asset: Optional[str] = None,
        strategy: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """List trades with filters."""
        query = self.client.table("trades").select("*")
        
        if asset:
            query = query.eq("asset", asset.upper())
        if strategy:
            query = query.eq("strategy", strategy)
        if start_date:
            query = query.gte("executed_at", start_date)
        if end_date:
            query = query.lte("executed_at", end_date)
        
        result = query.order("executed_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []
    
    async def update_trade(self, trade_id: str, trade_data: dict) -> dict:
        """Update a trade."""
        result = self.client.table("trades").update(trade_data).eq("id", trade_id).execute()
        if not result.data:
            raise DatabaseError(f"Trade not found: {trade_id}")
        return result.data[0]
    
    async def delete_trade(self, trade_id: str) -> bool:
        """Delete a trade."""
        result = self.client.table("trades").delete().eq("id", trade_id).execute()
        return len(result.data) > 0 if result.data else False
    
    async def get_trades_by_ids(self, trade_ids: list) -> list:
        """Get multiple trades by IDs."""
        if not trade_ids:
            return []
        result = self.client.table("trades").select("*").in_("id", trade_ids).execute()
        return result.data or []
    
    async def get_recent_trades(self, days: int = 7, limit: int = 50) -> list:
        """Get recent trades for context."""
        from datetime import datetime, timedelta
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        result = self.client.table("trades").select("*")\
            .gte("executed_at", start_date)\
            .order("executed_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data or []

    async def get_all_trades_for_portfolio(self, limit: int = 5000) -> list:
        """Get all trades needed to rebuild current positions locally."""
        result = self.client.table("trades").select("*")\
            .order("executed_at")\
            .limit(limit)\
            .execute()
        return result.data or []
    
    # ============================================
    # POSITIONS
    # ============================================
    
    async def list_position_seeds(self) -> list:
        """Get seeded starting positions from the local positions table."""
        result = self.client.table("positions").select("*")\
            .gt("quantity", 0)\
            .order("asset")\
            .execute()
        return result.data or []

    async def get_positions(self) -> list:
        """Backward-compatible alias for seeded positions."""
        return await self.list_position_seeds()
    
    async def get_position(self, asset: str) -> Optional[dict]:
        """Get a single position by asset."""
        result = self.client.table("positions").select("*").eq("asset", asset.upper()).execute()
        return result.data[0] if result.data else None
    
    async def upsert_position(self, position_data: dict) -> dict:
        """Insert or update a position."""
        result = self.client.table("positions").upsert(
            position_data, 
            on_conflict="asset"
        ).execute()
        if not result.data:
            raise DatabaseError("Failed to upsert position")
        return result.data[0]
    
    async def get_closed_positions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Get closed positions history."""
        query = self.client.table("closed_positions").select("*")
        
        if start_date:
            query = query.gte("exit_date", start_date)
        if end_date:
            query = query.lte("exit_date", end_date)
        
        result = query.order("exit_date", desc=True).limit(limit).execute()
        return result.data or []
    
    async def create_closed_position(self, position_data: dict) -> dict:
        """Create a closed position record."""
        result = self.client.table("closed_positions").insert(position_data).execute()
        if not result.data:
            raise DatabaseError("Failed to create closed position")
        return result.data[0]

    async def get_stock_price_history(self, assets: list[str], days: int = 90) -> list:
        """Get local daily close history from stock_ohlcv when available."""
        from datetime import datetime, timedelta

        if not assets:
            return []

        start_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
        try:
            result = self.client.table("stock_ohlcv").select("symbol, date, close")\
                .in_("symbol", [asset.upper() for asset in assets])\
                .gte("date", start_date)\
                .order("date")\
                .execute()
            return result.data or []
        except Exception as exc:
            logger.warning("stock_ohlcv unavailable in personal DB: %s", exc)
            return []

    async def get_latest_stock_prices(self, assets: list[str]) -> dict:
        """Get latest local stock close per asset from stock_ohlcv when available."""
        if not assets:
            return {}

        try:
            result = self.client.table("stock_ohlcv").select("symbol, date, close")\
                .in_("symbol", [asset.upper() for asset in assets])\
                .order("date", desc=True)\
                .execute()
        except Exception as exc:
            logger.warning("latest stock_ohlcv unavailable in personal DB: %s", exc)
            return {}

        latest_prices: dict[str, dict] = {}
        for row in result.data or []:
            symbol = (row.get("symbol") or "").upper()
            if symbol and symbol not in latest_prices and row.get("close") is not None:
                latest_prices[symbol] = {
                    "price": float(row["close"]),
                    "date": row.get("date"),
                    "source": "personal_db_stock_ohlcv",
                }
        return latest_prices
    
    # ============================================
    # JOURNAL
    # ============================================
    
    async def upsert_journal_entry(self, entry_data: dict) -> dict:
        """Create or update a journal entry (one per day)."""
        result = self.client.table("journal_entries").upsert(
            entry_data,
            on_conflict="entry_date"
        ).execute()
        if not result.data:
            raise DatabaseError("Failed to upsert journal entry")
        return result.data[0]
    
    async def get_journal_entry(self, entry_date: str) -> Optional[dict]:
        """Get journal entry for a specific date."""
        result = self.client.table("journal_entries").select("*")\
            .eq("entry_date", entry_date).execute()
        return result.data[0] if result.data else None
    
    async def list_journal_entries(self, limit: int = 30, offset: int = 0) -> list:
        """List journal entries."""
        result = self.client.table("journal_entries").select("*")\
            .order("entry_date", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        return result.data or []
    
    async def get_journaling_streak(self) -> dict:
        """Calculate current journaling streak."""
        from datetime import date, timedelta
        
        entries = await self.list_journal_entries(limit=100)
        if not entries:
            return {"current_streak": 0, "longest_streak": 0, "total_entries": 0}
        
        # Get dates as set for O(1) lookup
        entry_dates = {e["entry_date"] for e in entries}
        
        # Calculate current streak
        current_streak = 0
        check_date = date.today()
        
        while str(check_date) in entry_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
        
        # If today missing but yesterday present, check from yesterday
        if current_streak == 0:
            check_date = date.today() - timedelta(days=1)
            while str(check_date) in entry_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
        
        return {
            "current_streak": current_streak,
            "total_entries": len(entries),
            "last_entry": entries[0]["entry_date"] if entries else None
        }
    
    # ============================================
    # PRINCIPLES
    # ============================================
    
    async def create_principle(self, principle_data: dict) -> dict:
        """Create a trading principle."""
        result = self.client.table("principles").insert(principle_data).execute()
        if not result.data:
            raise DatabaseError("Failed to create principle")
        return result.data[0]
    
    async def get_principle(self, principle_id: str) -> Optional[dict]:
        """Get a single principle."""
        result = self.client.table("principles").select("*")\
            .eq("id", principle_id).execute()
        return result.data[0] if result.data else None
    
    async def list_principles(self, active_only: bool = True) -> list:
        """List all trading principles."""
        query = self.client.table("principles").select("*")
        if active_only:
            query = query.eq("active", True)
        result = query.order("priority", desc=True).execute()
        return result.data or []
    
    async def update_principle(self, principle_id: str, principle_data: dict) -> dict:
        """Update a principle."""
        result = self.client.table("principles").update(principle_data)\
            .eq("id", principle_id).execute()
        if not result.data:
            raise DatabaseError(f"Principle not found: {principle_id}")
        return result.data[0]
    
    async def record_principle_event(
        self,
        principle_id: str,
        followed: bool
    ) -> dict:
        """Record a principle follow or violation."""
        principle = await self.get_principle(principle_id)
        if not principle:
            raise DatabaseError(f"Principle not found: {principle_id}")
        
        update_data = {}
        if followed:
            update_data["times_followed"] = principle.get("times_followed", 0) + 1
        else:
            update_data["times_violated"] = principle.get("times_violated", 0) + 1
            update_data["last_violated_at"] = "now()"
        
        return await self.update_principle(principle_id, update_data)
    
    async def get_recent_violations(self, days: int = 30) -> list:
        """Get recently violated principles."""
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        result = self.client.table("principles").select("*")\
            .gte("last_violated_at", cutoff)\
            .order("last_violated_at", desc=True)\
            .execute()
        return result.data or []
    
    # ============================================
    # PATTERNS
    # ============================================
    
    async def create_pattern(self, pattern_data: dict) -> dict:
        """Create a pattern record."""
        result = self.client.table("patterns").insert(pattern_data).execute()
        if not result.data:
            raise DatabaseError("Failed to create pattern")
        return result.data[0]
    
    async def list_patterns(
        self,
        pattern_type: Optional[str] = None,
        category: Optional[str] = None,
        resolved: bool = False
    ) -> list:
        """List patterns with filters."""
        query = self.client.table("patterns").select("*")
        
        if pattern_type:
            query = query.eq("pattern_type", pattern_type)
        if category:
            query = query.eq("category", category)
        
        query = query.eq("resolved", resolved)
        result = query.order("occurrence_count", desc=True).execute()
        return result.data or []
    
    async def update_pattern(self, pattern_id: str, pattern_data: dict) -> dict:
        """Update a pattern."""
        result = self.client.table("patterns").update(pattern_data)\
            .eq("id", pattern_id).execute()
        if not result.data:
            raise DatabaseError(f"Pattern not found: {pattern_id}")
        return result.data[0]
    
    async def get_active_alerts(self) -> list:
        """Get patterns that need attention (unacknowledged weaknesses)."""
        result = self.client.table("patterns").select("*")\
            .eq("pattern_type", "weakness")\
            .eq("acknowledged", False)\
            .eq("resolved", False)\
            .order("severity")\
            .order("occurrence_count", desc=True)\
            .execute()
        return result.data or []
    
    # ============================================
    # COACH SESSIONS
    # ============================================
    
    async def create_coach_session(self, session_data: dict) -> dict:
        """Create a coaching session."""
        result = self.client.table("coach_sessions").insert(session_data).execute()
        if not result.data:
            raise DatabaseError("Failed to create coach session")
        return result.data[0]
    
    async def get_coach_session(self, session_id: str) -> Optional[dict]:
        """Get a coaching session."""
        result = self.client.table("coach_sessions").select("*")\
            .eq("id", session_id).execute()
        return result.data[0] if result.data else None
    
    async def list_coach_sessions(
        self,
        session_type: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """List coaching sessions."""
        query = self.client.table("coach_sessions").select("*")
        if session_type:
            query = query.eq("session_type", session_type)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    
    async def update_coach_session(self, session_id: str, session_data: dict) -> dict:
        """Update a coaching session."""
        result = self.client.table("coach_sessions").update(session_data)\
            .eq("id", session_id).execute()
        if not result.data:
            raise DatabaseError(f"Coach session not found: {session_id}")
        return result.data[0]
    
    # ============================================
    # POST MORTEMS
    # ============================================
    
    async def create_post_mortem(self, pm_data: dict) -> dict:
        """Create a post-mortem analysis."""
        result = self.client.table("post_mortems").insert(pm_data).execute()
        if not result.data:
            raise DatabaseError("Failed to create post-mortem")
        return result.data[0]
    
    async def list_post_mortems(self, limit: int = 20) -> list:
        """List post-mortem analyses."""
        result = self.client.table("post_mortems").select("*")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data or []


class AreteDB:
    """
    Arete Supabase database client.
    Read-only access for market data, theses, and notes.
    """
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        if self._client is None:
            url = os.getenv("ARETE_SUPABASE_URL", "") or settings.arete_supabase_url or "https://goptgqfllyutklnyjvoj.supabase.co"
            key = os.getenv("ARETE_SUPABASE_KEY", "") or settings.arete_supabase_key
            
            # Try keychain if env var/settings not set
            if not key:
                key = get_keychain_password("supabase-arete-anon", "arete") or ""
            
            if not key:
                raise DatabaseError(
                    "Arete Supabase key not found. "
                    "Set ARETE_SUPABASE_KEY env var or add to keychain."
                )
            
            self._client = create_client(url, key)
        return self._client
    
    # ============================================
    # MARKET DATA (read-only)
    # ============================================
    
    async def get_current_prices(self, assets: list) -> dict:
        """Get current prices for assets."""
        symbols = [a.upper() for a in assets]
        
        result = self.client.table("cmc_asset_data").select("symbol, price, date")\
            .in_("symbol", symbols)\
            .order("date", desc=True)\
            .execute()
        
        # Get latest price per symbol
        prices = {}
        for row in result.data or []:
            symbol = row["symbol"]
            if symbol not in prices:
                prices[symbol] = {
                    "price": float(row["price"]),
                    "date": row["date"]
                }
        return prices
    
    async def get_price_at_date(self, asset: str, date_str: str) -> Optional[float]:
        """Get price for asset at a specific date."""
        result = self.client.table("cmc_asset_data").select("price")\
            .eq("symbol", asset.upper())\
            .lte("date", date_str)\
            .order("date", desc=True)\
            .limit(1)\
            .execute()
        
        if result.data:
            return float(result.data[0]["price"])
        return None
    
    async def get_price_history(
        self,
        asset: str,
        days: int = 30
    ) -> list:
        """Get price history for an asset."""
        from datetime import datetime, timedelta
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        result = self.client.table("cmc_asset_data").select("date, price")\
            .eq("symbol", asset.upper())\
            .gte("date", start_date)\
            .order("date")\
            .execute()
        
        return result.data or []
    
    async def get_market_summary(self) -> dict:
        """Get overall market summary (BTC, ETH, total market cap)."""
        prices = await self.get_current_prices(["BTC", "ETH"])
        
        # Get 24h change if available
        btc_history = await self.get_price_history("BTC", days=2)
        eth_history = await self.get_price_history("ETH", days=2)
        
        def calc_change(history: list) -> Optional[float]:
            if len(history) >= 2:
                old = float(history[0]["price"])
                new = float(history[-1]["price"])
                return ((new - old) / old) * 100 if old else None
            return None
        
        return {
            "btc": {
                "price": prices.get("BTC", {}).get("price"),
                "change_24h": calc_change(btc_history)
            },
            "eth": {
                "price": prices.get("ETH", {}).get("price"),
                "change_24h": calc_change(eth_history)
            }
        }
    
    # ============================================
    # THESES (read-only)
    # ============================================
    
    async def get_thesis(self, thesis_id: str) -> Optional[dict]:
        """Get a thesis by ID."""
        result = self.client.table("theses").select("*")\
            .eq("id", thesis_id).execute()
        return result.data[0] if result.data else None
    
    async def get_theses_for_asset(self, asset: str) -> list:
        """Get all theses related to an asset."""
        result = self.client.table("theses").select("*")\
            .ilike("assets", f"%{asset}%")\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        return result.data or []
    
    # ============================================
    # NOTES (read-only)
    # ============================================
    
    async def get_notes(self, note_ids: list) -> list:
        """Get notes by IDs."""
        if not note_ids:
            return []
        result = self.client.table("notes").select("*")\
            .in_("id", note_ids).execute()
        return result.data or []
    
    async def get_recent_notes_for_asset(self, asset: str, limit: int = 10) -> list:
        """Get recent notes mentioning an asset."""
        result = self.client.table("notes").select("*")\
            .ilike("content", f"%{asset}%")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data or []


# Singleton instances
@lru_cache()
def get_personal_db() -> PersonalDB:
    return PersonalDB()


@lru_cache()
def get_arete_db() -> AreteDB:
    return AreteDB()


# Convenience exports
personal_db = get_personal_db()
arete_db = get_arete_db()
