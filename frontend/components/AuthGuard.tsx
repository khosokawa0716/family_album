import { useEffect, ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";

interface AuthGuardProps {
  children: ReactNode;
  redirectTo?: string;
  fallback?: ReactNode;
}

export const AuthGuard = ({
  children,
  redirectTo = "/login",
  fallback = <div>Loading...</div>,
}: AuthGuardProps) => {
  const { isAuthenticated, isLoading, requireAuth } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      requireAuth(redirectTo);
    }
  }, [isAuthenticated, isLoading, requireAuth, redirectTo]);

  if (isLoading) {
    return <>{fallback}</>;
  }

  if (!isAuthenticated) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
