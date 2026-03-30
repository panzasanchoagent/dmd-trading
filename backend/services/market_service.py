"""
Market Service.
Fetches market context from Arete DB for trade correlation.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

from db import arete_db

logger = logging.getLogger(__name__)


class MarketService:
    """
    Provides market context for trading analysis.
    All data sourced from Arete Supabase (read-only).
    """
    
    def __init__(self):
        self.db = arete_db
    
    async def get_current_prices(self, assets: List[str]) -> Dict[str, float]:
        """Get current prices for given assets."""
        prices = await self.db.get_current_prices(assets)
        return {k: v.get("price", 0) for k, v in prices.items()}
    
    async def get_market_summary(self) -> dict:
        """Get overall market summary (BTC, ETH, regime)."""
        summary = await self.db.get_market_summary()
        
        # Determine market regime
        btc_change = summary.get("btc", {}).get("change_24h", 0) or 0
        eth_change = summary.get("eth", {}).get("change_24h", 0) or 0
        avg_change = (btc_change + eth_change) / 2
        
        if avg_change > 5:
            regime = "Bullish (strong)"
        elif avg_change > 2:
            regime = "Bullish"
        elif avg_change > -2:
            regime = "Sideways"
        elif avg_change > -5:
            regime = "Bearish"
        else:
            regime = "Bearish (strong)"
        
        summary["regime"] = regime
        return summary
    
    async def get_context_at_time(
        self,
        timestamp: str,
        assets: List[str] = None
    ) -> dict:
        """Get market context at a specific time."""
        if assets is None:
            assets = ["BTC", "ETH"]
        
        # Parse timestamp
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            dt = timestamp
        
        date_str = dt.strftime("%Y-%m-%d")
        
        context = {}
        for asset in assets:
            price = await self.db.get_price_at_date(asset, date_str)
            context[asset.lower() + "_price"] = price
        
        return context
    
    async def get_trade_market_context(
        self,
        entry_time: str,
        exit_time: str = None
    ) -> dict:
        """Get market context for a trade (entry and optionally exit)."""
        entry_ctx = await self.get_context_at_time(entry_time)
        
        result = {
            "at_entry": entry_ctx
        }
        
        if exit_time:
            exit_ctx = await self.get_context_at_time(exit_time)
            result["at_exit"] = exit_ctx
            
            # Calculate BTC change during hold
            btc_entry = entry_ctx.get("btc_price", 0)
            btc_exit = exit_ctx.get("btc_price", 0)
            if btc_entry and btc_exit:
                result["btc_change_pct"] = ((btc_exit - btc_entry) / btc_entry) * 100
        
        return result
    
    async def get_weekly_market_summary(self) -> dict:
        """Get market performance for the past week."""
        today = datetime.utcnow()
        week_ago = today - timedelta(days=7)
        
        # Get BTC history
        btc_history = await self.db.get_price_history("BTC", days=7)
        eth_history = await self.db.get_price_history("ETH", days=7)
        
        def calc_change(history: list) -> float:
            if len(history) >= 2:
                old = float(history[0]["price"])
                new = float(history[-1]["price"])
                return ((new - old) / old) * 100 if old else 0
            return 0
        
        btc_change = calc_change(btc_history)
        eth_change = calc_change(eth_history)
        
        # Calculate volatility (simplified: range / avg)
        def calc_volatility(history: list) -> str:
            if len(history) < 3:
                return "Unknown"
            prices = [float(h["price"]) for h in history]
            range_pct = (max(prices) - min(prices)) / min(prices) * 100
            if range_pct > 20:
                return "High"
            elif range_pct > 10:
                return "Moderate"
            else:
                return "Low"
        
        # Determine weekly regime
        avg_change = (btc_change + eth_change) / 2
        if avg_change > 10:
            regime = "Strong Rally"
        elif avg_change > 3:
            regime = "Uptrend"
        elif avg_change > -3:
            regime = "Consolidation"
        elif avg_change > -10:
            regime = "Downtrend"
        else:
            regime = "Strong Selloff"
        
        return {
            "btc_weekly_change": btc_change,
            "eth_weekly_change": eth_change,
            "regime": regime,
            "volatility": calc_volatility(btc_history)
        }
    
    async def get_context_for_asset(self, asset: str) -> dict:
        """Get comprehensive market context for a specific asset."""
        # Get current price
        prices = await self.db.get_current_prices([asset, "BTC", "ETH"])
        
        # Get price history for trend
        history = await self.db.get_price_history(asset, days=7)
        btc_history = await self.db.get_price_history("BTC", days=7)
        
        # Calculate changes
        def calc_change(hist: list) -> float:
            if len(hist) >= 2:
                old = float(hist[0]["price"])
                new = float(hist[-1]["price"])
                return ((new - old) / old) * 100 if old else 0
            return 0
        
        asset_change = calc_change(history)
        btc_change = calc_change(btc_history)
        
        # Determine trend
        if asset_change > 10:
            trend = "Strong uptrend"
        elif asset_change > 3:
            trend = "Uptrend"
        elif asset_change > -3:
            trend = "Sideways"
        elif asset_change > -10:
            trend = "Downtrend"
        else:
            trend = "Strong downtrend"
        
        return {
            "asset": asset,
            "current_price": prices.get(asset, {}).get("price"),
            "7d_change_pct": asset_change,
            "btc_7d_change_pct": btc_change,
            "trend": trend,
            "btc_price": prices.get("BTC", {}).get("price"),
            "eth_price": prices.get("ETH", {}).get("price"),
            "vs_btc": "outperforming" if asset_change > btc_change else "underperforming"
        }
    
    async def get_weekly_summary(self) -> dict:
        """Alias for get_weekly_market_summary."""
        return await self.get_weekly_market_summary()
    
    async def get_thesis_context(self, asset: str) -> List[dict]:
        """Get relevant theses for an asset from Arete DB."""
        theses = await self.db.get_theses_for_asset(asset)
        
        # Format for context injection
        formatted = []
        for t in theses:
            formatted.append({
                "id": t.get("id"),
                "title": t.get("title"),
                "summary": t.get("summary", "")[:500],
                "status": t.get("status"),
                "created": t.get("created_at")
            })
        
        return formatted
    
    async def correlate_trade_with_market(
        self,
        trade: dict
    ) -> dict:
        """
        Analyze how a trade correlated with market conditions.
        Did the trader trade with or against the trend?
        """
        entry_time = trade.get("entry_time") or trade.get("executed_at")
        exit_time = trade.get("exit_time")
        
        if not entry_time:
            return {"correlation": "unknown", "reason": "No entry time"}
        
        market_ctx = await self.get_trade_market_context(entry_time, exit_time)
        
        btc_change = market_ctx.get("btc_change_pct", 0)
        trade_pnl_pct = float(trade.get("pnl_pct", 0) or 0)
        side = trade.get("side", "BUY").upper()
        
        # Determine correlation
        if side == "BUY":
            # Long position
            if btc_change > 5 and trade_pnl_pct > 0:
                correlation = "with_trend"
                reason = "Long during bull market - rode the wave"
            elif btc_change < -5 and trade_pnl_pct < 0:
                correlation = "against_trend"
                reason = "Long during bear market - fought the trend"
            elif btc_change > 5 and trade_pnl_pct < 0:
                correlation = "underperformed"
                reason = "Lost money in a bull market"
            else:
                correlation = "neutral"
                reason = "Market was sideways"
        else:
            # Short position
            if btc_change < -5 and trade_pnl_pct > 0:
                correlation = "with_trend"
                reason = "Short during bear market - rode the wave"
            elif btc_change > 5 and trade_pnl_pct < 0:
                correlation = "against_trend"
                reason = "Short during bull market - fought the trend"
            else:
                correlation = "neutral"
                reason = "Market was sideways"
        
        return {
            "correlation": correlation,
            "reason": reason,
            "btc_change_pct": btc_change,
            "trade_pnl_pct": trade_pnl_pct,
            "market_context": market_ctx
        }


# Singleton
_market_service: Optional[MarketService] = None


def get_market_service() -> MarketService:
    global _market_service
    if _market_service is None:
        _market_service = MarketService()
    return _market_service
