'use client';

export default function PostMortemsPage() {
  const postMortems = [
    {
      id: '1',
      asset: 'SOL',
      result: 'loss',
      pnl: -1200,
      keyLesson: 'Chased entry after missing initial breakout. Should have waited for retest.',
      createdAt: '2026-03-25',
    },
    {
      id: '2',
      asset: 'BTC',
      result: 'win',
      pnl: 3500,
      keyLesson: 'Thesis played out exactly. Patience on entry paid off.',
      createdAt: '2026-03-20',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Post-Mortems</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          + New Post-Mortem
        </button>
      </div>

      <p className="text-gray-600">
        Structured reflections on completed trades. Learn from both wins and losses.
      </p>

      {/* Post-Mortems List */}
      <div className="space-y-4">
        {postMortems.map((pm) => (
          <div key={pm.id} className="bg-white rounded-lg border p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <span className="text-xl font-bold">{pm.asset}</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  pm.result === 'win' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {pm.result.toUpperCase()}
                </span>
              </div>
              <span className={`text-lg font-semibold ${pm.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${pm.pnl.toLocaleString()}
              </span>
            </div>
            <p className="text-gray-600 text-sm">💡 {pm.keyLesson}</p>
            <p className="text-gray-400 text-xs mt-2">{pm.createdAt}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
