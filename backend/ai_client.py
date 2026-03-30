"""
AI Coach Client for Trading Journal.
Pattern: OpenClaw CLI first, fallback to direct Anthropic API.
"""

import os
import json
import subprocess
import logging
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Default model for AI coaching
DEFAULT_MODEL = "claude-opus-4-5"


class AIClientError(Exception):
    """Custom exception for AI client errors."""
    pass


class AICoachClient:
    """
    AI coaching client with dual-mode execution:
    1. Primary: OpenClaw CLI (uses existing session/auth)
    2. Fallback: Direct Anthropic API
    """
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._anthropic_client = None
    
    @property
    def anthropic_client(self):
        """Lazy-load Anthropic client."""
        if self._anthropic_client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    # Try keychain
                    try:
                        result = subprocess.run(
                            ["security", "find-generic-password", 
                             "-s", "anthropic-api", "-a", "anthropic", "-w"],
                            capture_output=True, text=True, check=True
                        )
                        api_key = result.stdout.strip()
                    except subprocess.CalledProcessError:
                        pass
                
                if api_key:
                    self._anthropic_client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                logger.warning("anthropic package not installed")
        return self._anthropic_client
    
    async def send_message(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None
    ) -> dict:
        """
        Send a message to the AI coach.
        Returns: {"content": str, "model": str, "tokens_used": int}
        """
        # Try OpenClaw CLI first
        result = await self._try_openclaw(system_prompt, user_message, conversation_history)
        if result:
            return result
        
        # Fallback to direct Anthropic API
        result = await self._try_anthropic(system_prompt, user_message, conversation_history)
        if result:
            return result
        
        raise AIClientError("All AI providers failed")
    
    async def _try_openclaw(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None
    ) -> Optional[dict]:
        """Try sending via OpenClaw CLI."""
        try:
            # Build the full prompt with context
            full_message = self._build_message(system_prompt, user_message, conversation_history)
            
            # Call OpenClaw CLI
            result = subprocess.run(
                [
                    "openclaw", "sessions", "send",
                    "--model", self.model,
                    "--message", full_message
                ],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0 and result.stdout:
                return {
                    "content": result.stdout.strip(),
                    "model": self.model,
                    "tokens_used": None,  # CLI doesn't report tokens
                    "provider": "openclaw"
                }
            
            logger.warning(f"OpenClaw CLI failed: {result.stderr}")
            return None
            
        except subprocess.TimeoutExpired:
            logger.warning("OpenClaw CLI timed out")
            return None
        except FileNotFoundError:
            logger.warning("OpenClaw CLI not found")
            return None
        except Exception as e:
            logger.warning(f"OpenClaw CLI error: {e}")
            return None
    
    async def _try_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None
    ) -> Optional[dict]:
        """Try sending via direct Anthropic API."""
        if not self.anthropic_client:
            return None
        
        try:
            # Build messages array
            messages = []
            if conversation_history:
                for msg in conversation_history:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",  # Fallback model
                max_tokens=4096,
                system=system_prompt,
                messages=messages
            )
            
            content = response.content[0].text if response.content else ""
            tokens = response.usage.input_tokens + response.usage.output_tokens
            
            return {
                "content": content,
                "model": response.model,
                "tokens_used": tokens,
                "provider": "anthropic"
            }
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return None
    
    def _build_message(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None
    ) -> str:
        """Build full message for CLI (includes system prompt in message)."""
        parts = []
        
        # System context
        parts.append(f"<system>\n{system_prompt}\n</system>\n")
        
        # Conversation history
        if conversation_history:
            parts.append("<conversation>")
            for msg in conversation_history:
                role = msg.get("role", "user").upper()
                content = msg.get("content", "")
                parts.append(f"\n[{role}]: {content}")
            parts.append("\n</conversation>\n")
        
        # Current message
        parts.append(f"<user_message>\n{user_message}\n</user_message>")
        
        return "\n".join(parts)


class PreTradeCoach:
    """Specialized coach for pre-trade validation."""
    
    def __init__(self, ai_client: AICoachClient = None):
        self.client = ai_client or AICoachClient()
    
    async def validate(
        self,
        trade_plan: dict,
        principles: List[dict],
        portfolio_summary: dict,
        recent_trades: List[dict],
        market_context: dict
    ) -> dict:
        """Validate a planned trade against principles and context."""
        from prompts.pre_trade_review import build_system_prompt
        
        system_prompt = build_system_prompt(
            principles=principles,
            portfolio_summary=portfolio_summary,
            recent_trades=recent_trades,
            market_context=market_context
        )
        
        user_message = f"""Please review this planned trade:

Asset: {trade_plan.get('asset')}
Side: {trade_plan.get('side')}
Quantity: {trade_plan.get('quantity')}
Price: {trade_plan.get('price')}
Stop Loss: {trade_plan.get('stop_loss', 'Not set')}
Take Profit: {trade_plan.get('take_profit', 'Not set')}
Position Size: {trade_plan.get('position_size_pct', 'Not specified')}% of portfolio
Conviction: {trade_plan.get('conviction', 'Not rated')}/10

Rationale: {trade_plan.get('rationale', 'None provided')}

Please provide:
1. Your recommendation (GO / CAUTION / STOP)
2. Key concerns or validations
3. Checklist verification
4. Suggested adjustments if any
"""
        
        response = await self.client.send_message(system_prompt, user_message)
        
        # Parse recommendation from response
        content = response["content"]
        recommendation = "caution"  # Default
        if "STOP" in content.upper()[:100]:
            recommendation = "stop"
        elif "GO" in content.upper()[:100] and "CAUTION" not in content.upper()[:100]:
            recommendation = "go"
        
        return {
            "recommendation": recommendation,
            "reasoning": content,
            "model_used": response["model"],
            "tokens_used": response.get("tokens_used")
        }


class PostTradeCoach:
    """Specialized coach for post-trade analysis."""
    
    def __init__(self, ai_client: AICoachClient = None):
        self.client = ai_client or AICoachClient()
    
    async def analyze(
        self,
        trade: dict,
        market_context: dict,
        similar_trades: List[dict] = None
    ) -> dict:
        """Analyze a completed trade for lessons."""
        from prompts.post_trade_review import build_system_prompt
        
        system_prompt = build_system_prompt(
            trade_details=trade,
            market_context=market_context,
            similar_trades=similar_trades or []
        )
        
        user_message = f"""Please analyze this completed trade:

Asset: {trade.get('asset')}
Side: {trade.get('side')}
Entry Price: {trade.get('entry_price')}
Exit Price: {trade.get('exit_price')}
Quantity: {trade.get('quantity')}
P&L: {trade.get('pnl')} ({trade.get('pnl_pct')}%)
Holding Period: {trade.get('holding_days')} days

Original Thesis: {trade.get('entry_rationale', 'Not recorded')}

Please provide:
1. Entry quality assessment (1-5)
2. Exit quality assessment (1-5)
3. What went well
4. What could improve
5. Key lesson to remember
6. Patterns to watch for
"""
        
        response = await self.client.send_message(system_prompt, user_message)
        
        return {
            "analysis": response["content"],
            "model_used": response["model"],
            "tokens_used": response.get("tokens_used")
        }


class WeeklyCoach:
    """Specialized coach for weekly review analysis."""
    
    def __init__(self, ai_client: AICoachClient = None):
        self.client = ai_client or AICoachClient()
    
    async def analyze_week(
        self,
        weekly_trades: List[dict],
        pnl_summary: dict,
        principles: List[dict],
        market_summary: dict,
        patterns: List[dict] = None
    ) -> dict:
        """Conduct weekly trading review."""
        from prompts.weekly_analysis import build_system_prompt
        
        system_prompt = build_system_prompt(
            weekly_trades=weekly_trades,
            pnl_summary=pnl_summary,
            principles=principles,
            market_summary=market_summary
        )
        
        # Build trade summary
        trade_list = []
        for t in weekly_trades:
            trade_list.append(
                f"- {t.get('asset')} {t.get('side')}: {t.get('quantity')} @ {t.get('price')} "
                f"({t.get('executed_at', '')[:10]})"
            )
        
        user_message = f"""Weekly Review Request

Period: Last 7 days
Total Trades: {len(weekly_trades)}
Net P&L: ${pnl_summary.get('total_pnl', 0):,.2f} ({pnl_summary.get('total_pnl_pct', 0):.1f}%)
Win Rate: {pnl_summary.get('win_rate', 0):.0f}%

Trades:
{chr(10).join(trade_list) if trade_list else "No trades this week"}

Known Patterns Being Tracked:
{chr(10).join(f"- {p.get('name')}: {p.get('description')}" for p in (patterns or [])) or "None tracked yet"}

Please provide:
1. Week summary and key stats
2. Best trade of the week (and why)
3. Worst trade of the week (and why)
4. Recurring patterns identified
5. Principle adherence assessment
6. 3 specific, actionable improvements for next week
"""
        
        response = await self.client.send_message(system_prompt, user_message)
        
        return {
            "analysis": response["content"],
            "model_used": response["model"],
            "tokens_used": response.get("tokens_used")
        }


class AdHocCoach:
    """General-purpose coaching conversations."""
    
    def __init__(self, ai_client: AICoachClient = None):
        self.client = ai_client or AICoachClient()
    
    async def chat(
        self,
        message: str,
        context: dict = None,
        conversation_history: List[dict] = None
    ) -> dict:
        """Have a coaching conversation."""
        system_prompt = """You are an experienced trading coach. 
Your role is to help the trader improve their execution, psychology, and decision-making.

Be direct, honest, and constructive. Focus on actionable advice.
If you notice concerning patterns, point them out diplomatically but clearly.

Context about this trader's current state:
"""
        
        if context:
            if context.get("portfolio_value"):
                system_prompt += f"\nPortfolio Value: ${context['portfolio_value']:,.2f}"
            if context.get("open_positions"):
                system_prompt += f"\nOpen Positions: {context['open_positions']}"
            if context.get("recent_pnl"):
                system_prompt += f"\nRecent P&L: ${context['recent_pnl']:,.2f}"
            if context.get("known_patterns"):
                system_prompt += f"\nKnown Patterns: {', '.join(context['known_patterns'])}"
        
        response = await self.client.send_message(
            system_prompt, 
            message,
            conversation_history
        )
        
        return {
            "response": response["content"],
            "model_used": response["model"],
            "tokens_used": response.get("tokens_used")
        }


# Singleton instances
def get_ai_client(model: str = DEFAULT_MODEL) -> AICoachClient:
    return AICoachClient(model=model)


def get_pre_trade_coach() -> PreTradeCoach:
    return PreTradeCoach()


def get_post_trade_coach() -> PostTradeCoach:
    return PostTradeCoach()


def get_weekly_coach() -> WeeklyCoach:
    return WeeklyCoach()


def get_adhoc_coach() -> AdHocCoach:
    return AdHocCoach()
