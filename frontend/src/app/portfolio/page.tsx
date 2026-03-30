'use client';

import { useState, useEffect } from 'react';

interface Position {
  id: string;
  asset: string;
  quantity: number;
  avgEntryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  unrealizedPnLPct: number;
  positionType: string;
}

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Fetch from backend /api/positions
    // Mock data for now
    setPositions([
      {
        id: '1',
        asset: 'BTC',
        quantity: 0.5,
        avgEntryPrice: 45000,
        currentPrice: 66000,
        unrealizedPnL: 10500,
        unrealizedPnLPct: 46.7,
        positionType: 'core',
      },
      {
        id: '2',
        asset: 'ETH',
        quantity: 5,
        avgEntryPrice: 2200,
        currentPrice: 2000,
        unrealizedPnL: -1000,
        unrealizedPnLPct: -9.1,
        positionType: 'trading',
      },
    ]);
    setLoading(false);
  }, []);

  const totalValue = positions.reduce((sum, p) => sum + p.quantity * p.currentPrice, 0);
  const totalPnL = positions.reduce((sum, p) => sum + p.unrealizedPnL, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Portfolio</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          + New Trade
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Total Value</p>
          <p className="text-2xl font-bold">${totalValue.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Unrealized P&L</p>
          <p className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            ${totalPnL.toLocaleString()}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Positions</p>
          <p className="text-2xl font-bold">{positions.length}</p>
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-white rounded-lg border">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Asset</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Quantity</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Avg Entry</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Current</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">P&L</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Type</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {positions.map((position) => (
              <tr key={position.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{position.asset}</td>
                <td className="px-4 py-3 text-right">{position.quantity}</td>
                <td className="px-4 py-3 text-right">${position.avgEntryPrice.toLocaleString()}</td>
                <td className="px-4 py-3 text-right">${position.currentPrice.toLocaleString()}</td>
                <td className={`px-4 py-3 text-right ${position.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ${position.unrealizedPnL.toLocaleString()} ({position.unrealizedPnLPct.toFixed(1)}%)
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="px-2 py-1 bg-gray-100 rounded text-xs">{position.positionType}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
