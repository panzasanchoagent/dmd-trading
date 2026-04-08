import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, '/Users/dmd/dmd-trading/backend')

from services import portfolio_service


class PortfolioFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_price_fallbacks_uses_static_prices(self):
        positions = [
            {"asset": "USD", "quantity": 48000.0, "avg_entry_price": 1.0, "total_cost_basis": 48000.0},
            {"asset": "WEAT", "quantity": 1000.0, "avg_entry_price": 23.1929, "total_cost_basis": 23192.9},
        ]

        enriched, total_value = portfolio_service.apply_price_fallbacks(positions, {})

        self.assertEqual(total_value, 71192.9)
        self.assertEqual(enriched[0]["current_price"], 1.0)
        self.assertEqual(enriched[0]["price_source"], "static_fallback")
        self.assertEqual(enriched[1]["current_price"], 23.1929)
        self.assertEqual(enriched[1]["current_value"], 23192.9)

    async def test_nav_history_uses_static_price_until_sold(self):
        seed_positions = [
            {
                "asset": "USD",
                "quantity": 48000.0,
                "avg_entry_price": 1.0,
                "first_entry_date": "2026-01-01T00:00:00+00:00",
                "last_trade_date": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ]
        trades = [
            {
                "asset": "SSV",
                "side": "BUY",
                "quantity": 2000.0,
                "price": 0.7961051,
                "executed_at": "2026-01-26T09:50:23+00:00",
            },
            {
                "asset": "SSV",
                "side": "SELL",
                "quantity": 2000.0,
                "price": 0.45508981,
                "executed_at": "2026-03-12T14:18:38+00:00",
            },
        ]

        with patch.object(portfolio_service, 'reconstruct_portfolio_state', AsyncMock(return_value=type('R', (), {"positions": [{"asset": "USD"}], "source": "positions_plus_trades"})())), \
             patch.object(portfolio_service.personal_db, 'list_position_seeds', AsyncMock(return_value=seed_positions)), \
             patch.object(portfolio_service.personal_db, 'get_all_trades_for_portfolio', AsyncMock(return_value=trades)), \
             patch.object(portfolio_service.personal_db, 'get_stock_price_history', AsyncMock(return_value=[])):
            history, source = await portfolio_service.compute_daily_nav_history(days=90)

        jan_27 = next(point for point in history if point['date'] == '2026-01-27')
        mar_13 = next(point for point in history if point['date'] == '2026-03-13')

        self.assertEqual(source, 'positions_plus_trades')
        self.assertAlmostEqual(jan_27['nav'], 48000.0, places=4)
        self.assertAlmostEqual(mar_13['nav'], 47317.9694, places=4)


if __name__ == '__main__':
    unittest.main()
