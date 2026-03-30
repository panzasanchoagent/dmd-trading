"""
Post-Trade Review Prompt Template.
Used for analyzing completed trades and extracting lessons.
"""

from typing import List, Optional
import json


def build_system_prompt(
    trade_details: dict,
    market_context: dict,
    similar_trades: List[dict]
) -> str:
    """Build the system prompt for post-trade analysis."""
    
    # Format trade details
    trade_text = f"""
Asset: {trade_details.get('asset', 'Unknown')}
Side: {trade_details.get('side', 'Unknown')}
Entry: ${trade_details.get('entry_price', 0):,.4f} on {trade_details.get('entry_date', 'Unknown')}
Exit: ${trade_details.get('exit_price', 0):,.4f} on {trade_details.get('exit_date', 'Unknown')}
Quantity: {trade_details.get('quantity', 0)}
Position Size: {trade_details.get('position_size_pct', 'Unknown')}% of portfolio

Realized P&L: ${trade_details.get('pnl', 0):,.2f} ({trade_details.get('pnl_pct', 0):+.2f}%)
Holding Period: {trade_details.get('holding_days', 0)} days

Original Entry Rationale:
{trade_details.get('entry_rationale', 'Not recorded')}

Stop Loss Set: ${trade_details.get('stop_loss', 'Not set')}
Take Profit Set: ${trade_details.get('take_profit', 'Not set')}
Strategy: {trade_details.get('strategy', 'Not specified')}
"""
    
    # Format market context
    market_text = ""
    if market_context:
        entry_ctx = market_context.get('at_entry', {})
        exit_ctx = market_context.get('at_exit', {})
        market_text = f"""
At Entry:
- BTC: ${entry_ctx.get('btc_price', 0):,.2f}
- ETH: ${entry_ctx.get('eth_price', 0):,.2f}
- Regime: {entry_ctx.get('regime', 'Unknown')}

At Exit:
- BTC: ${exit_ctx.get('btc_price', 0):,.2f}
- ETH: ${exit_ctx.get('eth_price', 0):,.2f}
- Regime: {exit_ctx.get('regime', 'Unknown')}

BTC Change During Hold: {market_context.get('btc_change_pct', 0):+.1f}%
"""
    else:
        market_text = "Market data not available."
    
    # Format similar trades
    similar_text = ""
    if similar_trades:
        for t in similar_trades[:5]:
            result = "WIN" if t.get('pnl', 0) > 0 else "LOSS"
            similar_text += f"\n- {t.get('asset')} ({t.get('strategy', 'N/A')}): {result} {t.get('pnl_pct', 0):+.1f}% over {t.get('holding_days', '?')} days"
    else:
        similar_text = "No similar historical trades found."
    
    return f"""You are analyzing a completed trade to extract actionable lessons.

Your focus areas:
1. Entry Quality - Was timing good? Was the entry price optimal?
2. Exit Quality - Did the trader exit well? Too early? Too late?
3. Sizing - Was position size appropriate for the conviction/risk?
4. Thesis Quality - Was the original thesis correct? If not, what was missed?
5. Emotional Factors - Signs of FOMO, fear, revenge trading, or patience?

Be specific about what worked and what didn't.
Identify patterns that might apply to future trades.

═══════════════════════════════════════════════════════════════
THE TRADE
═══════════════════════════════════════════════════════════════
{trade_text}

═══════════════════════════════════════════════════════════════
MARKET CONDITIONS
═══════════════════════════════════════════════════════════════
{market_text}

═══════════════════════════════════════════════════════════════
SIMILAR PAST TRADES
═══════════════════════════════════════════════════════════════
{similar_text}

═══════════════════════════════════════════════════════════════

Analyze this trade using this format:

**TRADE RESULT: [WIN/LOSS/BREAKEVEN]**

**Quality Scores (1-5):**
- Entry: X/5 - [brief reason]
- Exit: X/5 - [brief reason]
- Sizing: X/5 - [brief reason]
- Thesis: X/5 - [brief reason]

**What Went Well:**
- Point 1
- Point 2

**What Could Improve:**
- Point 1
- Point 2

**Key Lesson:**
One specific, memorable takeaway from this trade.

**Patterns to Watch:**
Any recurring themes compared to similar trades.

**Emotional Flags (if any):**
Signs of FOMO, fear, revenge trading, overconfidence, etc.
"""
