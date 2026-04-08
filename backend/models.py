"""
Pydantic models for Trading Journal.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================
# TRADES
# ============================================

class TradeCreate(BaseModel):
    """Create a new trade."""
    asset: str
    side: str  # BUY, SELL
    quantity: Decimal
    price: Decimal
    quote_currency: str = "USD"
    source_platform: Optional[str] = None
    executed_at: datetime
    
    # Optional
    trade_type: Optional[str] = None  # entry, add, trim, exit, stop_loss
    strategy: Optional[str] = None  # thesis_driven, momentum, scalp
    timeframe: Optional[str] = None  # day_trade, swing, position
    thesis_id: Optional[UUID] = None
    note_ids: Optional[List[UUID]] = None
    planned_entry: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    position_size_pct: Optional[Decimal] = None
    entry_rationale: Optional[str] = None
    tags: Optional[List[str]] = None


class Trade(TradeCreate):
    """Trade with computed fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    cash_flow: Decimal
    slippage_pct: Optional[Decimal] = None


# ============================================
# POSITIONS
# ============================================

class Position(BaseModel):
    """Current open position."""
    id: UUID
    updated_at: datetime
    asset: str
    quantity: Decimal
    avg_entry_price: Optional[Decimal]
    total_cost_basis: Optional[Decimal]
    first_entry_date: Optional[datetime]
    last_trade_date: Optional[datetime]
    number_of_trades: Optional[int]
    current_price: Optional[Decimal]
    current_value: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    unrealized_pnl_pct: Optional[Decimal]
    position_type: Optional[str]


class ClosedPosition(BaseModel):
    """Historical closed position."""
    id: UUID
    created_at: datetime
    asset: str
    entry_date: Optional[datetime]
    avg_entry_price: Optional[Decimal]
    exit_date: Optional[datetime]
    avg_exit_price: Optional[Decimal]
    realized_pnl: Optional[Decimal]
    realized_pnl_pct: Optional[Decimal]
    holding_period_days: Optional[int]
    number_of_trades: Optional[int]
    strategy: Optional[str]
    win_loss: Optional[str]


# ============================================
# JOURNAL
# ============================================

class JournalEntryCreate(BaseModel):
    """Create a journal entry."""
    entry_date: date
    
    # Pre-market
    market_outlook: Optional[str] = None
    planned_actions: Optional[str] = None
    risk_appetite: Optional[str] = None  # aggressive, normal, defensive
    
    # End of day
    what_happened: Optional[str] = None
    what_went_well: Optional[str] = None
    what_went_poorly: Optional[str] = None
    lessons_learned: Optional[str] = None
    
    # Emotional state
    emotional_state: Optional[str] = None
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    focus_level: Optional[int] = Field(None, ge=1, le=5)
    
    # Links
    trade_ids: Optional[List[UUID]] = None
    principle_violations: Optional[List[UUID]] = None


class JournalEntry(JournalEntryCreate):
    """Journal entry with metadata."""
    id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================
# PRINCIPLES
# ============================================

class PrincipleCreate(BaseModel):
    """Create a trading principle."""
    title: str
    description: str
    category: Optional[str] = None  # risk, entry, exit, sizing, psychology
    rule_type: Optional[str] = "soft"  # hard, soft
    quantifiable: bool = False
    metric: Optional[str] = None
    threshold: Optional[Decimal] = None
    priority: int = 5


class Principle(PrincipleCreate):
    """Trading principle with tracking."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    times_followed: int = 0
    times_violated: int = 0
    last_violated_at: Optional[datetime] = None
    active: bool = True


# ============================================
# POST MORTEMS
# ============================================

class PostMortemCreate(BaseModel):
    """Create a post-mortem analysis."""
    trade_ids: List[UUID]
    asset: str
    result: Optional[str] = None  # win, loss, breakeven
    pnl: Optional[Decimal] = None
    pnl_pct: Optional[Decimal] = None
    
    # Scores
    entry_quality: Optional[int] = Field(None, ge=1, le=5)
    exit_quality: Optional[int] = Field(None, ge=1, le=5)
    sizing_quality: Optional[int] = Field(None, ge=1, le=5)
    thesis_quality: Optional[int] = Field(None, ge=1, le=5)
    
    # Reflection
    what_went_well: Optional[str] = None
    what_went_poorly: Optional[str] = None
    would_do_differently: Optional[str] = None
    key_lesson: Optional[str] = None
    
    # Patterns
    emotional_factors: Optional[List[str]] = None
    execution_errors: Optional[List[str]] = None
    principles_followed: Optional[List[UUID]] = None
    principles_violated: Optional[List[UUID]] = None


class PostMortem(PostMortemCreate):
    """Post-mortem with AI feedback."""
    id: UUID
    created_at: datetime
    ai_feedback: Optional[str] = None
    ai_generated_at: Optional[datetime] = None


# ============================================
# COACH
# ============================================

class CoachMessage(BaseModel):
    """Single message in coach conversation."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CoachSession(BaseModel):
    """AI coaching session."""
    id: UUID
    created_at: datetime
    session_type: str  # pre_trade, post_trade, weekly_review, ad_hoc
    trade_ids: Optional[List[UUID]] = None
    messages: List[CoachMessage]
    key_insights: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None


class PreTradeReview(BaseModel):
    """Pre-trade review request."""
    asset: str
    side: str
    quantity: Decimal
    price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    position_size_pct: Optional[Decimal] = None
    thesis_id: Optional[UUID] = None
    conviction: Optional[int] = Field(None, ge=1, le=10)
    rationale: Optional[str] = None


class CoachResponse(BaseModel):
    """AI coach response."""
    recommendation: str  # go, caution, stop
    reasoning: str
    checklist_results: Optional[dict] = None
    warnings: Optional[List[str]] = None
