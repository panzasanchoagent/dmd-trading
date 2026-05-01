import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.modules.setdefault('dotenv', types.SimpleNamespace(load_dotenv=lambda: None))
sys.modules.setdefault('db', types.SimpleNamespace(PersonalDB=object))

sys.path.insert(0, '/Users/dmd/dmd-trading/backend')

from scripts.cash_flow_ingestion import cash_flow_row_to_normalized, transform_cash_flows


class CashFlowIngestionTests(unittest.TestCase):
    def test_cash_flow_row_normalizes_deposit_and_tags(self):
        normalized = cash_flow_row_to_normalized({
            'executed_at': '2026-05-01T09:00:00Z',
            'flow_type': 'deposit',
            'asset': 'usd',
            'amount': '10000',
            'source_platform': 'bank_wire',
            'reference': 'initial_funding',
            'notes': 'Initial funding',
            'tags': 'funding,external_cash_flow',
        })

        self.assertEqual(normalized['flow_type'], 'DEPOSIT')
        self.assertEqual(normalized['asset'], 'USD')
        self.assertEqual(normalized['amount'], 10000.0)
        self.assertIn('external_cash_flow', normalized['tags'])
        self.assertEqual(normalized['executed_at'], '2026-05-01T09:00:00+00:00')

    def test_transform_cash_flows_reads_csv_end_to_end(self):
        csv_content = """executed_at,flow_type,asset,amount,source_platform,reference,notes,tags
2026-05-01T09:00:00Z,DEPOSIT,USD,10000,bank_wire,initial_funding,Initial funding,"funding,external_cash_flow"
2026-05-03T14:30:00Z,WITHDRAWAL,USDC,2500,hyperliquid,profit_sweep,Swept profits,"profit_sweep,external_cash_flow"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'cash_flows.csv'
            path.write_text(csv_content, encoding='utf-8')

            normalized = transform_cash_flows(path)

        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized[0]['flow_type'], 'DEPOSIT')
        self.assertEqual(normalized[1]['flow_type'], 'WITHDRAWAL')
        self.assertEqual(normalized[1]['asset'], 'USDC')


if __name__ == '__main__':
    unittest.main()
