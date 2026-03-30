'use client';

import { useState } from 'react';

export default function PrinciplesPage() {
  const [principles, setPrinciples] = useState([
    {
      id: '1',
      title: 'Never risk more than 2% per trade',
      category: 'risk',
      ruleType: 'hard',
      timesFollowed: 45,
      timesViolated: 3,
      active: true,
    },
    {
      id: '2',
      title: 'Always set stop loss before entry',
      category: 'entry',
      ruleType: 'hard',
      timesFollowed: 42,
      timesViolated: 6,
      active: true,
    },
    {
      id: '3',
      title: 'Wait for confirmation on breakouts',
      category: 'entry',
      ruleType: 'soft',
      timesFollowed: 28,
      timesViolated: 12,
      active: true,
    },
  ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Trading Principles</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          + New Principle
        </button>
      </div>

      <p className="text-gray-600">
        Your codified trading rules. Hard rules should never be broken. Soft rules are guidelines.
      </p>

      {/* Principles List */}
      <div className="space-y-4">
        {principles.map((p) => (
          <div key={p.id} className="bg-white rounded-lg border p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs ${
                    p.ruleType === 'hard' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {p.ruleType.toUpperCase()}
                  </span>
                  <span className="px-2 py-1 bg-gray-100 rounded text-xs">{p.category}</span>
                </div>
                <h3 className="text-lg font-medium mt-2">{p.title}</h3>
              </div>
              <div className="text-right">
                <p className="text-green-600 text-sm">✓ {p.timesFollowed} followed</p>
                <p className="text-red-600 text-sm">✗ {p.timesViolated} violated</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
