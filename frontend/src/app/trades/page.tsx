'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

interface TradeRecord {
  id: string;
  asset: string;
  side: string;
  quantity: number;
  price: number;
  quote_currency?: string | null;
  executed_at: string;
  strategy?: string | null;
  timeframe?: string | null;
  source_platform?: string | null;
  cash_flow?: number | null;
}

interface TradesResponse {
  trades: TradeRecord[];
  total: number;
  offset: number;
  limit: number;
}

function formatCurrency(value: number | null | undefined, currency = 'USD') {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body?.detail || detail;
    } catch {
      // Ignore non-JSON errors.
    }
    throw new Error(detail);
  }
  return response.json();
}

export default function TradesPage() {
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assetFilter, setAssetFilter] = useState('ALL');
  const [strategyFilter, setStrategyFilter] = useState('ALL');
  const [dateFilter, setDateFilter] = useState('');

  useEffect(() => {
    async function loadTrades() {
      try {
        setLoading(true);
        const data = await fetchJson<TradesResponse>('/api/trades?limit=500');
        setTrades(data.trades || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load trades');
      } finally {
        setLoading(false);
      }
    }

    loadTrades();
  }, []);

  const assetOptions = useMemo(
    () => ['ALL', ...Array.from(new Set(trades.map((trade) => trade.asset).filter(Boolean))).sort()],
    [trades]
  );

  const strategyOptions = useMemo(
    () => ['ALL', ...Array.from(new Set(trades.map((trade) => trade.strategy).filter((value): value is string => Boolean(value)))).sort()],
    [trades]
  );

  const filteredTrades = useMemo(() => {
    return trades.filter((trade) => {
      if (assetFilter !== 'ALL' && trade.asset !== assetFilter) return false;
      if (strategyFilter !== 'ALL' && (trade.strategy || '') !== strategyFilter) return false;
      if (dateFilter && !trade.executed_at.startsWith(dateFilter)) return false;
      return true;
    });
  }, [trades, assetFilter, strategyFilter, dateFilter]);

  const totalCashFlow = useMemo(
    () => filteredTrades.reduce((sum, trade) => sum + (trade.cash_flow || 0), 0),
    [filteredTrades]
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trade Log</h1>
          <p className="text-sm text-gray-500">Showing {filteredTrades.length} of {trades.length} locally stored trades</p>
        </div>
        <Link
          href="/trades/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          + New Trade
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <SummaryCard label="Trades Loaded" value={String(filteredTrades.length)} />
        <SummaryCard label="Assets Traded" value={String(new Set(filteredTrades.map((trade) => trade.asset)).size)} />
        <SummaryCard label="Net Cash Flow" value={formatCurrency(totalCashFlow)} tone={totalCashFlow >= 0 ? 'positive' : 'negative'} />
      </div>

      <div className="flex flex-col gap-4 md:flex-row">
        <select className="px-3 py-2 border rounded-md bg-white" value={assetFilter} onChange={(event) => setAssetFilter(event.target.value)}>
          {assetOptions.map((asset) => (
            <option key={asset} value={asset}>{asset === 'ALL' ? 'All Assets' : asset}</option>
          ))}
        </select>
        <select className="px-3 py-2 border rounded-md bg-white" value={strategyFilter} onChange={(event) => setStrategyFilter(event.target.value)}>
          {strategyOptions.map((strategy) => (
            <option key={strategy} value={strategy}>{strategy === 'ALL' ? 'All Strategies' : strategy}</option>
          ))}
        </select>
        <input type="date" className="px-3 py-2 border rounded-md bg-white" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} />
      </div>

      {loading ? (
        <div className="animate-pulse text-khaki-600">Loading trades...</div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px]">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Asset</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Side</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Quantity</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Price</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Gross</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Cash Flow</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Strategy</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Timeframe</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Platform</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredTrades.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="px-4 py-8 text-center text-gray-500">No trades match the current filters.</td>
                  </tr>
                ) : (
                  filteredTrades.map((trade) => {
                    const gross = trade.quantity * trade.price;
                    return (
                      <tr key={trade.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm">{formatDate(trade.executed_at)}</td>
                        <td className="px-4 py-3 font-medium">{trade.asset}</td>
                        <td className={`px-4 py-3 font-medium ${trade.side === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>{trade.side}</td>
                        <td className="px-4 py-3 text-right">{trade.quantity.toLocaleString()}</td>
                        <td className="px-4 py-3 text-right">{formatCurrency(trade.price, trade.quote_currency || 'USD')}</td>
                        <td className="px-4 py-3 text-right">{formatCurrency(gross, trade.quote_currency || 'USD')}</td>
                        <td className={`px-4 py-3 text-right ${(trade.cash_flow || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatCurrency(trade.cash_flow, trade.quote_currency || 'USD')}</td>
                        <td className="px-4 py-3 text-sm">{trade.strategy || '—'}</td>
                        <td className="px-4 py-3 text-sm">{trade.timeframe || '—'}</td>
                        <td className="px-4 py-3 text-sm">{trade.source_platform || '—'}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'positive' | 'negative' }) {
  const toneClass = tone === 'positive' ? 'text-green-600' : tone === 'negative' ? 'text-red-600' : 'text-gray-900';
  return (
    <div className="rounded-lg border bg-white p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-2xl font-bold ${toneClass}`}>{value}</p>
    </div>
  );
}
