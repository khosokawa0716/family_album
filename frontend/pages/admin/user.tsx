import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import { AdminGuard } from "@/components/AdminGuard";
import { useAdminUsers } from "@/hooks/useAdminUsers";
import { UserCreateRequest, UserUpdateRequest } from "@/types/users";

export default function AdminUser() {
  const { users, currentUser, loading, error, createUser, updateUser, deleteUser } = useAdminUsers();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);

  const [createForm, setCreateForm] = useState({
    user_name: "",
    password: "",
    email: "",
    type: 0,
  });

  const [editForm, setEditForm] = useState({
    user_name: "",
    email: "",
    type: 0,
    status: 1,
  });

  const selectedUser = users.find((u) => u.id === selectedUserId);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!currentUser) {
      alert("ユーザー情報を取得できませんでした");
      return;
    }

    const userData: UserCreateRequest = {
      user_name: createForm.user_name,
      password: createForm.password,
      email: createForm.email || null,
      type: createForm.type,
      family_id: currentUser.family_id,
    };

    const success = await createUser(userData);
    if (success) {
      setShowCreateModal(false);
      setCreateForm({ user_name: "", password: "", email: "", type: 0 });
    } else {
      alert("ユーザーの作成に失敗しました");
    }
  };

  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedUserId) return;

    const userData: UserUpdateRequest = {
      user_name: editForm.user_name,
      email: editForm.email || null,
      type: editForm.type,
      status: editForm.status,
    };

    const success = await updateUser(selectedUserId, userData);
    if (success) {
      setShowEditModal(false);
      setSelectedUserId(null);
    } else {
      alert("ユーザーの更新に失敗しました");
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUserId) return;

    if (currentUser && selectedUserId === currentUser.id) {
      alert("自分自身を削除することはできません");
      return;
    }

    const success = await deleteUser(selectedUserId);
    if (success) {
      setShowDeleteDialog(false);
      setSelectedUserId(null);
    } else {
      alert("ユーザーの削除に失敗しました");
    }
  };

  const openEditModal = (userId: number) => {
    const user = users.find((u) => u.id === userId);
    if (user) {
      setEditForm({
        user_name: user.user_name,
        email: user.email || "",
        type: user.type,
        status: user.status,
      });
      setSelectedUserId(userId);
      setShowEditModal(true);
    }
  };

  const openDeleteDialog = (userId: number) => {
    setSelectedUserId(userId);
    setShowDeleteDialog(true);
  };

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="ユーザー管理">
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            ＋新規ユーザー追加
          </button>
        </PageHeader>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Loading...</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ユーザー名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      メールアドレス
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      権限
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状態
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr key={user.id} className={user.status === 0 ? "text-gray-400" : ""}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {user.user_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {user.email || "-"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {user.type === 10 ? "管理者" : "一般"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {user.status === 1 ? "有効" : "無効"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                        <button
                          onClick={() => openEditModal(user.id)}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          編集
                        </button>
                        <button
                          onClick={() => openDeleteDialog(user.id)}
                          className="text-red-600 hover:text-red-900"
                          disabled={user.status === 0}
                        >
                          削除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 新規ユーザー追加モーダル */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-xl font-bold text-gray-900 mb-4">新規ユーザー追加</h2>
              <form onSubmit={handleCreateUser}>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="create-user-name" className="block text-sm font-medium text-gray-700 mb-1">
                      ユーザー名 *
                    </label>
                    <input
                      id="create-user-name"
                      type="text"
                      value={createForm.user_name}
                      onChange={(e) => setCreateForm({ ...createForm, user_name: e.target.value })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="create-password" className="block text-sm font-medium text-gray-700 mb-1">
                      パスワード *
                    </label>
                    <input
                      id="create-password"
                      type="password"
                      value={createForm.password}
                      onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="create-email" className="block text-sm font-medium text-gray-700 mb-1">
                      メールアドレス
                    </label>
                    <input
                      id="create-email"
                      type="email"
                      value={createForm.email}
                      onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="create-type" className="block text-sm font-medium text-gray-700 mb-1">
                      権限
                    </label>
                    <select
                      id="create-type"
                      value={createForm.type}
                      onChange={(e) => setCreateForm({ ...createForm, type: Number(e.target.value) })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value={0}>一般</option>
                      <option value={10}>管理者</option>
                    </select>
                  </div>
                </div>
                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateModal(false);
                      setCreateForm({ user_name: "", password: "", email: "", type: 0 });
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    キャンセル
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-medium"
                  >
                    作成
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ユーザー編集モーダル */}
        {showEditModal && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-xl font-bold text-gray-900 mb-4">ユーザー編集</h2>
              <form onSubmit={handleEditUser}>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="edit-user-name" className="block text-sm font-medium text-gray-700 mb-1">
                      ユーザー名 *
                    </label>
                    <input
                      id="edit-user-name"
                      type="text"
                      value={editForm.user_name}
                      onChange={(e) => setEditForm({ ...editForm, user_name: e.target.value })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="edit-email" className="block text-sm font-medium text-gray-700 mb-1">
                      メールアドレス
                    </label>
                    <input
                      id="edit-email"
                      type="email"
                      value={editForm.email}
                      onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="edit-type" className="block text-sm font-medium text-gray-700 mb-1">
                      権限
                    </label>
                    <select
                      id="edit-type"
                      value={editForm.type}
                      onChange={(e) => setEditForm({ ...editForm, type: Number(e.target.value) })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value={0}>一般</option>
                      <option value={10}>管理者</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="edit-status" className="block text-sm font-medium text-gray-700 mb-1">
                      状態
                    </label>
                    <select
                      id="edit-status"
                      value={editForm.status}
                      onChange={(e) => setEditForm({ ...editForm, status: Number(e.target.value) })}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      disabled
                    >
                      <option value={1}>有効</option>
                      <option value={0}>無効</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">※状態の変更は現在サポートされていません</p>
                  </div>
                </div>
                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedUserId(null);
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    キャンセル
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-medium"
                  >
                    更新
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* 削除確認ダイアログ */}
        {showDeleteDialog && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-xl font-bold text-gray-900 mb-4">ユーザー削除確認</h2>
              <p className="text-gray-700 mb-6">
                ユーザー「{selectedUser.user_name}」を削除してもよろしいですか？
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowDeleteDialog(false);
                    setSelectedUserId(null);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  キャンセル
                </button>
                <button
                  onClick={handleDeleteUser}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium"
                >
                  削除
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
