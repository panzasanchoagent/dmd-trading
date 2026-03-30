"""
Weekly Analysis Prompt Template.
Used for conducting comprehensive weekly trading reviews.
"""

from typing import List, Optional
import json


def build_system_prompt(
    weekly_trades: List[dict],
    pnl_summary: dict,
    principles: List[dict],
    market_summary: dict
) -> str:
    """Build the system prompt for weekly analysis."""
    
    # Format weekly trades
    trades_text = ""
    if weekly_trades:
        for t in weekly_trades:
            pnl = t.get('pnl', 0)
            pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
            trades_text += f"""
---
{t.get('asset')} {t.get('side')} | {t.get('executed_at', '')[:10]}
Qty: {t.get('quantity')} @ ${t.get('price', 0):,.4f}
Strategy: {t.get('strategy', 'Not tagged')}
P&L: {pnl_str} ({t.get('pnl_pct', 0):+.1f}%)
Note: {t.get('entry_rationale', 'No notes')[:100]}
"""
    else:
        trades_text = "No trades executed this week."
    
    # Format P&L summary
    pnl_text = f"""
Total Realized P&L: ${pnl_summary.get('total_pnl', 0):,.2f}
Win Rate: {pnl_summary.get('win_rate', 0):.0f}%
Average Win: ${pnl_summary.get('avg_win', 0):,.2f}
Average Loss: ${pnl_summary.get('avg_loss', 0):,.2f}
Largest Win: ${pnl_summary.get('largest_win', 0):,.2f}
Largest Loss: ${pnl_summary.get('largest_loss', 0):,.2f}
Profit Factor: {pnl_summary.get('profit_factor', 0):.2f}
Total Trades: {pnl_summary.get('total_trades', 0)}
"""
    
    # Format principles adherence
    principles_text = ""
    if principles:
        for p in principles:
            followed = p.get('times_followed', 0)
            violated = p.get('times_violated', 0)
            total = followed + violated
            adherence = (followed / total * 100) if total > 0 else 100
            status = "✓" if adherence >= 80 else "⚠️" if adherence >= 50 else "✗"
            principles_text += f"\n{status} {p.get('title')}: {adherence:.0f}% adherence ({followed}/{total})"
    else:
        principles_text = "No principles defined yet."
    
    # Format market summary
    market_text = f"""
BTC Performance: {market_summary.get('btc_weekly_change', 0):+.1f}%
ETH Performance: {market_summary.get('eth_weekly_change', 0):+.1f}%
Market Regime: {market_summary.get('regime', 'Unknown')}
Volatility: {market_summary.get('volatility', 'Normal')}
"""
    
    return f"""You are conducting a comprehensive weekly trading review.

Your objectives:
1. Evaluate overall performance objectively
2. Identify recurring patterns (both strengths and weaknesses)
3. Assess principle adherence
4. Correlate performance with market conditions
5. Provide specific, actionable improvements for next week

Be direct and honest. Celebrate wins, but don't sugarcoat problems.
Focus on patterns and behaviors, not just outcomes.

═══════════════════════════════════════════════════════════════
PERFORMANCE SUMMARY
═══════════════════════════════════════════════════════════════
{pnl_text}

═══════════════════════════════════════════════════════════════
MARKET CONDITIONS THIS WEEK
═══════════════════════════════════════════════════════════════
{market_text}

═══════════════════════════════════════════════════════════════
PRINCIPLE ADHERENCE
═══════════════════════════════════════════════════════════════
{principles_text}

═══════════════════════════════════════════════════════════════
ALL TRADES THIS WEEK
═══════════════════════════════════════════════════════════════
{trades_text}

═══════════════════════════════════════════════════════════════

Provide your weekly review using this format:

**WEEK SUMMARY**
Brief overview of the week's trading (2-3 sentences).

**BY THE NUMBERS**
- Net P&L: $X,XXX
- Win Rate: XX%
- Best Trade: [Asset] (+$XXX)
- Worst Trade: [Asset] (-$XXX)

**BEST TRADE OF THE WEEK**
[Asset]: Why this was the best execution.
What made it work? What can be replicated?

**WORST TRADE OF THE WEEK**
[Asset]: What went wrong.
What can be learned? How to avoid repeating?

**PATTERNS IDENTIFIED**

Strengths (keep doing):
1. Pattern 1
2. Pattern 2

Weaknesses (address):
1. Pattern 1
2. Pattern 2

**PRINCIPLE ADHERENCE**
Which rules were followed? Which were broken?
Any principles that need adjustment?

**MARKET CORRELATION**
Did you trade with or against the market trend?
How did market conditions affect your decisions?

**ACTION ITEMS FOR NEXT WEEK**
1. Specific, actionable improvement #1
2. Specific, actionable improvement #2
3. Specific, actionable improvement #3

**OVERALL GRADE: [A/B/C/D/F]**
Brief justification (1 sentence).
"""
