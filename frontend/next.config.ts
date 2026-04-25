import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "",
  },
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
};

export default nextConfig;
