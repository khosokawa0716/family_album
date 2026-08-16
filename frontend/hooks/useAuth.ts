import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { authService } from "@/services/auth";
import { ApiError } from "@/lib/api/client";

interface User {
  id: number;
  user_name: string;
  nickname: string | null;
  theme_color: string | null;
  avatar_path: string | null;
  email: string | null;
  type: number;
  family_id: number;
  status: number;
  create_date: string;
  update_date: string;
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const router = useRouter();

  const checkAuth = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setIsAuthenticated(false);
        setUser(null);
        return false;
      }

      const userData = await authService.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);
      return true;
    } catch (err) {
      setIsAuthenticated(false);
      setUser(null);
      // 401（トークン自体が無効・期限切れ）のときだけ保存済みのトークンを破棄する。
      // ネットワーク不調等の一時的な失敗まで破棄すると、再アクセス時に
      // 有効なトークンがあるのに毎回ログインを要求することになってしまう。
      if (err instanceof ApiError && err.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
      }
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const requireAuth = async (redirectTo: string = "/login") => {
    const isAuth = await checkAuth();
    if (!isAuth) {
      router.push(redirectTo);
      return false;
    }
    return true;
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      setUser(null);
      setIsAuthenticated(false);
      router.push("/login");
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return {
    user,
    isLoading,
    isAuthenticated,
    checkAuth,
    requireAuth,
    logout,
  };
};
