import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.modules.setdefault('dotenv', types.SimpleNamespace(load_dotenv=lambda: None))
sys.modules.setdefault('db', types.SimpleNamespace(PersonalDB=object))

sys.path.insert(0, '/Users/dmd/dmd-trading/backend')

from scripts.trade_ingestion import hyperliquid_trade_to_normalized, transform_hyperliquid


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

    def test_real_export_timestamp_format_is_supported(self):
        row = {
            'time': '14/01/2026 - 04:46:00',
            'coin': 'SOL',
            'dir': 'Open Long',
            'px': '180.5',
            'sz': '3',
            'ntl': '541.5',
            'fee': '0.2',
            'closedPnl': '',
        }

        normalized = hyperliquid_trade_to_normalized(row)

        self.assertEqual(normalized['executed_at'], '2026-01-14T04:46:00+00:00')
        self.assertEqual(normalized['side'], 'BUY')
        self.assertEqual(normalized['metadata']['source_trade']['raw_time'], row['time'])

    def test_transform_hyperliquid_reads_real_sample_shape_end_to_end(self):
        csv_content = """time,coin,dir,px,sz,ntl,fee,closedPnl
14/01/2026 - 04:46:00,BTC,Open Long,100000,0.1,10000,1,
14/01/2026 - 05:00:00,BTC,Close Long,101000,0.1,10100,1,100

"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'hyperliquid.csv'
            path.write_text(csv_content, encoding='utf-8')

            normalized = transform_hyperliquid(path)

        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized[0]['side'], 'BUY')
        self.assertEqual(normalized[0]['executed_at'], '2026-01-14T04:46:00+00:00')
        self.assertEqual(normalized[1]['side'], 'SELL')
        self.assertIn('has_closed_pnl', normalized[1]['tags'])


if __name__ == '__main__':
    unittest.main()
