'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function NewTradePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    asset: '',
    side: 'BUY',
    quantity: '',
    price: '',
    executedAt: new Date().toISOString().slice(0, 16),
    tradeType: 'entry',
    strategy: '',
    stopLoss: '',
    takeProfit: '',
    entryRationale: '',
    thesisId: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // TODO: POST to backend /api/trades
      console.log('Submitting trade:', form);
      
      // Mock success
      await new Promise((r) => setTimeout(r, 500));
      router.push('/trades');
    } catch (error) {
      console.error('Failed to submit trade:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Log New Trade</h1>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg border">
        {/* Asset & Side */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Asset</label>
            <input
              type="text"
              value={form.asset}
              onChange={(e) => setForm({ ...form, asset: e.target.value.toUpperCase() })}
              placeholder="BTC, ETH, SOL..."
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Side</label>
            <select
              value={form.side}
              onChange={(e) => setForm({ ...form, side: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
            >
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </div>
        </div>

        {/* Quantity & Price */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
            <input
              type="number"
              step="any"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              placeholder="0.00"
              className="w-full px-3 py-2 border rounded-md"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Price</label>
            <input
              type="number"
              step="any"
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              placeholder="0.00"
              className="w-full px-3 py-2 border rounded-md"
              required
            />
          </div>
        </div>

        {/* Execution Time */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Executed At</label>
          <input
            type="datetime-local"
            value={form.executedAt}
            onChange={(e) => setForm({ ...form, executedAt: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
            required
          />
        </div>

        {/* Trade Type & Strategy */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Trade Type</label>
            <select
              value={form.tradeType}
              onChange={(e) => setForm({ ...form, tradeType: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
            >
              <option value="entry">Entry</option>
              <option value="add">Add to Position</option>
              <option value="trim">Trim Position</option>
              <option value="exit">Exit</option>
              <option value="stop_loss">Stop Loss</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Strategy</label>
            <select
              value={form.strategy}
              onChange={(e) => setForm({ ...form, strategy: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
            >
              <option value="">Select strategy...</option>
              <option value="thesis_driven">Thesis Driven</option>
              <option value="momentum">Momentum</option>
              <option value="scalp">Scalp</option>
              <option value="mean_reversion">Mean Reversion</option>
            </select>
          </div>
        </div>

        {/* Risk Management */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Stop Loss</label>
            <input
              type="number"
              step="any"
              value={form.stopLoss}
              onChange={(e) => setForm({ ...form, stopLoss: e.target.value })}
              placeholder="Optional"
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Take Profit</label>
            <input
              type="number"
              step="any"
              value={form.takeProfit}
              onChange={(e) => setForm({ ...form, takeProfit: e.target.value })}
              placeholder="Optional"
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
        </div>

        {/* Entry Rationale */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Entry Rationale</label>
          <textarea
            value={form.entryRationale}
            onChange={(e) => setForm({ ...form, entryRationale: e.target.value })}
            placeholder="Why are you making this trade?"
            rows={3}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        {/* Submit */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Log Trade'}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="px-6 py-2 border rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
