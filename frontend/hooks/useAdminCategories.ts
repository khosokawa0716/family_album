import { useState, useEffect } from "react";
import { categoryService } from "@/services/categories";
import { CategoryResponse, CategoryCreateRequest, CategoryUpdateRequest } from "@/types/categories";

export const useAdminCategories = () => {
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCategories = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await categoryService.getCategories();
      setCategories(response);
    } catch (err) {
      console.error("Error fetching categories:", err);
      setError("カテゴリの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  const createCategory = async (categoryData: CategoryCreateRequest): Promise<void> => {
    try {
      await categoryService.createCategory(categoryData);
      await fetchCategories();
    } catch (err: any) {
      console.error("Error creating category:", err);
      if (err.response?.status === 409) {
        throw new Error("このカテゴリ名は既に使用されています");
      }
      throw new Error("カテゴリの作成に失敗しました");
    }
  };

  const updateCategory = async (categoryId: number, categoryData: CategoryUpdateRequest): Promise<void> => {
    try {
      await categoryService.updateCategory(categoryId, categoryData);
      await fetchCategories();
    } catch (err: any) {
      console.error("Error updating category:", err);
      if (err.response?.status === 409) {
        throw new Error("このカテゴリ名は既に使用されています");
      }
      throw new Error("カテゴリの更新に失敗しました");
    }
  };

  const deleteCategory = async (categoryId: number): Promise<void> => {
    try {
      await categoryService.deleteCategory(categoryId);
      await fetchCategories();
    } catch (err) {
      console.error("Error deleting category:", err);
      throw new Error("カテゴリの削除に失敗しました");
    }
  };

  return {
    categories,
    isLoading,
    error,
    createCategory,
    updateCategory,
    deleteCategory,
    refreshCategories: fetchCategories,
  };
};
