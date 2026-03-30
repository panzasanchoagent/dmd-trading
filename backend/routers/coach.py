"""
Coach Router - AI coaching endpoints.
The brain of the trading journal.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from decimal import Decimal

from db import personal_db, arete_db
from ai_client import (
    get_pre_trade_coach,
    get_post_trade_coach,
    get_weekly_coach,
    get_adhoc_coach
)
from services.pattern_service import get_pattern_service
from services.market_service import get_market_service

router = APIRouter()


# ============================================
# REQUEST MODELS
# ============================================

class PreTradeRequest(BaseModel):
    """Pre-trade validation request."""
    asset: str
    side: str  # BUY, SELL
    quantity: Decimal
    price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    position_size_pct: Optional[Decimal] = None
    thesis_id: Optional[UUID] = None
    conviction: Optional[int] = Field(None, ge=1, le=10)
    rationale: Optional[str] = None


class PostTradeRequest(BaseModel):
    """Post-trade review request."""
    trade_id: UUID
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    pnl_pct: Optional[Decimal] = None
    holding_days: Optional[int] = None
    entry_rationale: Optional[str] = None


class ChatRequest(BaseModel):
    """Ad-hoc coaching chat request."""
    message: str
    include_context: bool = True
    session_id: Optional[UUID] = None  # Continue existing session


class PatternAcknowledgeRequest(BaseModel):
    """Acknowledge a pattern."""
    pattern_id: UUID
    action: str = "acknowledge"  # acknowledge, address, resolve


# ============================================
# PRE-TRADE VALIDATION
# ============================================

@router.post("/validate-thesis")
async def validate_thesis(request: PreTradeRequest):
    """
    Pre-trade thesis validation.
    
    Reviews the planned trade against:
    - Trading principles
    - Current portfolio state
    - Recent trading history
    - Market conditions
    
    Returns: GO / CAUTION / STOP recommendation
    """
    try:
        # Gather context
        principles = await personal_db.list_principles(active_only=True)
        positions = await personal_db.get_positions()
        recent_trades = await personal_db.get_recent_trades(days=30, limit=20)
        
        # Get market context
        market_service = get_market_service()
        market_context = await market_service.get_context_for_asset(request.asset)
        
        # Calculate portfolio summary
        assets = [p["asset"] for p in positions] + [request.asset]
        prices = await arete_db.get_current_prices(list(set(assets)))
        
        total_value = sum(
            float(p["quantity"]) * prices.get(p["asset"], {}).get("price", 0)
            for p in positions
        )
        
        portfolio_summary = {
            "total_value": total_value,
            "position_count": len(positions),
            "existing_position": next(
                (p for p in positions if p["asset"] == request.asset.upper()),
                None
            )
        }
        
        # Convert request to dict
        trade_plan = {
            "asset": request.asset,
            "side": request.side,
            "quantity": float(request.quantity),
            "price": float(request.price),
            "stop_loss": float(request.stop_loss) if request.stop_loss else None,
            "take_profit": float(request.take_profit) if request.take_profit else None,
            "position_size_pct": float(request.position_size_pct) if request.position_size_pct else None,
            "conviction": request.conviction,
            "rationale": request.rationale
        }
        
        # Get AI validation
        coach = get_pre_trade_coach()
        result = await coach.validate(
            trade_plan=trade_plan,
            principles=principles,
            portfolio_summary=portfolio_summary,
            recent_trades=recent_trades,
            market_context=market_context
        )
        
        # Save session
        session_data = {
            "session_type": "pre_trade",
            "position_snapshot": {
                "portfolio_value": total_value,
                "position_count": len(positions)
            },
            "messages": [
                {"role": "user", "content": f"Validate trade: {request.asset} {request.side}", "timestamp": datetime.utcnow().isoformat()},
                {"role": "assistant", "content": result["reasoning"], "timestamp": datetime.utcnow().isoformat()}
            ],
            "key_insights": [result["recommendation"]],
            "model_used": result.get("model_used"),
            "tokens_used": result.get("tokens_used")
        }
        
        saved_session = await personal_db.create_coach_session(session_data)
        
        return {
            "recommendation": result["recommendation"],
            "reasoning": result["reasoning"],
            "session_id": saved_session.get("id"),
            "model_used": result.get("model_used")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# POST-TRADE REVIEW
# ============================================

@router.post("/review-trade")
async def review_trade(request: PostTradeRequest):
    """
    Post-trade analysis.
    
    Analyzes a completed trade for:
    - Entry/exit quality
    - What went well/poorly
    - Lessons learned
    - Pattern identification
    """
    try:
        # Get the trade
        trade = await personal_db.get_trade(str(request.trade_id))
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        # Enrich with request data
        trade_details = {
            **trade,
            "entry_price": float(request.entry_price) if request.entry_price else trade.get("price"),
            "exit_price": float(request.exit_price) if request.exit_price else None,
            "pnl": float(request.pnl) if request.pnl else trade.get("pnl"),
            "pnl_pct": float(request.pnl_pct) if request.pnl_pct else trade.get("pnl_pct"),
            "holding_days": request.holding_days,
            "entry_rationale": request.entry_rationale or trade.get("entry_rationale")
        }
        
        # Get market context at trade time
        market_service = get_market_service()
        market_context = await market_service.get_context_at_time(
            trade_details["asset"],
            trade_details.get("executed_at")
        )
        
        # Find similar trades
        all_trades = await personal_db.list_trades(asset=trade_details["asset"], limit=50)
        similar_trades = [t for t in all_trades if t.get("id") != str(request.trade_id)][:5]
        
        # Get AI review
        coach = get_post_trade_coach()
        result = await coach.analyze(
            trade=trade_details,
            market_context=market_context,
            similar_trades=similar_trades
        )
        
        # Save session
        session_data = {
            "session_type": "post_trade",
            "trade_ids": [str(request.trade_id)],
            "messages": [
                {"role": "user", "content": f"Review trade {request.trade_id}", "timestamp": datetime.utcnow().isoformat()},
                {"role": "assistant", "content": result["analysis"], "timestamp": datetime.utcnow().isoformat()}
            ],
            "model_used": result.get("model_used"),
            "tokens_used": result.get("tokens_used")
        }
        
        saved_session = await personal_db.create_coach_session(session_data)
        
        return {
            "analysis": result["analysis"],
            "session_id": saved_session.get("id"),
            "trade_id": str(request.trade_id),
            "model_used": result.get("model_used")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WEEKLY ANALYSIS
# ============================================

@router.post("/weekly-analysis")
async def run_weekly_analysis():
    """
    Weekly trading review.
    
    Comprehensive analysis of the past week:
    - Win rate and P&L
    - Best/worst trades
    - Pattern detection
    - Principle adherence
    - Market correlation
    - Actionable improvements
    """
    try:
        # Get week's data
        trades = await personal_db.get_recent_trades(days=7)
        principles = await personal_db.list_principles(active_only=True)
        
        # Calculate P&L summary
        wins = [t for t in trades if float(t.get("pnl", 0) or 0) > 0]
        losses = [t for t in trades if float(t.get("pnl", 0) or 0) < 0]
        total_pnl = sum(float(t.get("pnl", 0) or 0) for t in trades)
        
        pnl_summary = {
            "total_pnl": total_pnl,
            "total_pnl_pct": None,  # Would need portfolio value
            "win_rate": (len(wins) / len(trades) * 100) if trades else 0,
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses)
        }
        
        # Get market summary
        market_service = get_market_service()
        market_summary = await market_service.get_weekly_summary()
        
        # Get existing patterns
        pattern_service = get_pattern_service()
        patterns = await personal_db.list_patterns(resolved=False)
        
        # Run AI analysis
        coach = get_weekly_coach()
        result = await coach.analyze_week(
            weekly_trades=trades,
            pnl_summary=pnl_summary,
            principles=principles,
            market_summary=market_summary,
            patterns=patterns
        )
        
        # Also run pattern detection
        new_patterns = await pattern_service.run_full_analysis(lookback_days=30)
        
        # Save patterns
        if new_patterns.get("patterns"):
            await pattern_service.save_patterns(new_patterns["patterns"])
        
        # Save session
        session_data = {
            "session_type": "weekly_review",
            "trade_ids": [t.get("id") for t in trades if t.get("id")],
            "position_snapshot": pnl_summary,
            "messages": [
                {"role": "user", "content": "Weekly analysis request", "timestamp": datetime.utcnow().isoformat()},
                {"role": "assistant", "content": result["analysis"], "timestamp": datetime.utcnow().isoformat()}
            ],
            "key_insights": new_patterns.get("weaknesses", [])[:3],
            "model_used": result.get("model_used"),
            "tokens_used": result.get("tokens_used")
        }
        
        saved_session = await personal_db.create_coach_session(session_data)
        
        return {
            "analysis": result["analysis"],
            "pnl_summary": pnl_summary,
            "patterns_detected": {
                "total": new_patterns.get("summary", {}).get("total_patterns", 0),
                "weaknesses": len(new_patterns.get("weaknesses", [])),
                "strengths": len(new_patterns.get("strengths", []))
            },
            "session_id": saved_session.get("id"),
            "model_used": result.get("model_used")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# AD-HOC CHAT
# ============================================

@router.post("/chat")
async def coach_chat(request: ChatRequest):
    """
    Ad-hoc coaching conversation.
    
    Ask questions, get guidance, work through trading psychology.
    """
    try:
        context = {}
        
        if request.include_context:
            # Get portfolio context
            positions = await personal_db.get_positions()
            assets = [p["asset"] for p in positions]
            prices = await arete_db.get_current_prices(assets) if assets else {}
            
            total_value = sum(
                float(p["quantity"]) * prices.get(p["asset"], {}).get("price", 0)
                for p in positions
            )
            
            # Get recent P&L
            recent_trades = await personal_db.get_recent_trades(days=7)
            recent_pnl = sum(float(t.get("pnl", 0) or 0) for t in recent_trades)
            
            # Get known patterns
            patterns = await personal_db.list_patterns(pattern_type="weakness", resolved=False)
            
            context = {
                "portfolio_value": total_value,
                "open_positions": len(positions),
                "recent_pnl": recent_pnl,
                "known_patterns": [p.get("name") for p in patterns[:5]]
            }
        
        # Get conversation history if continuing session
        conversation_history = []
        if request.session_id:
            session = await personal_db.get_coach_session(str(request.session_id))
            if session:
                conversation_history = session.get("messages", [])
        
        # Get response
        coach = get_adhoc_coach()
        result = await coach.chat(
            message=request.message,
            context=context,
            conversation_history=conversation_history
        )
        
        # Save/update session
        new_messages = conversation_history + [
            {"role": "user", "content": request.message, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": result["response"], "timestamp": datetime.utcnow().isoformat()}
        ]
        
        if request.session_id:
            await personal_db.update_coach_session(
                str(request.session_id),
                {"messages": new_messages}
            )
            session_id = str(request.session_id)
        else:
            session_data = {
                "session_type": "ad_hoc",
                "messages": new_messages,
                "model_used": result.get("model_used"),
                "tokens_used": result.get("tokens_used")
            }
            saved = await personal_db.create_coach_session(session_data)
            session_id = saved.get("id")
        
        return {
            "response": result["response"],
            "session_id": session_id,
            "model_used": result.get("model_used")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PATTERNS & ALERTS
# ============================================

@router.get("/patterns")
async def get_patterns(
    pattern_type: Optional[str] = Query(None, description="weakness, strength, or neutral"),
    category: Optional[str] = Query(None, description="timing, sizing, emotion, etc."),
    include_resolved: bool = Query(False)
):
    """
    Get identified trading patterns.
    
    Patterns are automatically detected by the weekly analysis
    and can be manually acknowledged/addressed.
    """
    try:
        patterns = await personal_db.list_patterns(
            pattern_type=pattern_type,
            category=category,
            resolved=include_resolved
        )
        
        # Categorize
        weaknesses = [p for p in patterns if p.get("pattern_type") == "weakness"]
        strengths = [p for p in patterns if p.get("pattern_type") == "strength"]
        
        return {
            "patterns": patterns,
            "summary": {
                "total": len(patterns),
                "weaknesses": len(weaknesses),
                "strengths": len(strengths),
                "unacknowledged": sum(1 for p in patterns if not p.get("acknowledged"))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_active_alerts():
    """
    Get active alerts for recurring issues.
    
    These are patterns that need attention:
    - Unacknowledged weaknesses
    - Critical/high severity patterns
    - Recently triggered patterns
    """
    try:
        pattern_service = get_pattern_service()
        alerts = await pattern_service.get_active_alerts()
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda a: severity_order.get(a.get("severity", "low"), 4))
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "critical_count": sum(1 for a in alerts if a.get("severity") == "critical"),
            "high_count": sum(1 for a in alerts if a.get("severity") == "high")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns/{pattern_id}/acknowledge")
async def acknowledge_pattern(pattern_id: UUID, request: PatternAcknowledgeRequest):
    """
    Acknowledge or update a pattern's status.
    
    Actions:
    - acknowledge: Mark as seen
    - address: Mark as being worked on
    - resolve: Mark as resolved
    """
    try:
        update_data = {}
        
        if request.action == "acknowledge":
            update_data["acknowledged"] = True
        elif request.action == "address":
            update_data["acknowledged"] = True
            update_data["being_addressed"] = True
        elif request.action == "resolve":
            update_data["resolved"] = True
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        result = await personal_db.update_pattern(str(pattern_id), update_data)
        
        return {
            "status": "updated",
            "pattern_id": str(pattern_id),
            "action": request.action,
            "pattern": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-pattern-detection")
async def run_pattern_detection(days: int = Query(90, ge=30, le=365)):
    """
    Manually trigger pattern detection.
    
    Analyzes trade history to identify recurring patterns.
    """
    try:
        pattern_service = get_pattern_service()
        results = await pattern_service.run_full_analysis(lookback_days=days)
        
        # Save new patterns
        saved_count = 0
        if results.get("patterns"):
            saved_count = await pattern_service.save_patterns(results["patterns"])
        
        return {
            "summary": results.get("summary", {}),
            "weaknesses": results.get("weaknesses", []),
            "strengths": results.get("strengths", []),
            "patterns_saved": saved_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HISTORY
# ============================================

@router.get("/sessions")
async def list_coach_sessions(
    session_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """List coaching session history."""
    try:
        sessions = await personal_db.list_coach_sessions(
            session_type=session_type,
            limit=limit
        )
        
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_coach_session(session_id: UUID):
    """Get a specific coaching session."""
    try:
        session = await personal_db.get_coach_session(str(session_id))
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
