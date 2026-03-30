"""Trading Journal API Routers."""

from .trades import router as trades_router
from .portfolio import router as portfolio_router
from .journal import router as journal_router
from .principles import router as principles_router
from .coach import router as coach_router

__all__ = [
    "trades_router",
    "portfolio_router", 
    "journal_router",
    "principles_router",
    "coach_router"
]
