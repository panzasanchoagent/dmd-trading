'use client';

import { useState, useEffect } from 'react';

interface PortfolioSummary {
  totalValue: number;
  totalPnL: number;
  totalPnLPct: number;
  openPositions: number;
  todayPnL: number;
}

export default function Dashboard() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Fetch from backend
    // For now, mock data
    setSummary({
      totalValue: 125000,
      totalPnL: 15000,
      totalPnLPct: 13.6,
      openPositions: 5,
      todayPnL: 450,
    });
    setLoading(false);
  }, []);

  if (loading) {
    return <div className="animate-pulse text-khaki-600">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-khaki-900">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Portfolio Value"
          value={`$${summary?.totalValue.toLocaleString()}`}
          subtitle="Total positions"
          icon="💰"
        />
        <SummaryCard
          title="Total P&L"
          value={`$${summary?.totalPnL.toLocaleString()}`}
          subtitle={`${summary?.totalPnLPct}%`}
          positive={summary?.totalPnL! > 0}
          icon="📈"
        />
        <SummaryCard
          title="Today's P&L"
          value={`$${summary?.todayPnL.toLocaleString()}`}
          positive={summary?.todayPnL! > 0}
          icon="📅"
        />
        <SummaryCard
          title="Open Positions"
          value={summary?.openPositions.toString() || '0'}
          subtitle="Active trades"
          icon="📊"
        />
      </div>

      {/* Quick Actions */}
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

      {/* Recent Activity */}
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
