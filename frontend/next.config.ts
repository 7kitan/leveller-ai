import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/cv",
        destination: "/user/cv",
        permanent: true,
      },
      {
        source: "/analysis",
        destination: "/user/analysis",
        permanent: true,
      },
      {
        source: "/jobs",
        destination: "/user/jobs",
        permanent: true,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`, // Proxy sang Gateway
      },
    ];
  },
};

export default nextConfig;
