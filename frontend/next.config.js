/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.realtor.ca",
      },
      {
        protocol: "https",
        hostname: "cdn.realtor.ca",
      },
    ],
  },
};

module.exports = nextConfig;
