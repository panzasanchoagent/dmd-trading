"""
Trades Router - CRUD operations for trade log.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from decimal import Decimal

from db import personal_db
from models import TradeCreate, Trade

router = APIRouter()


class TradeResponse(BaseModel):
    """Trade response with all fields."""
    id: UUID
    asset: str
    side: str
    quantity: Decimal
    price: Decimal
    quote_currency: str
    source_platform: Optional[str] = None
    executed_at: datetime
    trade_type: Optional[str] = None
    strategy: Optional[str] = None
    timeframe: Optional[str] = None
    thesis_id: Optional[UUID] = None
    note_ids: Optional[List[UUID]] = None
    planned_entry: Optional[Decimal] = None
    slippage_pct: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    position_size_pct: Optional[Decimal] = None
    entry_rationale: Optional[str] = None
    tags: Optional[List[str]] = None
    cash_flow: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime


class TradesListResponse(BaseModel):
    """Paginated trades list."""
    trades: List[dict]
    total: int
    offset: int
    limit: int


@router.post("", response_model=dict)
async def create_trade(trade: TradeCreate):
    """
    Create a new trade entry.
    
    Required fields: asset, side, quantity, price, executed_at
    Optional: trade_type, strategy, stop_loss, take_profit, etc.
    """
    try:
        trade_data = trade.model_dump(exclude_none=True)
        
        # Convert datetime to ISO string
        if "executed_at" in trade_data:
            trade_data["executed_at"] = trade_data["executed_at"].isoformat()
        
        # Convert UUIDs to strings
        if "thesis_id" in trade_data and trade_data["thesis_id"]:
            trade_data["thesis_id"] = str(trade_data["thesis_id"])
        if "note_ids" in trade_data and trade_data["note_ids"]:
            trade_data["note_ids"] = [str(n) for n in trade_data["note_ids"]]
        
        # Convert Decimals to floats for JSON
        for key in ["quantity", "price", "planned_entry", "stop_loss", "take_profit", "position_size_pct"]:
            if key in trade_data and trade_data[key] is not None:
                trade_data[key] = float(trade_data[key])
        
        result = await personal_db.create_trade(trade_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TradesListResponse)
async def list_trades(
    asset: Optional[str] = Query(None, description="Filter by asset (e.g., BTC, ETH)"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List trades with optional filters.
    
    Supports filtering by asset, strategy, and date range.
    Returns paginated results.
    """
    try:
        trades = await personal_db.list_trades(
            asset=asset,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return {
            "trades": trades,
            "total": len(trades),  # Would need separate count query for accurate total
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trade_id}")
async def get_trade(trade_id: UUID):
    """Get a single trade by ID."""
    try:
        trade = await personal_db.get_trade(str(trade_id))
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        return trade
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{trade_id}")
async def update_trade(trade_id: UUID, trade: TradeCreate):
    """Update an existing trade."""
    try:
        trade_data = trade.model_dump(exclude_none=True)
        
        # Convert types for JSON
        if "executed_at" in trade_data:
            trade_data["executed_at"] = trade_data["executed_at"].isoformat()
        
        for key in ["quantity", "price", "planned_entry", "stop_loss", "take_profit", "position_size_pct"]:
            if key in trade_data and trade_data[key] is not None:
                trade_data[key] = float(trade_data[key])
        
        result = await personal_db.update_trade(str(trade_id), trade_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{trade_id}")
async def delete_trade(trade_id: UUID):
    """Delete a trade."""
    try:
        success = await personal_db.delete_trade(str(trade_id))
        if not success:
            raise HTTPException(status_code=404, detail="Trade not found")
        return {"status": "deleted", "id": str(trade_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent/summary")
async def get_recent_summary(days: int = Query(7, ge=1, le=90)):
    """Get summary of recent trading activity."""
    try:
        trades = await personal_db.get_recent_trades(days=days)
        
        if not trades:
            return {
                "period_days": days,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "assets_traded": []
            }
        
        wins = sum(1 for t in trades if float(t.get("pnl", 0) or 0) > 0)
        losses = sum(1 for t in trades if float(t.get("pnl", 0) or 0) < 0)
        total_pnl = sum(float(t.get("pnl", 0) or 0) for t in trades)
        assets = list(set(t.get("asset") for t in trades if t.get("asset")))
        
        return {
            "period_days": days,
            "total_trades": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            "total_pnl": total_pnl,
            "assets_traded": assets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
