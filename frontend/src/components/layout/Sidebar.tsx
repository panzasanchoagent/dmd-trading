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
    <div className="w-64 bg-white border-r border-khaki-200 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-khaki-200 bg-gradient-to-r from-khaki-50 to-white">
        <h1 className="text-xl font-bold text-khaki-900">🎯 Trigger</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className={clsx(
              'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
              pathname === item.href
                ? 'bg-khaki-100 text-khaki-900 border-l-3 border-khaki-600'
                : 'text-khaki-700 hover:bg-khaki-50 hover:text-khaki-900'
            )}
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
          </Link>
        ))}

        {/* Divider */}
        <div className="my-4 border-t border-khaki-200" />

        {/* External Links */}
        <p className="px-3 text-xs font-semibold text-khaki-500 uppercase tracking-wider">
          Connected Apps
        </p>
        {externalLinks.map((item) => (
          <a
            key={item.name}
            href={item.href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center px-3 py-2 text-sm font-medium text-khaki-700 hover:bg-khaki-50 hover:text-khaki-900 rounded-lg transition-colors"
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
            <span className="ml-auto text-khaki-400">↗</span>
          </a>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-khaki-200 bg-khaki-50">
        <p className="text-xs text-khaki-600 text-center">
          Connected to Arete DB
        </p>
      </div>
    </div>
  );
}
