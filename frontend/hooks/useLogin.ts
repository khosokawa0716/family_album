import { useState } from "react";
import { useRouter } from "next/router";

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
      const response = await fetch("/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(loginData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "ログインに失敗しました");
      }

      const data: LoginResponse = await response.json();

      // トークンをローカルストレージに保存
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      // ユーザー情報表示ページに遷移
      router.push("/tmp");
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