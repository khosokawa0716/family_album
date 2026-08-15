import { apiClient } from "@/lib/api/client";
import {
  UserCreateRequest,
  UserUpdateRequest,
  UserResponse,
  UserDeleteResponse,
} from "@/types/users";

export const userService = {
  async createUser(userData: UserCreateRequest): Promise<UserResponse> {
    return apiClient.post<UserResponse>("/users", userData);
  },

  async getUsers(): Promise<UserResponse[]> {
    return apiClient.get<UserResponse[]>("/users");
  },

  async updateUser(userId: number, userData: UserUpdateRequest): Promise<UserResponse> {
    return apiClient.patch<UserResponse>(`/users/${userId}`, userData);
  },

  async deleteUser(userId: number): Promise<UserDeleteResponse> {
    return apiClient.delete<UserDeleteResponse>(`/users/${userId}`);
  },

  async uploadAvatar(userId: number, file: File): Promise<UserResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.postFormData<UserResponse>(`/users/${userId}/avatar`, formData);
  },

  async deleteAvatar(userId: number): Promise<UserResponse> {
    return apiClient.delete<UserResponse>(`/users/${userId}/avatar`);
  },
};
