export default {
  async redirects() {
    return [
      {
        source: "/",
        destination: "/photo/list",
        permanent: true,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost/api/:path*",
      },
    ];
  },
};
