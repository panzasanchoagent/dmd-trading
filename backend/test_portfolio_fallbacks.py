import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, '/Users/dmd/dmd-trading/backend')

from services import portfolio_service


class PortfolioFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_price_fallbacks_uses_static_prices(self):
        positions = [
            {"asset": "USD", "quantity": 48000.0, "avg_entry_price": 1.0, "total_cost_basis": 48000.0},
            {"asset": "USDC", "quantity": 1000.0, "avg_entry_price": 1.0, "total_cost_basis": 1000.0},
            {"asset": "WEAT", "quantity": 1000.0, "avg_entry_price": 23.1929, "total_cost_basis": 23192.9},
        ]

        enriched, total_value = portfolio_service.apply_price_fallbacks(positions, {})

        self.assertEqual(total_value, 72192.9)
        self.assertEqual(enriched[0]["current_price"], 1.0)
        self.assertEqual(enriched[0]["price_source"], "static_fallback")
        self.assertEqual(enriched[1]["current_price"], 1.0)
        self.assertEqual(enriched[1]["current_value"], 1000.0)
        self.assertEqual(enriched[2]["current_price"], 23.1929)
        self.assertEqual(enriched[2]["current_value"], 23192.9)

    async def test_get_latest_price_map_prefers_arete_market_tables(self):
        trades = [{"asset": "SOL", "price": 145.0, "executed_at": "2026-03-13T00:00:00+00:00"}]

        with patch.object(
            portfolio_service.arete_db,
            'get_current_prices',
            AsyncMock(return_value={
                'BTC': {"price": 60000.0, "source": 'arete_cmc_asset_data', "date": '2026-03-13'},
                'WEAT': {"price": 23.5, "source": 'arete_stock_ohlcv', "date": '2026-03-13'},
            }),
        ), patch.object(
            portfolio_service.personal_db,
            'get_all_trades_for_portfolio',
            AsyncMock(return_value=trades),
        ):
            prices = await portfolio_service.get_latest_price_map(['BTC', 'WEAT', 'SOL', 'USD', 'USDC'])

        self.assertEqual(prices['BTC']['source'], 'arete_cmc_asset_data')
        self.assertEqual(prices['WEAT']['source'], 'arete_stock_ohlcv')
        self.assertEqual(prices['SOL']['source'], 'latest_trade_price')
        self.assertEqual(prices['USD']['price'], 1.0)
        self.assertEqual(prices['USDC']['price'], 1.0)

    async def test_reconstruct_portfolio_state_supports_open_shorts(self):
        trades = [
            {
                "asset": "ETH",
                "side": "SELL",
                "quantity": 2.0,
                "price": 1000.0,
                "executed_at": "2026-03-11T00:00:00+00:00",
                "category": "Crypto - Hyperliquid",
                "source_platform": "hyperliquid",
            },
            {
                "asset": "ETH",
                "side": "BUY",
                "quantity": 1.0,
                "price": 900.0,
                "executed_at": "2026-03-12T00:00:00+00:00",
                "category": "Crypto - Hyperliquid",
                "source_platform": "hyperliquid",
            },
        ]

        with patch.object(portfolio_service.personal_db, 'list_position_seeds', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.personal_db, 'get_all_trades_for_portfolio', AsyncMock(return_value=trades)), \
             patch.object(portfolio_service.personal_db, 'list_cash_transactions', AsyncMock(return_value=[])):
            reconstruction = await portfolio_service.reconstruct_portfolio_state()

        positions = {position['asset']: position for position in reconstruction.positions}
        self.assertEqual(positions['ETH']['quantity'], -1.0)
        self.assertEqual(positions['ETH']['position_direction'], 'short')
        self.assertEqual(positions['ETH']['avg_entry_price'], 1000.0)
        self.assertEqual(positions['ETH']['total_cost_basis'], -1000.0)
        self.assertEqual(positions['USD']['quantity'], 1100.0)

    async def test_reconstruct_portfolio_state_tracks_usdc_cash_and_book_classification(self):
        trades = [
            {
                "asset": "HYPE",
                "side": "BUY",
                "quantity": 100.0,
                "price": 20.0,
                "quote_currency": "USDC",
                "executed_at": "2026-03-11T00:00:00+00:00",
                "category": "Crypto - Hyperliquid",
                "source_platform": "hyperliquid",
                "tags": ["category:crypto-hyperliquid"],
            },
            {
                "asset": "HYPE",
                "side": "SELL",
                "quantity": 100.0,
                "price": 21.0,
                "quote_currency": "USDC",
                "executed_at": "2026-03-12T00:00:00+00:00",
                "category": "Crypto - Hyperliquid",
                "source_platform": "hyperliquid",
                "tags": ["category:crypto-hyperliquid"],
            },
        ]

        with patch.object(portfolio_service.personal_db, 'list_position_seeds', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.personal_db, 'get_all_trades_for_portfolio', AsyncMock(return_value=trades)), \
             patch.object(portfolio_service.personal_db, 'list_cash_transactions', AsyncMock(return_value=[])):
            reconstruction = await portfolio_service.reconstruct_portfolio_state()

        positions = {position['asset']: position for position in reconstruction.positions}
        self.assertNotIn('USD', positions)
        self.assertEqual(positions['USDC']['quantity'], 100.0)
        self.assertEqual(positions['USDC']['part_of_book'], 'crypto')
        self.assertEqual(reconstruction.closed_positions[0]['part_of_book'], 'crypto')

    async def test_nav_history_uses_arete_prices_for_open_short(self):
        trades = [
            {
                "asset": "ETH",
                "side": "SELL",
                "quantity": 1.0,
                "price": 1000.0,
                "executed_at": "2026-03-11T00:00:00+00:00",
                "category": "Crypto - Hyperliquid",
                "source_platform": "hyperliquid",
            },
        ]

        class FixedDate(portfolio_service.date):
            @classmethod
            def today(cls):
                return cls(2026, 3, 13)

        reconstruction = type('R', (), {"positions": [{"asset": "ETH"}, {"asset": "USD"}], "source": "trades_only"})()

        with patch.object(portfolio_service, 'reconstruct_portfolio_state', AsyncMock(return_value=reconstruction)), \
             patch.object(portfolio_service.personal_db, 'list_position_seeds', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.personal_db, 'get_all_trades_for_portfolio', AsyncMock(return_value=trades)), \
             patch.object(portfolio_service.personal_db, 'list_cash_transactions', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.arete_db, 'get_stock_price_history', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.arete_db, 'get_price_history', AsyncMock(return_value=[
                 {"date": '2026-03-11', "price": 1000.0},
                 {"date": '2026-03-12', "price": 900.0},
                 {"date": '2026-03-13', "price": 800.0},
             ])), \
             patch.object(portfolio_service, 'date', FixedDate):
            history, source = await portfolio_service.compute_daily_nav_history(days=3)

        self.assertEqual(source, 'trades_only')
        self.assertEqual(history[0]['date'], '2026-03-11')
        self.assertAlmostEqual(history[0]['nav'], 0.0, places=4)
        self.assertAlmostEqual(history[1]['nav'], 100.0, places=4)
        self.assertAlmostEqual(history[2]['nav'], 200.0, places=4)

    async def test_nav_history_marks_usdc_cash_daily(self):
        trades = [
            {
                "asset": "HYPE",
                "side": "BUY",
                "quantity": 10.0,
                "price": 20.0,
                "quote_currency": "USDC",
                "executed_at": "2026-03-11T00:00:00+00:00",
                "category": "Crypto - Hyperliquid",
                "source_platform": "hyperliquid",
            },
        ]

        class FixedDate(portfolio_service.date):
            @classmethod
            def today(cls):
                return cls(2026, 3, 13)

        reconstruction = type('R', (), {"positions": [{"asset": "HYPE"}, {"asset": "USDC"}], "source": "trades_only"})()

        with patch.object(portfolio_service, 'reconstruct_portfolio_state', AsyncMock(return_value=reconstruction)), \
             patch.object(portfolio_service.personal_db, 'list_position_seeds', AsyncMock(return_value=[{
                 "asset": "USDC",
                 "quantity": 1000.0,
                 "avg_entry_price": 1.0,
                 "first_entry_date": "2026-03-10T00:00:00+00:00",
                 "last_trade_date": "2026-03-10T00:00:00+00:00",
             }])), \
             patch.object(portfolio_service.personal_db, 'get_all_trades_for_portfolio', AsyncMock(return_value=trades)), \
             patch.object(portfolio_service.personal_db, 'list_cash_transactions', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.arete_db, 'get_stock_price_history', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.arete_db, 'get_price_history', AsyncMock(return_value=[
                 {"date": '2026-03-11', "price": 20.0},
                 {"date": '2026-03-12', "price": 25.0},
                 {"date": '2026-03-13', "price": 30.0},
             ])), \
             patch.object(portfolio_service, 'date', FixedDate):
            history, _ = await portfolio_service.compute_daily_nav_history(days=3)

        self.assertAlmostEqual(history[0]['nav'], 1000.0, places=4)
        self.assertAlmostEqual(history[1]['nav'], 1050.0, places=4)
        self.assertAlmostEqual(history[2]['nav'], 1100.0, places=4)

    async def test_external_cash_flows_affect_cash_ledger_without_creating_trades(self):
        cash_transactions = [
            {
                "asset": "USD",
                "flow_type": "DEPOSIT",
                "amount": 1000.0,
                "executed_at": "2026-03-10T00:00:00+00:00",
            },
            {
                "asset": "USD",
                "flow_type": "WITHDRAWAL",
                "amount": 250.0,
                "executed_at": "2026-03-11T00:00:00+00:00",
            },
        ]

        with patch.object(portfolio_service.personal_db, 'list_position_seeds', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.personal_db, 'get_all_trades_for_portfolio', AsyncMock(return_value=[])), \
             patch.object(portfolio_service.personal_db, 'list_cash_transactions', AsyncMock(return_value=cash_transactions)):
            reconstruction = await portfolio_service.reconstruct_portfolio_state()

        positions = {position['asset']: position for position in reconstruction.positions}
        self.assertEqual(positions['USD']['quantity'], 750.0)
        self.assertEqual(positions['USD']['position_type'], 'cash')
        self.assertEqual(reconstruction.closed_positions, [])


if __name__ == '__main__':
    unittest.main()
