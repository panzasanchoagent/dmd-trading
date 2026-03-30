'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';

const navigation = [
  { name: 'Dashboard', href: '/', icon: '📊' },
  { name: 'Portfolio', href: '/portfolio', icon: '💼' },
  { name: 'Trades', href: '/trades', icon: '📈' },
  { name: 'Journal', href: '/journal', icon: '📝' },
  { name: 'Principles', href: '/principles', icon: '⚖️' },
  { name: 'Post-Mortems', href: '/post-mortems', icon: '🔍' },
  { name: 'AI Coach', href: '/coach', icon: '🤖' },
  { name: 'Patterns', href: '/patterns', icon: '🔮' },
];

const externalLinks = [
  { name: 'Neural Notes', href: 'http://localhost:3000', icon: '🧠' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">📒 Trading Journal</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className={clsx(
              'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
              pathname === item.href
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
          </Link>
        ))}

        {/* Divider */}
        <div className="my-4 border-t border-gray-200" />

        {/* External Links */}
        <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Connected Apps
        </p>
        {externalLinks.map((item) => (
          <a
            key={item.name}
            href={item.href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md"
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
            <span className="ml-auto text-gray-400">↗</span>
          </a>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          Connected to Arete DB
        </p>
      </div>
    </div>
  );
}
