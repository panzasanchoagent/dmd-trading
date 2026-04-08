'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface Position {
  asset: string;
  quantity: number;
  avg_entry_price: number | null;
  current_price: number | null;
  current_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  allocation_pct: number | null;
  position_type: string | null;
  first_entry_date?: string | null;
  last_trade_date?: string | null;
  number_of_trades?: number;
  price_source?: string;
}

interface ClosedPosition {
  asset: string;
  entry_date: string | null;
  exit_date: string | null;
  realized_pnl: number | null;
  realized_pnl_pct: number | null;
  holding_period_days: number | null;
  number_of_trades: number;
  win_loss: string | null;
}

interface NavPoint {
  date: string;
  nav: number;
  priced_assets: number;
  total_assets: number;
}

interface PositionsResponse {
  positions: Position[];
  total_value: number;
  position_count: number;
  source?: string;
}

interface ClosedResponse {
  closed_positions: ClosedPosition[];
  total_count: number;
  total_realized_pnl: number;
  win_rate: number;
}

interface NavHistoryResponse {
  history: NavPoint[];
  gap?: string;
}

interface PerformanceResponse {
  total_trades: number;
  total_realized_pnl: number;
  win_rate: number;
  expectancy: number;
  profit_factor: number;
}

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${value.toFixed(1)}%`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
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

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [source, setSource] = useState<string | null>(null);
  const [closedPositions, setClosedPositions] = useState<ClosedPosition[]>([]);
  const [navHistory, setNavHistory] = useState<NavPoint[]>([]);
  const [navGap, setNavGap] = useState<string | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPortfolio() {
      try {
        setLoading(true);
        const [positionsData, closedData, navData, performanceData] = await Promise.all([
          fetchJson<PositionsResponse>('/api/portfolio/positions'),
          fetchJson<ClosedResponse>('/api/portfolio/closed?limit=10'),
          fetchJson<NavHistoryResponse>('/api/portfolio/nav-history?days=90'),
          fetchJson<PerformanceResponse>('/api/portfolio/performance?days=365'),
        ]);

        setPositions(positionsData.positions || []);
        setTotalValue(positionsData.total_value || 0);
        setSource(positionsData.source || null);
        setClosedPositions(closedData.closed_positions || []);
        setNavHistory(navData.history || []);
        setNavGap(navData.gap || null);
        setPerformance(performanceData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load portfolio');
      } finally {
        setLoading(false);
      }
    }

    loadPortfolio();
  }, []);

  const totalUnrealizedPnL = useMemo(
    () => positions.reduce((sum, position) => sum + (position.unrealized_pnl || 0), 0),
    [positions]
  );

  const latestNav = navHistory.length ? navHistory[navHistory.length - 1]?.nav || 0 : totalValue;

  if (loading) {
    return <div className="animate-pulse text-khaki-600">Loading portfolio...</div>;
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-gray-900">Portfolio</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio</h1>
          {source && (
            <p className="text-sm text-gray-500">
              Source: {source === 'positions_plus_trades'
                ? 'reconstructed from seeded positions plus local trades'
                : source === 'positions_only'
                  ? 'seeded positions only'
                  : 'local trades only'}
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">Total Value</p>
          <p className="text-2xl font-bold">{formatCurrency(totalValue)}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">Unrealized P&amp;L</p>
          <p className={`text-2xl font-bold ${totalUnrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(totalUnrealizedPnL)}
          </p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">Closed Trades</p>
          <p className="text-2xl font-bold">{performance?.total_trades ?? closedPositions.length}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">Win Rate</p>
          <p className="text-2xl font-bold">{formatPct(performance?.win_rate)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-lg border bg-white p-4 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">NAV history</h2>
              <p className="text-sm text-gray-500">90 day reconstructed portfolio value</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-wide text-gray-400">Latest NAV</p>
              <p className="text-lg font-semibold">{formatCurrency(latestNav)}</p>
            </div>
          </div>
          {navHistory.length > 0 ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={navHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} minTickGap={24} />
                  <YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Legend />
                  <Line type="monotone" dataKey="nav" name="NAV" stroke="#2563eb" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-6 text-sm text-gray-500">
              {navGap || 'No NAV history available yet.'}
            </div>
          )}
        </div>

        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-lg font-semibold text-gray-900">Performance</h2>
          <div className="mt-4 space-y-3 text-sm">
            <div className="flex items-center justify-between"><span className="text-gray-500">Realized P&amp;L</span><span className="font-medium">{formatCurrency(performance?.total_realized_pnl)}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-500">Expectancy</span><span className="font-medium">{formatCurrency(performance?.expectancy)}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-500">Profit factor</span><span className="font-medium">{performance?.profit_factor === Infinity ? '∞' : performance?.profit_factor?.toFixed(2) ?? '—'}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-500">Open positions</span><span className="font-medium">{positions.length}</span></div>
          </div>
        </div>
      </div>

      <div className="rounded-lg border bg-white overflow-hidden">
        <div className="border-b px-4 py-3">
          <h2 className="text-lg font-semibold text-gray-900">Open positions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1000px]">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Asset</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">First Entry</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Last Trade</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Quantity</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Avg Entry</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Current</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Value</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">P&amp;L</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Allocation</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {positions.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                    No open positions yet. Add trades or seed the positions table.
                  </td>
                </tr>
              ) : (
                positions.map((position) => (
                  <tr key={position.asset} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{position.asset}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatDate(position.first_entry_date)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatDate(position.last_trade_date)}</td>
                    <td className="px-4 py-3 text-right">{position.quantity.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(position.avg_entry_price)}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(position.current_price)}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(position.current_value)}</td>
                    <td className={`px-4 py-3 text-right ${(position.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(position.unrealized_pnl)} ({formatPct(position.unrealized_pnl_pct)})
                    </td>
                    <td className="px-4 py-3 text-right">{formatPct(position.allocation_pct)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className="rounded bg-gray-100 px-2 py-1 text-xs">{position.position_type || 'unclassified'}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-lg border bg-white overflow-hidden">
        <div className="border-b px-4 py-3">
          <h2 className="text-lg font-semibold text-gray-900">Recent closed positions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px]">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Asset</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Entry</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Exit</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Trades</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Holding Days</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Realized P&amp;L</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {closedPositions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">No closed positions yet.</td>
                </tr>
              ) : (
                closedPositions.map((position, index) => (
                  <tr key={`${position.asset}-${position.exit_date || index}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{position.asset}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatDate(position.entry_date)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatDate(position.exit_date)}</td>
                    <td className="px-4 py-3 text-right">{position.number_of_trades}</td>
                    <td className="px-4 py-3 text-right">{position.holding_period_days ?? '—'}</td>
                    <td className={`px-4 py-3 text-right ${(position.realized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatCurrency(position.realized_pnl)}</td>
                    <td className={`px-4 py-3 text-right ${(position.realized_pnl_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatPct(position.realized_pnl_pct)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
