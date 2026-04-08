'use client';

import { useState, useEffect } from 'react';

interface PortfolioSummaryResponse {
  total_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  position_count: number;
}

interface NavHistoryResponse {
  history: Array<{
    date: string;
    nav: number;
  }>;
}

interface DashboardSummary {
  totalValue: number;
  totalPnL: number;
  totalPnLPct: number;
  openPositions: number;
  todayPnL: number;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toLocaleString();
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        const portfolio = await fetchJson<PortfolioSummaryResponse>('/api/portfolio/summary');

        let latestNav = portfolio.total_value ?? 0;
        let previousNav = latestNav;

        try {
          const navHistory = await fetchJson<NavHistoryResponse>('/api/portfolio/nav-history?days=2');
          latestNav = navHistory.history?.[navHistory.history.length - 1]?.nav ?? latestNav;
          previousNav = navHistory.history?.[navHistory.history.length - 2]?.nav ?? latestNav;
        } catch {
          // Keep dashboard summary working even if NAV history is unavailable.
        }

        setSummary({
          totalValue: portfolio.total_value ?? 0,
          totalPnL: portfolio.total_unrealized_pnl ?? 0,
          totalPnLPct: portfolio.total_unrealized_pnl_pct ?? 0,
          openPositions: portfolio.position_count ?? 0,
          todayPnL: latestNav - previousNav,
        });
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) {
    return <div className="animate-pulse text-khaki-600">Loading...</div>;
  }

  if (error) {
    return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-khaki-900">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Portfolio Value"
          value={`$${formatNumber(summary?.totalValue)}`}
          subtitle="Live portfolio summary"
          icon="💰"
        />
        <SummaryCard
          title="Total P&L"
          value={`$${formatNumber(summary?.totalPnL)}`}
          subtitle={`${summary?.totalPnLPct?.toFixed(1) ?? '0.0'}%`}
          positive={(summary?.totalPnL ?? 0) > 0}
          icon="📈"
        />
        <SummaryCard
          title="Today's P&L"
          value={`$${formatNumber(summary?.todayPnL)}`}
          positive={(summary?.todayPnL ?? 0) > 0}
          icon="📅"
        />
        <SummaryCard
          title="Open Positions"
          value={formatNumber(summary?.openPositions) || '0'}
          subtitle="Active holdings"
          icon="📊"
        />
      </div>

      <div className="card p-6">
        <h2 className="text-lg font-semibold text-khaki-900 mb-4">Quick Actions</h2>
        <div className="flex gap-4">
          <button className="btn-primary">
            + New Trade
          </button>
          <button className="btn-secondary">
            📝 Journal Entry
          </button>
          <button className="btn-secondary">
            🤖 Talk to Coach
          </button>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-lg font-semibold text-khaki-900 mb-4">Recent Activity</h2>
        <p className="text-khaki-500">No recent activity. Start by logging a trade!</p>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  subtitle,
  positive,
  icon,
}: {
  title: string;
  value: string;
  subtitle?: string;
  positive?: boolean;
  icon: string;
}) {
  return (
    <div className="card-hover p-4">
      <div className="flex items-center justify-between">
        <span className="text-2xl">{icon}</span>
        {positive !== undefined && (
          <span className={positive ? 'text-success' : 'text-danger'}>
            {positive ? '↑' : '↓'}
          </span>
        )}
      </div>
      <p className="mt-2 text-sm text-khaki-500">{title}</p>
      <p className="text-xl font-semibold text-khaki-900">{value}</p>
      {subtitle && <p className="text-sm text-khaki-400">{subtitle}</p>}
    </div>
  );
}
