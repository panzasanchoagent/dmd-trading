import sys
import unittest

sys.path.insert(0, '/Users/dmd/dmd-trading/backend')

from scripts.trade_ingestion import hyperliquid_trade_to_normalized


class HyperliquidIngestionTests(unittest.TestCase):
    def test_long_and_short_dirs_map_to_buy_sell_sides(self):
        open_long = hyperliquid_trade_to_normalized({
            'coin': 'BTC',
            'dir': 'Open Long',
            'px': '100000',
            'sz': '0.1',
            'ntl': '10000',
            'fee': '1',
            'closedPnl': '',
            'time': '2026-05-01 10:00:00',
        })
        close_long = hyperliquid_trade_to_normalized({
            'coin': 'BTC',
            'dir': 'Close Long',
            'px': '101000',
            'sz': '0.1',
            'ntl': '10100',
            'fee': '1',
            'closedPnl': '100',
            'time': '2026-05-01 11:00:00',
        })
        open_short = hyperliquid_trade_to_normalized({
            'coin': 'ETH',
            'dir': 'Open Short',
            'px': '2000',
            'sz': '2',
            'ntl': '4000',
            'fee': '2',
            'closedPnl': '',
            'time': '2026-05-01 12:00:00',
        })
        close_short = hyperliquid_trade_to_normalized({
            'coin': 'ETH',
            'dir': 'Close Short',
            'px': '1900',
            'sz': '2',
            'ntl': '3800',
            'fee': '2',
            'closedPnl': '200',
            'time': '2026-05-01 13:00:00',
        })

        self.assertEqual(open_long['side'], 'BUY')
        self.assertEqual(close_long['side'], 'SELL')
        self.assertEqual(open_short['side'], 'SELL')
        self.assertEqual(close_short['side'], 'BUY')
        self.assertEqual(open_short['metadata']['source_trade']['trade_intent'], 'open_short')
        self.assertIn('Hyperliquid direction: Open Short', open_short['entry_rationale'])
        self.assertIn('hyperliquid:close_short', close_short['tags'])


if __name__ == '__main__':
    unittest.main()
