import { apiClient } from "@/lib/api/client";
import { LoginRequest, LoginResponse, LogoutResponse, UserResponse } from "@/types/auth";

export const authService = {
  async login(loginData: LoginRequest): Promise<LoginResponse> {
    return apiClient.post<LoginResponse>("/login", loginData);
  },

  async logout(): Promise<LogoutResponse> {
    return apiClient.post<LogoutResponse>("/logout");
  },

  async getCurrentUser(): Promise<UserResponse> {
    return apiClient.get<UserResponse>("/users/me");
  },
};
