"""
Journal Router - Daily trading reflections.
"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db import personal_db
from models import JournalEntryCreate

router = APIRouter()


class JournalEntryResponse(BaseModel):
    """Journal entry response."""
    id: UUID
    entry_date: date
    market_outlook: Optional[str] = None
    planned_actions: Optional[str] = None
    risk_appetite: Optional[str] = None
    what_happened: Optional[str] = None
    what_went_well: Optional[str] = None
    what_went_poorly: Optional[str] = None
    lessons_learned: Optional[str] = None
    emotional_state: Optional[str] = None
    energy_level: Optional[int] = None
    focus_level: Optional[int] = None
    trade_ids: Optional[List[UUID]] = None
    principle_violations: Optional[List[UUID]] = None
    created_at: datetime
    updated_at: datetime


class JournalStreakResponse(BaseModel):
    """Journaling streak info."""
    current_streak: int
    total_entries: int
    last_entry: Optional[str] = None


@router.post("")
async def create_or_update_journal(entry: JournalEntryCreate):
    """
    Create or update a journal entry for a date.
    
    One entry per day - use PUT semantics (upsert).
    """
    try:
        entry_data = entry.model_dump(exclude_none=True)
        
        # Convert date to string
        if "entry_date" in entry_data:
            entry_data["entry_date"] = str(entry_data["entry_date"])
        
        # Convert UUIDs
        if "trade_ids" in entry_data and entry_data["trade_ids"]:
            entry_data["trade_ids"] = [str(t) for t in entry_data["trade_ids"]]
        if "principle_violations" in entry_data and entry_data["principle_violations"]:
            entry_data["principle_violations"] = [str(p) for p in entry_data["principle_violations"]]
        
        result = await personal_db.upsert_journal_entry(entry_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_journal_entries(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List journal entries, most recent first."""
    try:
        entries = await personal_db.list_journal_entries(limit=limit, offset=offset)
        return {
            "entries": entries,
            "count": len(entries),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streak")
async def get_journaling_streak():
    """
    Get current journaling streak.
    
    Tracks consecutive days with journal entries.
    """
    try:
        streak_info = await personal_db.get_journaling_streak()
        return streak_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today")
async def get_today_entry():
    """Get today's journal entry (create empty if not exists)."""
    try:
        today = str(date.today())
        entry = await personal_db.get_journal_entry(today)
        
        if entry:
            return entry
        
        # Return empty template for today
        return {
            "entry_date": today,
            "exists": False,
            "template": {
                "market_outlook": None,
                "planned_actions": None,
                "risk_appetite": None,
                "what_happened": None,
                "what_went_well": None,
                "what_went_poorly": None,
                "lessons_learned": None,
                "emotional_state": None,
                "energy_level": None,
                "focus_level": None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_date}")
async def get_journal_entry(entry_date: str):
    """Get journal entry for a specific date (YYYY-MM-DD)."""
    try:
        # Validate date format
        datetime.strptime(entry_date, "%Y-%m-%d")
        
        entry = await personal_db.get_journal_entry(entry_date)
        if not entry:
            raise HTTPException(status_code=404, detail=f"No entry for {entry_date}")
        return entry
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/emotional-patterns")
async def get_emotional_patterns(days: int = Query(30, ge=7, le=90)):
    """
    Analyze emotional patterns over time.
    
    Correlates emotional_state with trading outcomes.
    """
    try:
        entries = await personal_db.list_journal_entries(limit=days)
        trades = await personal_db.get_recent_trades(days=days)
        
        if not entries:
            return {"patterns": [], "message": "No journal entries to analyze"}
        
        # Group trades by date
        trades_by_date = {}
        for t in trades:
            trade_date = t.get("executed_at", "")[:10]
            if trade_date not in trades_by_date:
                trades_by_date[trade_date] = []
            trades_by_date[trade_date].append(t)
        
        # Correlate emotional state with outcomes
        state_performance = {}
        for entry in entries:
            state = entry.get("emotional_state")
            if not state:
                continue
            
            entry_date = str(entry.get("entry_date"))
            day_trades = trades_by_date.get(entry_date, [])
            
            if day_trades:
                day_pnl = sum(float(t.get("pnl", 0) or 0) for t in day_trades)
                wins = sum(1 for t in day_trades if float(t.get("pnl", 0) or 0) > 0)
                losses = len(day_trades) - wins
                
                if state not in state_performance:
                    state_performance[state] = {
                        "total_pnl": 0,
                        "wins": 0,
                        "losses": 0,
                        "days": 0
                    }
                
                state_performance[state]["total_pnl"] += day_pnl
                state_performance[state]["wins"] += wins
                state_performance[state]["losses"] += losses
                state_performance[state]["days"] += 1
        
        # Format results
        patterns = []
        for state, stats in state_performance.items():
            total = stats["wins"] + stats["losses"]
            if total >= 3:
                win_rate = (stats["wins"] / total * 100) if total > 0 else 0
                patterns.append({
                    "emotional_state": state,
                    "days_traded": stats["days"],
                    "total_trades": total,
                    "win_rate": win_rate,
                    "total_pnl": stats["total_pnl"],
                    "avg_pnl_per_day": stats["total_pnl"] / stats["days"] if stats["days"] > 0 else 0
                })
        
        # Sort by P&L impact
        patterns.sort(key=lambda p: p["total_pnl"])
        
        return {
            "patterns": patterns,
            "period_days": days,
            "entries_analyzed": len(entries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/energy-correlation")
async def get_energy_correlation(days: int = Query(30, ge=7, le=90)):
    """Analyze correlation between energy/focus levels and performance."""
    try:
        entries = await personal_db.list_journal_entries(limit=days)
        trades = await personal_db.get_recent_trades(days=days)
        
        # Group trades by date
        trades_by_date = {}
        for t in trades:
            trade_date = t.get("executed_at", "")[:10]
            if trade_date not in trades_by_date:
                trades_by_date[trade_date] = []
            trades_by_date[trade_date].append(t)
        
        # Correlate levels with outcomes
        low_energy_pnl = []  # 1-2
        medium_energy_pnl = []  # 3
        high_energy_pnl = []  # 4-5
        
        for entry in entries:
            energy = entry.get("energy_level")
            if energy is None:
                continue
            
            entry_date = str(entry.get("entry_date"))
            day_trades = trades_by_date.get(entry_date, [])
            
            if day_trades:
                day_pnl = sum(float(t.get("pnl", 0) or 0) for t in day_trades)
                
                if energy <= 2:
                    low_energy_pnl.append(day_pnl)
                elif energy == 3:
                    medium_energy_pnl.append(day_pnl)
                else:
                    high_energy_pnl.append(day_pnl)
        
        def summarize(pnls):
            if not pnls:
                return {"days": 0, "total_pnl": 0, "avg_pnl": 0}
            return {
                "days": len(pnls),
                "total_pnl": sum(pnls),
                "avg_pnl": sum(pnls) / len(pnls)
            }
        
        return {
            "low_energy_1_2": summarize(low_energy_pnl),
            "medium_energy_3": summarize(medium_energy_pnl),
            "high_energy_4_5": summarize(high_energy_pnl),
            "recommendation": _get_energy_recommendation(
                summarize(low_energy_pnl),
                summarize(medium_energy_pnl),
                summarize(high_energy_pnl)
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_energy_recommendation(low, medium, high):
    """Generate recommendation based on energy correlation."""
    if low["days"] < 3 or high["days"] < 3:
        return "Not enough data for recommendation"
    
    if low["avg_pnl"] < 0 and high["avg_pnl"] > 0:
        return "Strong correlation: Avoid trading on low energy days"
    elif high["avg_pnl"] < low["avg_pnl"]:
        return "Interesting: Higher energy doesn't correlate with better performance. Consider if overconfidence is a factor."
    else:
        return "Energy level shows moderate correlation with performance"
