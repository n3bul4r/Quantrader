/** @type {import('next').NextConfig} */
const API = process.env.QT_API_URL || "http://localhost:8000";
const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};
export default nextConfig;
