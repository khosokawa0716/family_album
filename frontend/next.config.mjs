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
};
