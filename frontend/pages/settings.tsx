import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/hooks/useAuth";
import { userService } from "@/services/users";

export default function Settings() {
  const { user, checkAuth } = useAuth();
  const [nickname, setNickname] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (user) {
      setNickname(user.nickname || "");
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await userService.updateUser(user.id, { nickname: nickname.trim() || null });
      await checkAuth();
      setSuccess(true);
    } catch {
      setError("ニックネームの更新に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="設定" />

        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-1">表示名の設定</h2>
            <p className="text-sm text-gray-500 mb-4">
              ニックネームを設定すると、投稿者名やコメント欄でユーザー名の代わりに表示されます。空欄にするとユーザー名が表示されます。
            </p>

            <form onSubmit={handleSubmit}>
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="user-name"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    ユーザー名
                  </label>
                  <input
                    id="user-name"
                    type="text"
                    value={user?.user_name || ""}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-500"
                    disabled
                  />
                </div>
                <div>
                  <label htmlFor="nickname" className="block text-sm font-medium text-gray-700 mb-1">
                    ニックネーム
                  </label>
                  <input
                    id="nickname"
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    maxLength={64}
                    placeholder="表示したい名前を入力"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              {error && (
                <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                  {error}
                </div>
              )}
              {success && (
                <div className="mt-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-sm">
                  ニックネームを更新しました
                </div>
              )}

              <div className="mt-6 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm font-medium disabled:opacity-50"
                >
                  {saving ? "保存中..." : "保存"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
