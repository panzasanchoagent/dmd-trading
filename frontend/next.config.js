/** @type {import('next').NextConfig} */
function normalizeApiOrigin(url, source) {
  const isTailscaleHost = /^100\./.test(url.hostname);

  if (source !== 'API_URL' && isTailscaleHost && url.port === '8001') {
    return 'http://127.0.0.1:8001';
  }

  return url.origin;
}

function resolveApiBase() {
  const configured = process.env.API_URL
    ? { value: process.env.API_URL, source: 'API_URL' }
    : process.env.NEXT_PUBLIC_API_URL
      ? { value: process.env.NEXT_PUBLIC_API_URL, source: 'NEXT_PUBLIC_API_URL' }
      : { value: 'http://127.0.0.1:8001', source: 'default' };

  try {
    const url = new URL(configured.value);
    const normalizedOrigin = normalizeApiOrigin(url, configured.source);
    const normalizedPath = url.pathname.replace(/\/$/, '');
    const basePath = normalizedPath.endsWith('/api') ? normalizedPath : `${normalizedPath}/api`;
    return `${normalizedOrigin}${basePath}`;
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
