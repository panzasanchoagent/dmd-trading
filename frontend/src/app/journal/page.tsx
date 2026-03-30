'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function JournalPage() {
  const [entries, setEntries] = useState([
    {
      id: '1',
      entryDate: '2026-03-30',
      emotionalState: 'calm',
      energyLevel: 4,
      whatWentWell: 'Followed my stop loss discipline',
      lessonsLearned: 'Size positions based on conviction',
    },
    {
      id: '2',
      entryDate: '2026-03-29',
      emotionalState: 'anxious',
      energyLevel: 3,
      whatWentWell: 'Stayed patient during consolidation',
      lessonsLearned: 'Market structure trumps news',
    },
  ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Trading Journal</h1>
        <Link
          href="/journal/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          + New Entry
        </Link>
      </div>

      {/* Calendar View (simplified) */}
      <div className="bg-white rounded-lg border p-4">
        <p className="text-sm text-gray-500 mb-4">Recent Entries</p>
        <div className="space-y-4">
          {entries.map((entry) => (
            <div key={entry.id} className="border-l-4 border-blue-500 pl-4 py-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">{entry.entryDate}</span>
                <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                  {entry.emotionalState} • Energy: {entry.energyLevel}/5
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1">✅ {entry.whatWentWell}</p>
              <p className="text-sm text-gray-600">💡 {entry.lessonsLearned}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-3xl font-bold text-green-600">12</p>
          <p className="text-sm text-gray-500">Journal Streak</p>
        </div>
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-3xl font-bold">3.8</p>
          <p className="text-sm text-gray-500">Avg Energy</p>
        </div>
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-3xl font-bold">24</p>
          <p className="text-sm text-gray-500">Total Entries</p>
        </div>
      </div>
    </div>
  );
}
