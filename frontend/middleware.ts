import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // ログインページは認証チェックをスキップ
  const publicPaths = ["/login"];
  const isPublicPath = publicPaths.some((path) => pathname.startsWith(path));

  if (isPublicPath) {
    return NextResponse.next();
  }

  // クッキーからアクセストークンを取得（将来的にcookieベース認証に移行する場合）
  const token = request.cookies.get("access_token")?.value;

  // トークンがない場合、ログインページにリダイレクト
  // 注意: sessionStorageベースの認証では、middlewareでの完全な認証チェックは制限される
  // 実際の認証チェックは各ページコンポーネントで行う
  if (!token && pathname !== "/login") {
    // 静的ファイルやAPIルートは除外
    if (
      pathname.startsWith("/_next") ||
      pathname.startsWith("/api") ||
      pathname.startsWith("/static") ||
      pathname.includes(".")
    ) {
      return NextResponse.next();
    }

    // クライアントサイドでの認証チェックを促すため、
    // ここではリダイレクトせずにレスポンスを通す
    // 実際の認証チェックは各ページの useAuth フックで行う
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  // ミドルウェアを適用するパスを指定
  matcher: [
    /*
     * すべてのリクエストパスにマッチするが、以下を除く:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
