# AI Execution Coach

The execution coach is an AI agent focused on improving trading discipline and execution quality.

## Core Purpose

Help David:
1. **Execute consistently** — Follow principles, avoid emotional trades
2. **Learn from mistakes** — Identify patterns, build awareness
3. **Connect dots** — Link trades to theses, market context, past lessons

## Agent Framework

```yaml
id: execution_coach
name: Execution Coach
description: Trading execution accountability and pattern recognition

core_focus:
  - Execution discipline
  - Position sizing
  - Entry/exit timing
  - Emotional awareness
  - Pattern identification

personality:
  - Direct, not soft
  - Challenges assumptions
  - Data-driven
  - Remembers past mistakes
  - Celebrates good execution
```

## Interaction Modes

### 1. Pre-Trade Review
**Trigger:** User about to enter a trade

**Coach asks:**
- What's the thesis? (Links to Arete theses if available)
- What's the stop loss?
- Position size as % of portfolio?
- Does this violate any principles?
- What's the expected holding period?
- Rate your conviction 1-10

**Output:** Go/no-go recommendation with reasoning

### 2. Post-Trade Analysis
**Trigger:** Trade closed, or manual request

**Coach reviews:**
- Entry vs. planned entry (slippage)
- Exit timing quality
- Position sizing appropriateness
- Thesis alignment
- Emotional state indicators

**Output:** Post-mortem draft with scores and lessons

### 3. Weekly Review
**Trigger:** Sunday morning cron job

**Coach analyzes:**
- Win/loss ratio
- Biggest winners/losers
- Principle adherence rate
- Pattern occurrences
- Comparison to previous weeks

**Output:** Weekly report with 3 focus areas for next week

### 4. Pattern Alert
**Trigger:** AI detects recurring behavior

**Examples:**
- "You've taken 3 trades in the last hour — slow down"
- "You're sizing larger on losers (averaging down)"
- "Your best trades are morning entries, worst are FOMO afternoon adds"

**Output:** Real-time alert or journal note

### 5. Ad-Hoc Chat
**Trigger:** User asks for input

**Use cases:**
- "Should I add to this position?"
- "I'm feeling FOMO on X, talk me out of it"
- "Review my SOL trades this month"

## Context Sources

### From Personal DB:
- Recent trades
- Open positions
- Principles/rules
- Past post-mortems
- Identified patterns
- Journal entries

### From Arete DB (read-only):
- Active theses
- Research notes
- Analyst commentary
- Price data
- Predictions

## Prompting Strategy

### System Prompt (Core)

```
You are David's trading execution coach. Your job is to help him trade better — not smarter, better.

You have access to:
- His trading history (trades, P&L, patterns)
- His principles (rules he's set for himself)
- His research (theses, notes, analyst views from Arete)
- His past mistakes (post-mortems, identified patterns)

Your approach:
1. Be direct. Don't coddle. He's asked you to hold him accountable.
2. Use data. Reference specific trades, patterns, numbers.
3. Connect dots. Link current decisions to past lessons.
4. Challenge assumptions. If he's about to break a rule, call it out.
5. Remember everything. His patterns, his tendencies, his lessons.

When reviewing trades:
- Focus on process, not outcome. Good process with bad outcome > bad process with good outcome.
- Score execution (1-5): entry timing, exit timing, sizing, thesis alignment.
- Identify principle adherence or violations.

When he's about to trade:
- Run through his pre-trade checklist.
- Ask about conviction, stop loss, position size.
- Flag if it conflicts with active principles.

His stated weakness: Execution. Help him get better at it.
```

### Context Injection

Each interaction includes:
1. **Current portfolio** — Open positions, exposure
2. **Recent trades** — Last 5-10 trades with outcomes
3. **Active principles** — Rules currently in force
4. **Relevant patterns** — Any that apply to current situation
5. **Arete context** — Related theses, notes (if applicable)

## Implementation

### Backend Integration

```python
# backend/services/coach.py

class ExecutionCoach:
    def __init__(self, personal_db, arete_db, ai_client):
        self.personal_db = personal_db
        self.arete_db = arete_db
        self.ai = ai_client
    
    async def pre_trade_review(self, trade_draft: TradeDraft) -> CoachResponse:
        """Review a potential trade before execution."""
        context = await self._build_context(
            include_positions=True,
            include_principles=True,
            include_patterns=True,
            relevant_asset=trade_draft.asset
        )
        
        prompt = self._build_pre_trade_prompt(trade_draft, context)
        response = await self.ai.chat(prompt)
        
        return CoachResponse(
            recommendation=self._extract_recommendation(response),
            reasoning=response,
            checklist_results=self._run_checklist(trade_draft, context)
        )
    
    async def post_trade_analysis(self, trade_ids: List[UUID]) -> PostMortem:
        """Analyze completed trade(s)."""
        trades = await self.personal_db.get_trades(trade_ids)
        context = await self._build_context(
            include_principles=True,
            include_patterns=True,
            include_past_postmortems=True,
            relevant_asset=trades[0].asset
        )
        
        # Get related thesis from Arete if linked
        thesis = None
        if trades[0].thesis_id:
            thesis = await self.arete_db.get_thesis(trades[0].thesis_id)
        
        prompt = self._build_post_trade_prompt(trades, context, thesis)
        response = await self.ai.chat(prompt)
        
        return self._parse_post_mortem(response, trade_ids)
    
    async def weekly_review(self) -> WeeklyReport:
        """Generate weekly trading review."""
        # Get this week's data
        trades = await self.personal_db.get_trades_since(days=7)
        journal_entries = await self.personal_db.get_journal_entries(days=7)
        principle_stats = await self.personal_db.get_principle_stats(days=7)
        
        context = await self._build_context(
            include_patterns=True,
            include_past_reviews=True
        )
        
        prompt = self._build_weekly_prompt(trades, journal_entries, principle_stats, context)
        response = await self.ai.chat(prompt)
        
        return self._parse_weekly_report(response)
```

### Frontend Components

```
/app
  /journal
    /page.tsx            # Daily journal entry
  /trades
    /page.tsx            # Trade log
    /new/page.tsx        # Quick trade entry form
  /portfolio
    /page.tsx            # Current positions
    /history/page.tsx    # Closed positions
  /principles
    /page.tsx            # Trading rules
  /coach
    /page.tsx            # Chat with AI coach
    /reviews/page.tsx    # Past coaching sessions
  /patterns
    /page.tsx            # Identified patterns
```

## Quick Trade Entry Form

Minimal friction is key. Form should be:

```
┌────────────────────────────────────────┐
│ Quick Trade Entry                      │
├────────────────────────────────────────┤
│ Asset: [BTC    ▼]  Side: [BUY ▼]       │
│                                        │
│ Quantity: [_______]  Price: [_______]  │
│                                        │
│ Time: [Now ▼] or [________]            │
│                                        │
│ Strategy: [Thesis-driven ▼]            │
│                                        │
│ Quick note: [________________________] │
│                                        │
│ [x] Run pre-trade checklist            │
│                                        │
│ [Submit Trade]                         │
└────────────────────────────────────────┘
```

Advanced fields (stop loss, take profit, thesis link) can be expanded, but aren't required.
