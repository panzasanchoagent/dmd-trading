/** @type {import('next').NextConfig} */
function resolveApiBase() {
  const configuredUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

  try {
    const url = new URL(configuredUrl);
    const normalizedPath = url.pathname.replace(/\/$/, '');
    const basePath = normalizedPath.endsWith('/api') ? normalizedPath : `${normalizedPath}/api`;
    return `${url.origin}${basePath}`;
  } catch {
    return 'http://127.0.0.1:8001/api';
  }
}

const nextConfig = {
  async rewrites() {
    const apiBase = resolveApiBase();
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
