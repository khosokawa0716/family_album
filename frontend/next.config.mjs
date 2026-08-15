// 署名付き画像URL（/api/photos, /api/thumbnails, /api/avatars 等）はブラウザから
// 相対パスとして解決されるため、Next.js dev server自身がバックエンドへ転送する必要がある。
// 本番（Docker Compose）ではnginxがNext.jsに到達する前に/api/*をバックエンドへ振り分けるため
// この転送は実行されず、ここではbare-metalローカル開発向けの転送先のみを気にすればよい。
const API_INTERNAL_BASE = process.env.API_INTERNAL_BASE || "http://localhost:8000";

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
        destination: `${API_INTERNAL_BASE}/api/:path*`,
      },
    ];
  },
};
