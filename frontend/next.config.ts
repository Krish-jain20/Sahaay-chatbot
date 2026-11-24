import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// Optional, for a temporary public demo link: set BACKEND_URL (e.g. http://127.0.0.1:8001) and build the
// frontend with NEXT_PUBLIC_API_URL=/api. The browser then talks only to the frontend, which forwards
// /api/* to the backend, so one public link is enough. Unset by default: local development is unchanged.
const backendUrl = process.env.BACKEND_URL?.replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return backendUrl ? [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }] : [];
  },
};

export default createNextIntlPlugin()(nextConfig);
