/** @type {import('next').NextConfig} */
function resolveApiUrl() {
  const configuredUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

  try {
    const url = new URL(configuredUrl);
    const isTailscaleHost = /^100\./.test(url.hostname);

    if (isTailscaleHost && url.port === '8001') {
      return 'http://127.0.0.1:8001';
    }

    return url.origin;
  } catch {
    return 'http://127.0.0.1:8001';
  }
}

const nextConfig = {
  async rewrites() {
    const apiUrl = resolveApiUrl();
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
