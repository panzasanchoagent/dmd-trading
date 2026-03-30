'use client';

export default function PatternsPage() {
  const patterns = [
    {
      id: '1',
      name: 'FOMO on breakouts',
      description: 'Tendency to chase entries after initial breakout, leading to poor entries.',
      patternType: 'weakness',
      category: 'emotion',
      occurrenceCount: 8,
      estimatedPnlImpact: -4500,
      severity: 'high',
      beingAddressed: true,
    },
    {
      id: '2',
      name: 'Strong thesis conviction',
      description: 'Holding through volatility when thesis is intact leads to better outcomes.',
      patternType: 'strength',
      category: 'psychology',
      occurrenceCount: 12,
      estimatedPnlImpact: 8200,
      severity: 'high',
      beingAddressed: false,
    },
    {
      id: '3',
      name: 'Oversizing in high volatility',
      description: 'Position sizes increase when volatility is elevated, increasing risk.',
      patternType: 'weakness',
      category: 'sizing',
      occurrenceCount: 5,
      estimatedPnlImpact: -2100,
      severity: 'medium',
      beingAddressed: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">🔮 Pattern Detection</h1>
        <button className="px-4 py-2 border rounded-md hover:bg-gray-50">
          Run AI Analysis
        </button>
      </div>

      <p className="text-gray-600">
        AI-identified recurring patterns in your trading behavior. Acknowledge and address weaknesses to improve.
      </p>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Strengths</p>
          <p className="text-2xl font-bold text-green-600">
            {patterns.filter((p) => p.patternType === 'strength').length}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Weaknesses</p>
          <p className="text-2xl font-bold text-red-600">
            {patterns.filter((p) => p.patternType === 'weakness').length}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Est. P&L Impact</p>
          <p className="text-2xl font-bold">
            ${patterns.reduce((sum, p) => sum + p.estimatedPnlImpact, 0).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Patterns List */}
      <div className="space-y-4">
        {patterns.map((pattern) => (
          <div
            key={pattern.id}
            className={`bg-white rounded-lg border-l-4 p-4 ${
              pattern.patternType === 'strength' ? 'border-green-500' : 'border-red-500'
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    pattern.patternType === 'strength' 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {pattern.patternType.toUpperCase()}
                  </span>
                  <span className="px-2 py-1 bg-gray-100 rounded text-xs">{pattern.category}</span>
                  <span className={`px-2 py-1 rounded text-xs ${
                    pattern.severity === 'high' ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {pattern.severity}
                  </span>
                </div>
                <h3 className="text-lg font-medium">{pattern.name}</h3>
                <p className="text-gray-600 text-sm mt-1">{pattern.description}</p>
              </div>
              <div className="text-right">
                <p className={`text-lg font-semibold ${
                  pattern.estimatedPnlImpact >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  ${pattern.estimatedPnlImpact.toLocaleString()}
                </p>
                <p className="text-gray-400 text-sm">{pattern.occurrenceCount} occurrences</p>
                {pattern.beingAddressed && (
                  <span className="text-blue-600 text-xs">🔧 Being addressed</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
