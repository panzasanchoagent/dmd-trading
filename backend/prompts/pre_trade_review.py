"""
Pre-Trade Review Prompt Template.
Used for validating trades before execution.
"""

from typing import List, Optional
import json


def build_system_prompt(
    principles: List[dict],
    portfolio_summary: dict,
    recent_trades: List[dict],
    market_context: dict
) -> str:
    """Build the system prompt for pre-trade validation."""
    
    # Format principles
    principles_text = ""
    if principles:
        for p in principles:
            rule_type = "⚠️ HARD RULE" if p.get("rule_type") == "hard" else "Guideline"
            principles_text += f"\n- [{rule_type}] {p.get('title')}: {p.get('description')}"
            if p.get("quantifiable") and p.get("threshold"):
                principles_text += f" (Threshold: {p.get('metric')} ≤ {p.get('threshold')})"
    else:
        principles_text = "\nNo principles defined yet."
    
    # Format portfolio summary
    portfolio_text = ""
    if portfolio_summary:
        portfolio_text = f"""
Total Value: ${portfolio_summary.get('total_value', 0):,.2f}
Cash Available: ${portfolio_summary.get('cash', 0):,.2f}
Open Positions: {portfolio_summary.get('position_count', 0)}
Current Allocation:
  - Core: {portfolio_summary.get('core_pct', 0):.1f}%
  - Trading: {portfolio_summary.get('trading_pct', 0):.1f}%
  - Speculative: {portfolio_summary.get('speculative_pct', 0):.1f}%
  - Cash: {portfolio_summary.get('cash_pct', 0):.1f}%
"""
    else:
        portfolio_text = "\nPortfolio data not available."
    
    # Format recent trades
    recent_text = ""
    if recent_trades:
        for t in recent_trades[:5]:
            pnl = t.get('pnl', 0)
            pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
            recent_text += f"\n- {t.get('asset')} {t.get('side')}: {t.get('quantity')} @ ${t.get('price'):,.2f} ({pnl_str})"
    else:
        recent_text = "\nNo recent trades."
    
    # Format market context
    market_text = ""
    if market_context:
        btc = market_context.get('btc', {})
        eth = market_context.get('eth', {})
        market_text = f"""
BTC: ${btc.get('price', 0):,.2f} ({btc.get('change_24h', 0):+.1f}% 24h)
ETH: ${eth.get('price', 0):,.2f} ({eth.get('change_24h', 0):+.1f}% 24h)
Market Regime: {market_context.get('regime', 'Unknown')}
"""
    else:
        market_text = "\nMarket data not available."
    
    return f"""You are a trading coach reviewing a planned trade before execution.

Your role:
- Stress-test the thesis and validate the rationale
- Check risk parameters against defined principles
- Flag concerns honestly and directly
- If the trade looks solid, say so clearly

Be specific and actionable. Avoid generic advice.

═══════════════════════════════════════════════════════════════
TRADER'S PRINCIPLES
═══════════════════════════════════════════════════════════════
{principles_text}

═══════════════════════════════════════════════════════════════
POSITION SIZING RULES (Always enforce)
═══════════════════════════════════════════════════════════════
- Max single position: 20% of portfolio
- Max sector concentration: 40%
- Core positions: 60-80% allocation
- Trading positions: max 20% total
- Speculative: max 10% total

═══════════════════════════════════════════════════════════════
CURRENT PORTFOLIO STATE
═══════════════════════════════════════════════════════════════
{portfolio_text}

═══════════════════════════════════════════════════════════════
RECENT TRADE HISTORY (Last 5)
═══════════════════════════════════════════════════════════════
{recent_text}

═══════════════════════════════════════════════════════════════
MARKET CONTEXT
═══════════════════════════════════════════════════════════════
{market_text}

═══════════════════════════════════════════════════════════════

Evaluate the proposed trade and provide your recommendation.
Use this format:

**RECOMMENDATION: [GO / CAUTION / STOP]**

**Key Points:**
- Point 1
- Point 2

**Risk Checks:**
✓ or ✗ for each relevant principle

**Suggested Adjustments (if any):**
- Adjustment 1
"""
