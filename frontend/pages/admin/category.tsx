import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import { AdminGuard } from "@/components/AdminGuard";
import { useAdminCategories } from "@/hooks/useAdminCategories";
import { CategoryResponse } from "@/types/categories";

export default function AdminCategory() {
  const { categories, isLoading, createCategory, updateCategory, deleteCategory } =
    useAdminCategories();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<CategoryResponse | null>(null);

  const [formData, setFormData] = useState({ name: "", description: "" });
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleOpenCreateModal = () => {
    setFormData({ name: "", description: "" });
    setFormError("");
    setIsCreateModalOpen(true);
  };

  const handleOpenEditModal = (category: CategoryResponse) => {
    setSelectedCategory(category);
    setFormData({ name: category.name, description: category.description || "" });
    setFormError("");
    setIsEditModalOpen(true);
  };

  const handleOpenDeleteDialog = (category: CategoryResponse) => {
    setSelectedCategory(category);
    setIsDeleteDialogOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setFormError("カテゴリ名は必須です");
      return;
    }

    setIsSubmitting(true);
    setFormError("");
    try {
      await createCategory({
        name: formData.name.trim(),
        description: formData.description.trim() || null,
      });
      setIsCreateModalOpen(false);
      setFormData({ name: "", description: "" });
    } catch (err: any) {
      setFormError(err.message || "カテゴリの作成に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCategory) return;
    if (!formData.name.trim()) {
      setFormError("カテゴリ名は必須です");
      return;
    }

    setIsSubmitting(true);
    setFormError("");
    try {
      await updateCategory(selectedCategory.id, {
        name: formData.name.trim(),
        description: formData.description.trim() || null,
      });
      setIsEditModalOpen(false);
      setSelectedCategory(null);
      setFormData({ name: "", description: "" });
    } catch (err: any) {
      setFormError(err.message || "カテゴリの更新に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedCategory) return;

    setIsSubmitting(true);
    try {
      await deleteCategory(selectedCategory.id);
      setIsDeleteDialogOpen(false);
      setSelectedCategory(null);
    } catch (err: any) {
      alert(err.message || "カテゴリの削除に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="カテゴリ管理">
          <button
            onClick={handleOpenCreateModal}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            ＋新規カテゴリ追加
          </button>
        </PageHeader>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow">
            {isLoading ? (
              <div className="p-6 text-center text-gray-600">Loading...</div>
            ) : categories.length === 0 ? (
              <div className="p-6 text-center text-gray-600">カテゴリがありません</div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      カテゴリ名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      説明
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      編集
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      削除
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {categories.map((category) => (
                    <tr key={category.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {category.name}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        {category.description || "-"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => handleOpenEditModal(category)}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          編集
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => handleOpenDeleteDialog(category)}
                          className="text-red-600 hover:text-red-900"
                        >
                          削除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Create Modal */}
        {isCreateModalOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => !isSubmitting && setIsCreateModalOpen(false)}
          >
            <div
              className="bg-white rounded-lg p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4">新規カテゴリ追加</h2>
              <form onSubmit={handleCreateSubmit}>
                <div className="mb-4">
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                    カテゴリ名 <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    disabled={isSubmitting}
                  />
                </div>
                <div className="mb-4">
                  <label
                    htmlFor="description"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    説明
                  </label>
                  <textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    rows={3}
                    disabled={isSubmitting}
                  />
                </div>
                {formError && <div className="mb-4 text-sm text-red-600">{formError}</div>}
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                    disabled={isSubmitting}
                  >
                    キャンセル
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:bg-gray-400"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "作成中..." : "作成"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Modal */}
        {isEditModalOpen && selectedCategory && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => !isSubmitting && setIsEditModalOpen(false)}
          >
            <div
              className="bg-white rounded-lg p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4">カテゴリ編集</h2>
              <form onSubmit={handleEditSubmit}>
                <div className="mb-4">
                  <label
                    htmlFor="edit-name"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    カテゴリ名 <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    id="edit-name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    disabled={isSubmitting}
                  />
                </div>
                <div className="mb-4">
                  <label
                    htmlFor="edit-description"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    説明
                  </label>
                  <textarea
                    id="edit-description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    rows={3}
                    disabled={isSubmitting}
                  />
                </div>
                {formError && <div className="mb-4 text-sm text-red-600">{formError}</div>}
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setIsEditModalOpen(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                    disabled={isSubmitting}
                  >
                    キャンセル
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:bg-gray-400"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "更新中..." : "更新"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        {isDeleteDialogOpen && selectedCategory && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => !isSubmitting && setIsDeleteDialogOpen(false)}
          >
            <div
              className="bg-white rounded-lg p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4">カテゴリ削除</h2>
              <p className="text-sm text-gray-700 mb-4">
                <strong>{selectedCategory.name}</strong> を削除します。
                <br />
                このカテゴリを削除すると、紐づく写真のカテゴリがクリアされます。よろしいですか？
              </p>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsDeleteDialogOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  disabled={isSubmitting}
                >
                  キャンセル
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  className="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 disabled:bg-gray-400"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "削除中..." : "削除"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
