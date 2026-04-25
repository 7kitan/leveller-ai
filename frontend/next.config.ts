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
};

export default nextConfig;
