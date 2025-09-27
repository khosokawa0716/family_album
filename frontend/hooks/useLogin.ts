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

  const login = async (loginData: LoginRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient.post<LoginResponse>("/login", loginData);
      if (!data.access_token) {
        throw new Error("ログインに失敗しました");
      }
      // トークンをセッションストレージに保存
      sessionStorage.setItem("access_token", data.access_token);
      sessionStorage.setItem("user", JSON.stringify(data.user));

      // 写真一覧ページに遷移
      router.push("/photo/list");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインに失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user");
    router.push("/login");
  };

  return {
    login,
    logout,
    isLoading,
    error,
  };
};
