"""
AI Coach Prompts for Trading Journal.
Structured prompts for different coaching modes.
"""

from .pre_trade_review import build_system_prompt as pre_trade_prompt
from .post_trade_review import build_system_prompt as post_trade_prompt
from .weekly_analysis import build_system_prompt as weekly_prompt

__all__ = ["pre_trade_prompt", "post_trade_prompt", "weekly_prompt"]
