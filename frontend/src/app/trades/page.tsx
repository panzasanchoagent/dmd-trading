'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function TradesPage() {
  const [trades, setTrades] = useState([
    {
      id: '1',
      asset: 'BTC',
      side: 'BUY',
      quantity: 0.1,
      price: 65000,
      executedAt: '2026-03-28T10:30:00',
      strategy: 'thesis_driven',
    },
    {
      id: '2',
      asset: 'ETH',
      side: 'SELL',
      quantity: 2,
      price: 2100,
      executedAt: '2026-03-27T14:15:00',
      strategy: 'momentum',
    },
  ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Trade Log</h1>
        <Link
          href="/trades/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          + New Trade
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select className="px-3 py-2 border rounded-md">
          <option>All Assets</option>
          <option>BTC</option>
          <option>ETH</option>
          <option>SOL</option>
        </select>
        <select className="px-3 py-2 border rounded-md">
          <option>All Strategies</option>
          <option>Thesis Driven</option>
          <option>Momentum</option>
          <option>Scalp</option>
        </select>
        <input type="date" className="px-3 py-2 border rounded-md" />
      </div>

      {/* Trades Table */}
      <div className="bg-white rounded-lg border">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Date</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Asset</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Side</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Quantity</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Price</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Strategy</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {trades.map((trade) => (
              <tr key={trade.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm">
                  {new Date(trade.executedAt).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 font-medium">{trade.asset}</td>
                <td className={`px-4 py-3 ${trade.side === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>
                  {trade.side}
                </td>
                <td className="px-4 py-3 text-right">{trade.quantity}</td>
                <td className="px-4 py-3 text-right">${trade.price.toLocaleString()}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                    {trade.strategy}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button className="text-blue-600 hover:underline text-sm">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
