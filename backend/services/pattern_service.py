"""
Pattern Detection Service.
THE MOST IMPORTANT feature - identifies recurring trading behaviors.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from collections import defaultdict
from decimal import Decimal
import statistics
import logging

from db import personal_db, arete_db

logger = logging.getLogger(__name__)


class PatternService:
    """
    Detects and tracks recurring trading patterns.
    
    Pattern Categories:
    - timing: day of week, time of day patterns
    - sizing: position size vs outcome correlations
    - emotion: FOMO, revenge trading, fear indicators
    - entry: entry quality patterns
    - exit: exit quality patterns (holding too long/short)
    - market: correlation with market conditions
    """
    
    def __init__(self):
        self.db = personal_db
        self.arete = arete_db
    
    # ============================================
    # TIMING PATTERNS
    # ============================================
    
    async def analyze_day_of_week(self, trades: List[dict]) -> List[dict]:
        """
        Analyze win rate by day of week.
        Alert: "4/5 Monday entries were losers"
        """
        if len(trades) < 10:
            return []
        
        day_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0})
        
        for t in trades:
            executed_at = t.get("executed_at")
            if isinstance(executed_at, str):
                executed_at = datetime.fromisoformat(executed_at.replace("Z", "+00:00"))
            
            day_name = executed_at.strftime("%A")
            pnl = float(t.get("pnl", 0) or 0)
            
            if pnl > 0:
                day_stats[day_name]["wins"] += 1
            elif pnl < 0:
                day_stats[day_name]["losses"] += 1
            day_stats[day_name]["total_pnl"] += pnl
        
        patterns = []
        for day, stats in day_stats.items():
            total = stats["wins"] + stats["losses"]
            if total >= 3:  # Minimum sample
                win_rate = stats["wins"] / total * 100
                
                # Flag if significantly below average
                if win_rate < 35:
                    patterns.append({
                        "name": f"Weak {day} Performance",
                        "description": f"{stats['losses']}/{total} {day} trades were losers ({win_rate:.0f}% win rate)",
                        "pattern_type": "weakness",
                        "category": "timing",
                        "severity": "high" if total >= 5 else "medium",
                        "occurrence_count": total,
                        "estimated_pnl_impact": stats["total_pnl"],
                        "metadata": {
                            "day": day,
                            "win_rate": win_rate,
                            "total_trades": total
                        }
                    })
                
                # Also flag strong days
                elif win_rate > 70 and total >= 5:
                    patterns.append({
                        "name": f"Strong {day} Performance",
                        "description": f"{stats['wins']}/{total} {day} trades were winners ({win_rate:.0f}% win rate)",
                        "pattern_type": "strength",
                        "category": "timing",
                        "severity": "low",
                        "occurrence_count": total,
                        "estimated_pnl_impact": stats["total_pnl"],
                        "metadata": {
                            "day": day,
                            "win_rate": win_rate,
                            "total_trades": total
                        }
                    })
        
        return patterns
    
    async def analyze_time_of_day(self, trades: List[dict]) -> List[dict]:
        """Analyze performance by time of day (morning/afternoon/evening)."""
        if len(trades) < 10:
            return []
        
        time_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0})
        
        for t in trades:
            executed_at = t.get("executed_at")
            if isinstance(executed_at, str):
                executed_at = datetime.fromisoformat(executed_at.replace("Z", "+00:00"))
            
            hour = executed_at.hour
            if 6 <= hour < 12:
                period = "Morning (6-12)"
            elif 12 <= hour < 18:
                period = "Afternoon (12-18)"
            else:
                period = "Evening/Night (18-6)"
            
            pnl = float(t.get("pnl", 0) or 0)
            if pnl > 0:
                time_stats[period]["wins"] += 1
            elif pnl < 0:
                time_stats[period]["losses"] += 1
            time_stats[period]["total_pnl"] += pnl
        
        patterns = []
        for period, stats in time_stats.items():
            total = stats["wins"] + stats["losses"]
            if total >= 5:
                win_rate = stats["wins"] / total * 100
                
                if win_rate < 35:
                    patterns.append({
                        "name": f"Weak {period} Trading",
                        "description": f"Only {win_rate:.0f}% win rate during {period.lower()} hours",
                        "pattern_type": "weakness",
                        "category": "timing",
                        "severity": "medium",
                        "occurrence_count": total,
                        "estimated_pnl_impact": stats["total_pnl"],
                        "metadata": {"period": period, "win_rate": win_rate}
                    })
        
        return patterns
    
    # ============================================
    # SIZING PATTERNS
    # ============================================
    
    async def analyze_position_sizing(self, trades: List[dict]) -> List[dict]:
        """
        Analyze correlation between position size and outcomes.
        Alert: "Win rate drops 35% when position >5%"
        """
        patterns = []
        
        # Group by position size buckets
        size_buckets = {
            "small (<2%)": [],
            "medium (2-5%)": [],
            "large (5-10%)": [],
            "oversized (>10%)": []
        }
        
        for t in trades:
            size_pct = float(t.get("position_size_pct", 0) or 0)
            pnl = float(t.get("pnl", 0) or 0)
            
            if size_pct < 2:
                size_buckets["small (<2%)"].append(pnl)
            elif size_pct < 5:
                size_buckets["medium (2-5%)"].append(pnl)
            elif size_pct < 10:
                size_buckets["large (5-10%)"].append(pnl)
            else:
                size_buckets["oversized (>10%)"].append(pnl)
        
        # Calculate win rates per bucket
        bucket_stats = {}
        for bucket, pnls in size_buckets.items():
            if len(pnls) >= 3:
                wins = sum(1 for p in pnls if p > 0)
                losses = sum(1 for p in pnls if p < 0)
                total = wins + losses
                if total > 0:
                    bucket_stats[bucket] = {
                        "win_rate": wins / total * 100,
                        "count": total,
                        "total_pnl": sum(pnls)
                    }
        
        # Compare large/oversized to smaller positions
        baseline_wr = None
        for bucket in ["small (<2%)", "medium (2-5%)"]:
            if bucket in bucket_stats:
                if baseline_wr is None:
                    baseline_wr = bucket_stats[bucket]["win_rate"]
                else:
                    baseline_wr = (baseline_wr + bucket_stats[bucket]["win_rate"]) / 2
        
        if baseline_wr is not None:
            for bucket in ["large (5-10%)", "oversized (>10%)"]:
                if bucket in bucket_stats:
                    stats = bucket_stats[bucket]
                    drop = baseline_wr - stats["win_rate"]
                    
                    if drop > 20 and stats["count"] >= 3:
                        patterns.append({
                            "name": "Win Rate Drops with Size",
                            "description": f"Win rate drops {drop:.0f}% when position is {bucket}",
                            "pattern_type": "weakness",
                            "category": "sizing",
                            "severity": "high" if drop > 30 else "medium",
                            "occurrence_count": stats["count"],
                            "estimated_pnl_impact": stats["total_pnl"],
                            "metadata": {
                                "bucket": bucket,
                                "bucket_win_rate": stats["win_rate"],
                                "baseline_win_rate": baseline_wr,
                                "drop_pct": drop
                            }
                        })
        
        return patterns
    
    # ============================================
    # EMOTIONAL PATTERNS
    # ============================================
    
    async def detect_revenge_trades(self, trades: List[dict]) -> List[dict]:
        """
        Detect revenge trading (entry within 2 hours after a loss).
        Alert: "Revenge trades (entry <2h after loss): 20% win rate"
        """
        patterns = []
        
        # Sort by execution time
        sorted_trades = sorted(
            trades,
            key=lambda t: t.get("executed_at", "")
        )
        
        revenge_trades = []
        for i, trade in enumerate(sorted_trades):
            if i == 0:
                continue
            
            prev_trade = sorted_trades[i - 1]
            prev_pnl = float(prev_trade.get("pnl", 0) or 0)
            
            # Check if previous trade was a loss
            if prev_pnl >= 0:
                continue
            
            # Parse timestamps
            try:
                prev_time = datetime.fromisoformat(
                    prev_trade.get("executed_at", "").replace("Z", "+00:00")
                )
                curr_time = datetime.fromisoformat(
                    trade.get("executed_at", "").replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                continue
            
            # Check if entry within 2 hours of loss
            time_diff = (curr_time - prev_time).total_seconds() / 3600
            if time_diff <= 2:
                revenge_trades.append(trade)
        
        if len(revenge_trades) >= 3:
            wins = sum(1 for t in revenge_trades if float(t.get("pnl", 0) or 0) > 0)
            losses = len(revenge_trades) - wins
            total_pnl = sum(float(t.get("pnl", 0) or 0) for t in revenge_trades)
            win_rate = wins / len(revenge_trades) * 100
            
            if win_rate < 40:  # Below baseline
                patterns.append({
                    "name": "Revenge Trading",
                    "description": f"Trades within 2h of a loss: {win_rate:.0f}% win rate ({wins}/{len(revenge_trades)})",
                    "pattern_type": "weakness",
                    "category": "emotion",
                    "severity": "critical" if win_rate < 25 else "high",
                    "occurrence_count": len(revenge_trades),
                    "estimated_pnl_impact": total_pnl,
                    "supporting_trade_ids": [t.get("id") for t in revenge_trades],
                    "metadata": {
                        "win_rate": win_rate,
                        "total_trades": len(revenge_trades)
                    }
                })
        
        return patterns
    
    async def detect_fomo_entries(self, trades: List[dict]) -> List[dict]:
        """
        Detect FOMO entries (buying after large price moves).
        Requires market data correlation.
        """
        patterns = []
        fomo_trades = []
        
        for t in trades:
            if t.get("side") != "BUY":
                continue
            
            # Check tags for FOMO indicator
            tags = t.get("tags", []) or []
            if "fomo" in [tag.lower() for tag in tags]:
                fomo_trades.append(t)
                continue
            
            # Could add price momentum check here with market data
        
        if len(fomo_trades) >= 3:
            wins = sum(1 for t in fomo_trades if float(t.get("pnl", 0) or 0) > 0)
            total_pnl = sum(float(t.get("pnl", 0) or 0) for t in fomo_trades)
            win_rate = wins / len(fomo_trades) * 100 if fomo_trades else 0
            
            patterns.append({
                "name": "FOMO Entries",
                "description": f"Trades tagged as FOMO: {win_rate:.0f}% win rate",
                "pattern_type": "weakness",
                "category": "emotion",
                "severity": "high" if win_rate < 35 else "medium",
                "occurrence_count": len(fomo_trades),
                "estimated_pnl_impact": total_pnl,
                "supporting_trade_ids": [t.get("id") for t in fomo_trades]
            })
        
        return patterns
    
    # ============================================
    # EXIT PATTERNS
    # ============================================
    
    async def analyze_holding_period(self, trades: List[dict]) -> List[dict]:
        """
        Analyze holding period vs planned holding period.
        Alert: "Winners held avg 3 days vs planned 7"
        """
        patterns = []
        
        # Separate winners and losers with holding periods
        winners = []
        losers = []
        
        for t in trades:
            pnl = float(t.get("pnl", 0) or 0)
            # Estimate holding period from entry/exit if available
            holding_days = t.get("holding_period_days")
            
            if holding_days is not None:
                if pnl > 0:
                    winners.append(holding_days)
                elif pnl < 0:
                    losers.append(holding_days)
        
        if len(winners) >= 5 and len(losers) >= 5:
            avg_winner_hold = statistics.mean(winners)
            avg_loser_hold = statistics.mean(losers)
            
            # Alert if holding losers longer than winners
            if avg_loser_hold > avg_winner_hold * 1.5:
                patterns.append({
                    "name": "Holding Losers Too Long",
                    "description": f"Avg loser held {avg_loser_hold:.1f} days vs winners {avg_winner_hold:.1f} days",
                    "pattern_type": "weakness",
                    "category": "exit",
                    "severity": "high",
                    "occurrence_count": len(losers),
                    "metadata": {
                        "avg_winner_hold": avg_winner_hold,
                        "avg_loser_hold": avg_loser_hold
                    }
                })
            
            # Alert if cutting winners early
            if avg_winner_hold < 3:  # Less than 3 days
                patterns.append({
                    "name": "Cutting Winners Early",
                    "description": f"Average winner held only {avg_winner_hold:.1f} days",
                    "pattern_type": "weakness",
                    "category": "exit",
                    "severity": "medium",
                    "occurrence_count": len(winners),
                    "metadata": {"avg_winner_hold": avg_winner_hold}
                })
        
        return patterns
    
    # ============================================
    # STRATEGY PATTERNS
    # ============================================
    
    async def analyze_by_strategy(self, trades: List[dict]) -> List[dict]:
        """Analyze performance by trading strategy."""
        patterns = []
        
        strategy_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0})
        
        for t in trades:
            strategy = t.get("strategy", "untagged") or "untagged"
            pnl = float(t.get("pnl", 0) or 0)
            
            if pnl > 0:
                strategy_stats[strategy]["wins"] += 1
            elif pnl < 0:
                strategy_stats[strategy]["losses"] += 1
            strategy_stats[strategy]["total_pnl"] += pnl
        
        for strategy, stats in strategy_stats.items():
            total = stats["wins"] + stats["losses"]
            if total >= 5:
                win_rate = stats["wins"] / total * 100
                
                # Flag underperforming strategies
                if win_rate < 35 and stats["total_pnl"] < 0:
                    patterns.append({
                        "name": f"Weak Strategy: {strategy}",
                        "description": f"{strategy} strategy: {win_rate:.0f}% win rate, ${stats['total_pnl']:,.2f} P&L",
                        "pattern_type": "weakness",
                        "category": "strategy",
                        "severity": "high",
                        "occurrence_count": total,
                        "estimated_pnl_impact": stats["total_pnl"],
                        "metadata": {
                            "strategy": strategy,
                            "win_rate": win_rate
                        }
                    })
                
                # Flag strong strategies
                elif win_rate > 60 and stats["total_pnl"] > 0:
                    patterns.append({
                        "name": f"Strong Strategy: {strategy}",
                        "description": f"{strategy} strategy: {win_rate:.0f}% win rate, ${stats['total_pnl']:,.2f} P&L",
                        "pattern_type": "strength",
                        "category": "strategy",
                        "severity": "low",
                        "occurrence_count": total,
                        "estimated_pnl_impact": stats["total_pnl"],
                        "metadata": {
                            "strategy": strategy,
                            "win_rate": win_rate
                        }
                    })
        
        return patterns
    
    # ============================================
    # MASTER ANALYSIS
    # ============================================
    
    async def run_full_analysis(
        self,
        lookback_days: int = 90
    ) -> Dict[str, List[dict]]:
        """
        Run all pattern detection analyses.
        Returns categorized patterns.
        """
        # Get trades for analysis
        trades = await self.db.get_recent_trades(days=lookback_days, limit=500)
        
        if not trades:
            return {"patterns": [], "summary": "No trades to analyze"}
        
        all_patterns = []
        
        # Run all analyses
        all_patterns.extend(await self.analyze_day_of_week(trades))
        all_patterns.extend(await self.analyze_time_of_day(trades))
        all_patterns.extend(await self.analyze_position_sizing(trades))
        all_patterns.extend(await self.detect_revenge_trades(trades))
        all_patterns.extend(await self.detect_fomo_entries(trades))
        all_patterns.extend(await self.analyze_holding_period(trades))
        all_patterns.extend(await self.analyze_by_strategy(trades))
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_patterns.sort(key=lambda p: severity_order.get(p.get("severity", "low"), 4))
        
        # Categorize
        weaknesses = [p for p in all_patterns if p.get("pattern_type") == "weakness"]
        strengths = [p for p in all_patterns if p.get("pattern_type") == "strength"]
        
        # Calculate summary stats
        total_pnl_impact = sum(
            p.get("estimated_pnl_impact", 0) or 0 
            for p in weaknesses
        )
        
        return {
            "patterns": all_patterns,
            "weaknesses": weaknesses,
            "strengths": strengths,
            "summary": {
                "total_patterns": len(all_patterns),
                "weaknesses_count": len(weaknesses),
                "strengths_count": len(strengths),
                "estimated_weakness_pnl_impact": total_pnl_impact,
                "trades_analyzed": len(trades),
                "lookback_days": lookback_days
            }
        }
    
    async def get_active_alerts(self) -> List[dict]:
        """
        Get active alerts for recurring issues.
        These are patterns that need attention.
        """
        # Get from database
        db_alerts = await self.db.get_active_alerts()
        
        # Also run quick analysis for fresh patterns
        analysis = await self.run_full_analysis(lookback_days=30)
        
        # Filter to critical/high severity weaknesses
        fresh_alerts = [
            p for p in analysis.get("weaknesses", [])
            if p.get("severity") in ["critical", "high"]
        ]
        
        # Combine, dedupe by name
        seen_names = {a.get("name") for a in db_alerts}
        combined = list(db_alerts)
        
        for alert in fresh_alerts:
            if alert.get("name") not in seen_names:
                combined.append(alert)
                seen_names.add(alert.get("name"))
        
        return combined
    
    async def save_patterns(self, patterns: List[dict]) -> int:
        """Save detected patterns to database."""
        saved = 0
        for pattern in patterns:
            try:
                # Check if pattern already exists
                existing = await self.db.list_patterns()
                exists = any(
                    p.get("name") == pattern.get("name") 
                    for p in existing
                )
                
                if exists:
                    # Update occurrence count
                    for p in existing:
                        if p.get("name") == pattern.get("name"):
                            await self.db.update_pattern(
                                p["id"],
                                {
                                    "occurrence_count": pattern.get("occurrence_count", 1),
                                    "last_occurred_at": datetime.utcnow().isoformat(),
                                    "estimated_pnl_impact": pattern.get("estimated_pnl_impact")
                                }
                            )
                            break
                else:
                    # Create new pattern
                    pattern["first_identified_at"] = datetime.utcnow().isoformat()
                    pattern["last_occurred_at"] = datetime.utcnow().isoformat()
                    pattern["ai_identified"] = True
                    pattern["confidence_score"] = 0.8
                    await self.db.create_pattern(pattern)
                
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save pattern: {e}")
        
        return saved


# Singleton
_pattern_service: Optional[PatternService] = None


def get_pattern_service() -> PatternService:
    global _pattern_service
    if _pattern_service is None:
        _pattern_service = PatternService()
    return _pattern_service
