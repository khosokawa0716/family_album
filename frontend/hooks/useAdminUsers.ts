import { useState, useEffect, useCallback } from "react";
import { userService } from "@/services/users";
import { authService } from "@/services/auth";
import { UserResponse, UserCreateRequest, UserUpdateRequest } from "@/types/users";

export const useAdminUsers = () => {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await userService.getUsers();
      setUsers(response);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to fetch users";
      setError(errorMessage);
      console.error("Error fetching users:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = useCallback(async () => {
    try {
      const response = await authService.getCurrentUser();
      setCurrentUser(response);
    } catch (err) {
      console.error("Error fetching current user:", err);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchCurrentUser();
  }, [fetchUsers, fetchCurrentUser]);

  const createUser = async (userData: UserCreateRequest): Promise<boolean> => {
    setError(null);
    try {
      await userService.createUser(userData);
      await fetchUsers();
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create user";
      setError(errorMessage);
      console.error("Error creating user:", err);
      return false;
    }
  };

  const updateUser = async (userId: number, userData: UserUpdateRequest): Promise<boolean> => {
    setError(null);
    try {
      await userService.updateUser(userId, userData);
      await fetchUsers();
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to update user";
      setError(errorMessage);
      console.error("Error updating user:", err);
      return false;
    }
  };

  const deleteUser = async (userId: number): Promise<boolean> => {
    setError(null);
    try {
      await userService.deleteUser(userId);
      await fetchUsers();
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete user";
      setError(errorMessage);
      console.error("Error deleting user:", err);
      return false;
    }
  };

  return {
    users,
    currentUser,
    loading,
    error,
    createUser,
    updateUser,
    deleteUser,
    refreshUsers: fetchUsers,
  };
};
