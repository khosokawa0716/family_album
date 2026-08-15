import { useState } from "react";
import { useRouter } from "next/router";
import { apiClient } from "@/lib/api/client";

interface LoginRequest {
  user_name: string;
  password: string;
}

interface UserResponse {
  id: number;
  user_name: string;
  email: string | null;
  type: number;
  family_id: number;
  status: number;
  create_date: string;
  update_date: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export const useLogin = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const login = async (loginData: LoginRequest, redirectTo?: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient.post<LoginResponse>("/login", loginData);
      if (!data.access_token) {
        throw new Error("ログインに失敗しました");
      }
      // トークンをローカルストレージに保存（タブ・別ブラウザ起動をまたいでログイン状態を維持するため）
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      // 指定があれば元のページへ、なければ写真一覧ページに遷移
      router.push(redirectTo && redirectTo.startsWith("/") ? redirectTo : "/photo/list");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインに失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    router.push("/login");
  };

  return {
    login,
    logout,
    isLoading,
    error,
  };
};
