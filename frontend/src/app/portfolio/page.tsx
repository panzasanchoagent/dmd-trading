'use client';

import { useEffect, useMemo, useState } from 'react';

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
  source?: string;
}

interface PositionsResponse {
  positions: Position[];
  total_value: number;
  position_count: number;
  source?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(1)}%`;
}

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [source, setSource] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPortfolio() {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/portfolio/positions`, {
          cache: 'no-store',
        });

        if (!response.ok) {
          throw new Error(`Portfolio request failed (${response.status})`);
        }

        const data: PositionsResponse = await response.json();
        setPositions(data.positions || []);
        setTotalValue(data.total_value || 0);
        setSource(data.source || null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load portfolio');
      } finally {
        setLoading(false);
      }
    }

    loadPortfolio();
  }, []);

  const totalPnL = useMemo(
    () => positions.reduce((sum, position) => sum + (position.unrealized_pnl || 0), 0),
    [positions]
  );

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
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          + New Trade
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Total Value</p>
          <p className="text-2xl font-bold">{formatCurrency(totalValue)}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Unrealized P&amp;L</p>
          <p className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(totalPnL)}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Positions</p>
          <p className="text-2xl font-bold">{positions.length}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Asset</th>
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
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                  No open positions yet. Add trades or seed the positions table.
                </td>
              </tr>
            ) : (
              positions.map((position) => (
                <tr key={position.asset} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{position.asset}</td>
                  <td className="px-4 py-3 text-right">{position.quantity.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(position.avg_entry_price)}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(position.current_price)}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(position.current_value)}</td>
                  <td className={`px-4 py-3 text-right ${(position.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(position.unrealized_pnl)} ({formatPct(position.unrealized_pnl_pct)})
                  </td>
                  <td className="px-4 py-3 text-right">{formatPct(position.allocation_pct)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                      {position.position_type || 'unclassified'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
