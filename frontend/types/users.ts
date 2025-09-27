export interface UserCreateRequest {
  user_name: string;
  password: string;
  email?: string | null;
  type?: number;
  family_id: number;
}

export interface UserUpdateRequest {
  user_name?: string;
  password?: string;
  email?: string | null;
  type?: number;
  family_id?: number;
  status?: number;
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

export interface UserDeleteResponse {
  message: string;
  deleted_user_id: number;
}
