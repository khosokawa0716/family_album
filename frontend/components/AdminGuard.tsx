import { useEffect, ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/router";

interface AdminGuardProps {
  children: ReactNode;
  redirectTo?: string;
  fallback?: ReactNode;
}

export const AdminGuard = ({
  children,
  redirectTo = "/",
  fallback = <div>Loading...</div>,
}: AdminGuardProps) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      // 認証されていない場合はログインページへ
      if (!isAuthenticated) {
        router.push("/login");
        return;
      }

      // 管理者でない場合は指定のページへリダイレクト
      if (user?.type !== 10) {
        router.push(redirectTo);
      }
    }
  }, [isAuthenticated, isLoading, user, router, redirectTo]);

  if (isLoading) {
    return <>{fallback}</>;
  }

  if (!isAuthenticated || user?.type !== 10) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
