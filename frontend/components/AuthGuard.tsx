import { useEffect, ReactNode } from "react";
import { useRouter } from "next/router";
import { useAuth } from "@/hooks/useAuth";

interface AuthGuardProps {
  children: ReactNode;
  redirectTo?: string;
  fallback?: ReactNode;
}

export const AuthGuard = ({
  children,
  redirectTo,
  fallback = <div>Loading...</div>,
}: AuthGuardProps) => {
  const { isAuthenticated, isLoading, requireAuth } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // router.isReady前はasPathが動的ルートのプレースホルダー（例: /photo/detail/[id]）になっているため待つ
    if (!isLoading && !isAuthenticated && router.isReady) {
      // ログイン後に元のページへ戻れるよう、現在のパスをredirectパラメータで渡す
      const target =
        redirectTo ?? `/login?redirect=${encodeURIComponent(router.asPath)}`;
      requireAuth(target);
    }
  }, [isAuthenticated, isLoading, requireAuth, redirectTo, router.isReady, router.asPath]);

  if (isLoading) {
    return <>{fallback}</>;
  }

  if (!isAuthenticated) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
