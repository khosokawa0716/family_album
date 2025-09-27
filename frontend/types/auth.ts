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

export interface UserResponse {
  id: number;
  user_name: string;
  email: string | null;
  type: number;
  family_id: number;
  status: number;
  create_date: string; // ISO 8601 date string
  update_date: string; // ISO 8601 date string
}
