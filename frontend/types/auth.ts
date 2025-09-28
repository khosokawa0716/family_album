import { UserResponse } from "./users";

export type { UserResponse };

export interface LoginRequest {
  user_name: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface LogoutResponse {
  message: string;
}
