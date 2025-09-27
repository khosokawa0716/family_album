import { apiClient } from "@/lib/api/client";
import {
  CategoryResponse,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  CategoryDeleteResponse,
} from "@/types/categories";

export const categoryService = {
  async getCategories(): Promise<CategoryResponse[]> {
    return apiClient.get<CategoryResponse[]>("/categories");
  },

  async createCategory(categoryData: CategoryCreateRequest): Promise<CategoryResponse> {
    return apiClient.post<CategoryResponse>("/categories", categoryData);
  },

  async updateCategory(
    categoryId: number,
    categoryData: CategoryUpdateRequest,
  ): Promise<CategoryResponse> {
    return apiClient.patch<CategoryResponse>(`/categories/${categoryId}`, categoryData);
  },

  async deleteCategory(categoryId: number): Promise<CategoryDeleteResponse> {
    return apiClient.delete<CategoryDeleteResponse>(`/categories/${categoryId}`);
  },
};
