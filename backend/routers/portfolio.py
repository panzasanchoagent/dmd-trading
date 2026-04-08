"""
Portfolio Router - Positions, allocations, and concentration checks.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from decimal import Decimal

from db import arete_db
from services.portfolio_service import (
    PortfolioDataGap,
    compute_daily_nav_history,
    get_portfolio_positions,
    get_reconstructed_closed_positions,
)

router = APIRouter()


# Position sizing rules (from Liquid Portfolio Job)
POSITION_RULES = {
    "max_single_position_pct": 20.0,
    "max_sector_concentration_pct": 40.0,
    "core_allocation_range": (60.0, 80.0),
    "max_trading_allocation_pct": 20.0,
    "max_speculative_allocation_pct": 10.0
}


class PositionResponse(BaseModel):
    """Position with current market data."""
    asset: str
    quantity: Decimal
    avg_entry_price: Optional[Decimal]
    total_cost_basis: Optional[Decimal]
    current_price: Optional[Decimal]
    current_value: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    unrealized_pnl_pct: Optional[Decimal]
    allocation_pct: Optional[Decimal]
    position_type: Optional[str]


class PortfolioSummary(BaseModel):
    """Overall portfolio summary."""
    total_value: Decimal
    total_cost_basis: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_pct: Decimal
    position_count: int
    largest_position: Optional[str]
    largest_position_pct: Optional[Decimal]


class ConcentrationAlert(BaseModel):
    """Alert for concentration violations."""
    rule: str
    threshold: float
    current: float
    violation: bool
    message: str


@router.get("/positions")
async def get_positions(include_prices: bool = Query(True)):
    """
    Get all current positions with live prices.
    
    Fetches current market prices from Arete DB if include_prices=True.
    """
    try:
        positions, source = await get_portfolio_positions()

        if not positions:
            return {"positions": [], "total_value": 0, "position_count": 0, "source": source}
        
        # Get current prices if requested
        if include_prices:
            assets = [p["asset"] for p in positions]
            prices = await arete_db.get_current_prices(assets)
            
            total_value = 0
            for pos in positions:
                asset = pos["asset"]
                if asset in prices:
                    price = prices[asset]["price"]
                    pos["current_price"] = price
                    pos["current_value"] = float(pos["quantity"]) * price
                    total_value += pos["current_value"]
                    
                    if pos.get("total_cost_basis"):
                        pos["unrealized_pnl"] = pos["current_value"] - float(pos["total_cost_basis"])
                        pos["unrealized_pnl_pct"] = (pos["unrealized_pnl"] / float(pos["total_cost_basis"])) * 100
            
            # Calculate allocation percentages
            if total_value > 0:
                for pos in positions:
                    if pos.get("current_value"):
                        pos["allocation_pct"] = (pos["current_value"] / total_value) * 100
        
        total_value = sum(p.get("current_value", 0) or 0 for p in positions)
        
        return {
            "positions": positions,
            "total_value": total_value,
            "position_count": len(positions),
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/closed")
async def get_closed_positions(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    """Get closed position history with P&L."""
    try:
        closed, source = await get_reconstructed_closed_positions()
        if start_date:
            closed = [position for position in closed if (position.get("exit_date") or "") >= start_date]
        if end_date:
            closed = [position for position in closed if (position.get("exit_date") or "") <= end_date]
        closed = closed[:limit]
        
        # Calculate summary stats
        total_pnl = sum(float(p.get("realized_pnl", 0) or 0) for p in closed)
        wins = sum(1 for p in closed if p.get("win_loss") == "win")
        losses = sum(1 for p in closed if p.get("win_loss") == "loss")
        
        return {
            "closed_positions": closed,
            "total_count": len(closed),
            "total_realized_pnl": total_pnl,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            "source": source,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_portfolio_summary():
    """
    Get portfolio summary with key metrics.
    
    Returns: total value, P&L, position count, concentration metrics.
    """
    try:
        positions, source = await get_portfolio_positions()

        if not positions:
            return {
                "total_value": 0,
                "total_cost_basis": 0,
                "total_unrealized_pnl": 0,
                "total_unrealized_pnl_pct": 0,
                "position_count": 0,
                "largest_position": None,
                "largest_position_pct": 0,
                "allocation_by_type": {},
                "source": source
            }
        
        # Get prices
        assets = [p["asset"] for p in positions]
        prices = await arete_db.get_current_prices(assets)
        
        # Calculate values
        for pos in positions:
            asset = pos["asset"]
            if asset in prices:
                pos["current_price"] = prices[asset]["price"]
                pos["current_value"] = float(pos["quantity"]) * prices[asset]["price"]
        
        total_value = sum(p.get("current_value", 0) or 0 for p in positions)
        total_cost = sum(float(p.get("total_cost_basis", 0) or 0) for p in positions)
        total_pnl = total_value - total_cost
        
        # Find largest position
        largest = max(positions, key=lambda p: p.get("current_value", 0) or 0)
        largest_pct = (largest.get("current_value", 0) / total_value * 100) if total_value > 0 else 0
        
        # Allocation by position type
        type_alloc = {}
        for pos in positions:
            pos_type = pos.get("position_type", "unclassified") or "unclassified"
            if pos_type not in type_alloc:
                type_alloc[pos_type] = 0
            type_alloc[pos_type] += pos.get("current_value", 0) or 0
        
        # Convert to percentages
        if total_value > 0:
            type_alloc = {k: (v / total_value * 100) for k, v in type_alloc.items()}
        
        return {
            "total_value": total_value,
            "total_cost_basis": total_cost,
            "total_unrealized_pnl": total_pnl,
            "total_unrealized_pnl_pct": (total_pnl / total_cost * 100) if total_cost > 0 else 0,
            "position_count": len(positions),
            "largest_position": largest.get("asset"),
            "largest_position_pct": largest_pct,
            "allocation_by_type": type_alloc,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concentration")
async def check_concentration():
    """
    Check portfolio concentration against position sizing rules.
    
    Rules:
    - Max single position: 20%
    - Max sector: 40%
    - Core allocation: 60-80%
    - Trading allocation: max 20%
    - Speculative: max 10%
    """
    try:
        positions, source = await get_portfolio_positions()

        if not positions:
            return {"alerts": [], "status": "no_positions", "source": source}
        
        # Get prices and calculate values
        assets = [p["asset"] for p in positions]
        prices = await arete_db.get_current_prices(assets)
        
        for pos in positions:
            if pos["asset"] in prices:
                pos["current_value"] = float(pos["quantity"]) * prices[pos["asset"]]["price"]
        
        total_value = sum(p.get("current_value", 0) or 0 for p in positions)
        
        if total_value == 0:
            return {"alerts": [], "status": "no_value"}
        
        alerts = []
        
        # Check single position concentration
        for pos in positions:
            value = pos.get("current_value", 0) or 0
            pct = (value / total_value) * 100
            
            if pct > POSITION_RULES["max_single_position_pct"]:
                alerts.append({
                    "rule": "max_single_position",
                    "threshold": POSITION_RULES["max_single_position_pct"],
                    "current": pct,
                    "violation": True,
                    "message": f"{pos['asset']} is {pct:.1f}% of portfolio (max {POSITION_RULES['max_single_position_pct']}%)"
                })
        
        # Check allocation by position type
        type_values = {}
        for pos in positions:
            pos_type = pos.get("position_type", "unclassified") or "unclassified"
            if pos_type not in type_values:
                type_values[pos_type] = 0
            type_values[pos_type] += pos.get("current_value", 0) or 0
        
        # Trading allocation check
        trading_pct = (type_values.get("trading", 0) / total_value) * 100
        if trading_pct > POSITION_RULES["max_trading_allocation_pct"]:
            alerts.append({
                "rule": "max_trading_allocation",
                "threshold": POSITION_RULES["max_trading_allocation_pct"],
                "current": trading_pct,
                "violation": True,
                "message": f"Trading positions are {trading_pct:.1f}% (max {POSITION_RULES['max_trading_allocation_pct']}%)"
            })
        
        # Speculative allocation check
        spec_pct = (type_values.get("speculative", 0) / total_value) * 100
        if spec_pct > POSITION_RULES["max_speculative_allocation_pct"]:
            alerts.append({
                "rule": "max_speculative_allocation",
                "threshold": POSITION_RULES["max_speculative_allocation_pct"],
                "current": spec_pct,
                "violation": True,
                "message": f"Speculative positions are {spec_pct:.1f}% (max {POSITION_RULES['max_speculative_allocation_pct']}%)"
            })
        
        # Core allocation check (should be 60-80%)
        core_pct = (type_values.get("core", 0) / total_value) * 100
        min_core, max_core = POSITION_RULES["core_allocation_range"]
        if core_pct < min_core:
            alerts.append({
                "rule": "core_allocation_low",
                "threshold": min_core,
                "current": core_pct,
                "violation": True,
                "message": f"Core positions are only {core_pct:.1f}% (target {min_core}-{max_core}%)"
            })
        
        return {
            "alerts": alerts,
            "status": "violations_found" if alerts else "healthy",
            "summary": {
                "total_value": total_value,
                "position_count": len(positions),
                "allocation_by_type": {k: (v/total_value*100) for k, v in type_values.items()}
            },
            "rules": POSITION_RULES,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nav-history")
async def get_nav_history(days: int = Query(90, ge=7, le=3650)):
    """Get reconstructed daily NAV using local stock_ohlcv history when available."""
    try:
        history, source = await compute_daily_nav_history(days=days)
        return {
            "days": days,
            "history": history,
            "source": source,
        }
    except PortfolioDataGap as exc:
        return {
            "days": days,
            "history": [],
            "source": "positions_plus_trades",
            "gap": str(exc),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics(days: int = Query(30, ge=7, le=365)):
    """Get portfolio performance metrics over time."""
    try:
        closed, source = await get_reconstructed_closed_positions()
        
        # Filter by date range
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        closed = [p for p in closed if p.get("exit_date", "") >= cutoff]
        
        if not closed:
            return {
                "period_days": days,
                "total_realized_pnl": 0,
                "win_rate": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "source": source,
            }
        
        # Calculate metrics
        wins = [p for p in closed if p.get("win_loss") == "win"]
        losses = [p for p in closed if p.get("win_loss") == "loss"]
        
        total_pnl = sum(float(p.get("realized_pnl", 0) or 0) for p in closed)
        gross_profit = sum(float(p.get("realized_pnl", 0) or 0) for p in wins)
        gross_loss = abs(sum(float(p.get("realized_pnl", 0) or 0) for p in losses))
        
        win_pnls = [float(p.get("realized_pnl", 0) or 0) for p in wins]
        loss_pnls = [float(p.get("realized_pnl", 0) or 0) for p in losses]
        
        return {
            "period_days": days,
            "total_trades": len(closed),
            "total_realized_pnl": total_pnl,
            "win_rate": (len(wins) / len(closed) * 100) if closed else 0,
            "avg_win": (sum(win_pnls) / len(win_pnls)) if win_pnls else 0,
            "avg_loss": (sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0,
            "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else float('inf'),
            "largest_win": max(win_pnls) if win_pnls else 0,
            "largest_loss": min(loss_pnls) if loss_pnls else 0,
            "expectancy": (total_pnl / len(closed)) if closed else 0,
            "source": source,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
