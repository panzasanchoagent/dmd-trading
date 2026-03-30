'use client';

import { useState } from 'react';

export default function CoachPage() {
  const [message, setMessage] = useState('');
  const [conversation, setConversation] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm your AI trading coach. I can help you review trades, challenge your thinking, and identify patterns in your execution. What would you like to discuss?",
    },
  ]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const userMessage = { role: 'user', content: message };
    setConversation([...conversation, userMessage]);
    setMessage('');
    setLoading(true);

    // TODO: Call backend /api/coach with message
    // Mock response for now
    setTimeout(() => {
      setConversation((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: "That's an interesting point. Based on your recent trading patterns, I notice you've been sizing positions larger when volatility is high. Have you considered how this affects your risk exposure?",
        },
      ]);
      setLoading(false);
    }, 1000);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">🤖 AI Coach</h1>
        <div className="flex gap-2">
          <button className="px-3 py-1 text-sm border rounded-md hover:bg-gray-50">
            Review Last Trade
          </button>
          <button className="px-3 py-1 text-sm border rounded-md hover:bg-gray-50">
            Weekly Check-in
          </button>
        </div>
      </div>

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto bg-white rounded-lg border p-4 space-y-4">
        {conversation.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 px-4 py-2 rounded-lg">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask your coach..."
          className="flex-1 px-4 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
