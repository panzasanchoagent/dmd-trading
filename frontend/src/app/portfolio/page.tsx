'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
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
  days: number;
  history: NavPoint[];
  gap?: string;
}

interface PerformanceResponse {
  total_trades: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  total_pnl: number;
  win_rate: number;
  expectancy: number;
  profit_factor: number;
}

const PIE_COLORS = ['#2563eb', '#16a34a', '#dc2626', '#ca8a04', '#7c3aed', '#0891b2'];

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
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

function computeMaxDrawdown(history: NavPoint[]) {
  let peak = Number.NEGATIVE_INFINITY;
  let maxDrawdown = 0;

  for (const point of history) {
    if (point.nav > peak) peak = point.nav;
    if (peak > 0) {
      const drawdown = ((point.nav - peak) / peak) * 100;
      if (drawdown < maxDrawdown) maxDrawdown = drawdown;
    }
  }

  return maxDrawdown;
}

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [source, setSource] = useState<string | null>(null);
  const [closedPositions, setClosedPositions] = useState<ClosedPosition[]>([]);
  const [navHistory, setNavHistory] = useState<NavPoint[]>([]);
  const [navGap, setNavGap] = useState<string | null>(null);
  const [navDays, setNavDays] = useState<number | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPortfolio() {
      try {
        setLoading(true);
        const [positionsData, closedData, navData, performanceData] = await Promise.all([
          fetchJson<PositionsResponse>('/api/portfolio/positions'),
          fetchJson<ClosedResponse>('/api/portfolio/closed?limit=25'),
          fetchJson<NavHistoryResponse>('/api/portfolio/nav-history'),
          fetchJson<PerformanceResponse>('/api/portfolio/performance'),
        ]);

        setPositions(positionsData.positions || []);
        setTotalValue(positionsData.total_value || 0);
        setSource(positionsData.source || null);
        setClosedPositions(closedData.closed_positions || []);
        setNavHistory(navData.history || []);
        setNavGap(navData.gap || null);
        setNavDays(navData.days || null);
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

  const cashPosition = useMemo(
    () => positions.find((position) => position.asset === 'USD') || null,
    [positions]
  );

  const investedValue = useMemo(
    () => positions.filter((position) => position.asset !== 'USD').reduce((sum, position) => sum + (position.current_value || 0), 0),
    [positions]
  );

  const pieData = useMemo(
    () => positions.filter((position) => (position.current_value || 0) !== 0).map((position) => ({ name: position.asset, value: Math.abs(position.current_value || 0) })),
    [positions]
  );

  const topPnL = useMemo(
    () => [...positions].filter((position) => position.asset !== 'USD').sort((a, b) => (b.unrealized_pnl || 0) - (a.unrealized_pnl || 0)),
    [positions]
  );

  const latestNav = navHistory.length ? navHistory[navHistory.length - 1]?.nav || 0 : totalValue;
  const maxDrawdown = useMemo(() => computeMaxDrawdown(navHistory), [navHistory]);

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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Total Value" value={formatCurrency(totalValue)} />
        <MetricCard label="Unrealized P&L" value={formatCurrency(totalUnrealizedPnL)} tone={totalUnrealizedPnL >= 0 ? 'positive' : 'negative'} />
        <MetricCard label="Realized P&L" value={formatCurrency(performance?.total_realized_pnl)} tone={(performance?.total_realized_pnl || 0) >= 0 ? 'positive' : 'negative'} />
        <MetricCard label="Cash" value={formatCurrency(cashPosition?.current_value)} tone={(cashPosition?.current_value || 0) >= 0 ? 'default' : 'negative'} />
        <MetricCard label="Max Drawdown" value={formatPct(maxDrawdown)} tone={maxDrawdown >= 0 ? 'default' : 'negative'} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-lg border bg-white p-4 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">NAV history</h2>
              <p className="text-sm text-gray-500">Default view is YTD{navDays ? ` (${navDays} days loaded)` : ''}</p>
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
          <h2 className="text-lg font-semibold text-gray-900">Portfolio mix</h2>
          {pieData.length > 0 ? (
            <>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={90} label>
                      {pieData.map((entry, index) => (
                        <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between"><span className="text-gray-500">Invested</span><span className="font-medium">{formatCurrency(investedValue)}</span></div>
                <div className="flex items-center justify-between"><span className="text-gray-500">Cash weight</span><span className="font-medium">{formatPct(cashPosition?.allocation_pct)}</span></div>
                <div className="flex items-center justify-between"><span className="text-gray-500">Closed trades</span><span className="font-medium">{performance?.total_trades ?? closedPositions.length}</span></div>
                <div className="flex items-center justify-between"><span className="text-gray-500">Win rate</span><span className="font-medium">{formatPct(performance?.win_rate)}</span></div>
                <div className="flex items-center justify-between"><span className="text-gray-500">Profit factor</span><span className="font-medium">{performance?.profit_factor === Infinity ? '∞' : performance?.profit_factor?.toFixed(2) ?? '—'}</span></div>
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-lg border border-dashed p-6 text-sm text-gray-500">No position values available yet.</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-lg font-semibold text-gray-900">Current portfolio health</h2>
          <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <StatRow label="Total P&L" value={formatCurrency(performance?.total_pnl)} tone={(performance?.total_pnl || 0) >= 0 ? 'positive' : 'negative'} />
            <StatRow label="Expectancy" value={formatCurrency(performance?.expectancy)} />
            <StatRow label="Open positions" value={String(positions.length)} />
            <StatRow label="Priced NAV" value={formatCurrency(latestNav)} />
            <StatRow label="Cash quantity" value={cashPosition ? cashPosition.quantity.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'} tone={(cashPosition?.quantity || 0) >= 0 ? 'default' : 'negative'} />
            <StatRow label="Cash price source" value={cashPosition?.price_source || '—'} />
          </div>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-lg font-semibold text-gray-900">Open P&L leaderboard</h2>
          <div className="mt-4 space-y-3">
            {topPnL.length === 0 ? (
              <div className="text-sm text-gray-500">No open positions yet.</div>
            ) : (
              topPnL.slice(0, 5).map((position) => (
                <div key={position.asset} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm">
                  <div>
                    <p className="font-medium text-gray-900">{position.asset}</p>
                    <p className="text-gray-500">{formatCurrency(position.current_price)} · {position.price_source || 'n/a'}</p>
                  </div>
                  <div className={`text-right font-medium ${(position.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    <p>{formatCurrency(position.unrealized_pnl)}</p>
                    <p className="text-xs">{formatPct(position.unrealized_pnl_pct)}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="rounded-lg border bg-white overflow-hidden">
        <div className="border-b px-4 py-3">
          <h2 className="text-lg font-semibold text-gray-900">Open positions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1120px]">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Asset</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">First Entry</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Last Trade</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Quantity</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Avg Entry</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Current</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Value</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">P&L</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Allocation</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Price Source</th>
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
                    <td className="px-4 py-3 text-right text-xs text-gray-500">{position.price_source || '—'}</td>
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
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Realized P&L</th>
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

function MetricCard({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'positive' | 'negative' }) {
  const toneClass = tone === 'positive' ? 'text-green-600' : tone === 'negative' ? 'text-red-600' : 'text-gray-900';
  return (
    <div className="rounded-lg border bg-white p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-2xl font-bold ${toneClass}`}>{value}</p>
    </div>
  );
}

function StatRow({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'positive' | 'negative' }) {
  const toneClass = tone === 'positive' ? 'text-green-600' : tone === 'negative' ? 'text-red-600' : 'text-gray-900';
  return (
    <div className="rounded-lg bg-gray-50 p-3">
      <p className="text-xs uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`mt-1 text-base font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}
