import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useLogin } from "../hooks/useLogin";

interface UserInfo {
  id: number;
  user_name: string;
  email: string | null;
  type: number;
  family_id: number;
  status: number;
  create_date: string;
  update_date: string;
}

export default function TmpUserPage() {
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const router = useRouter();
  const { logout } = useLogin();

  useEffect(() => {
    // ローカルストレージからユーザー情報を取得
    const token = localStorage.getItem("access_token");
    const user = localStorage.getItem("user");

    if (!token || !user) {
      // トークンまたはユーザー情報がない場合はログインページにリダイレクト
      router.push("/login");
      return;
    }

    try {
      const parsedUser = JSON.parse(user);
      setUserInfo(parsedUser);
    } catch (error) {
      console.error("ユーザー情報の解析に失敗しました:", error);
      router.push("/login");
    }
  }, [router]);

  const handleLogout = () => {
    logout();
  };

  if (!userInfo) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md mx-auto bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 bg-indigo-600">
          <h1 className="text-xl font-bold text-white">ユーザー情報</h1>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">ID</label>
              <p className="mt-1 text-sm text-gray-900">{userInfo.id}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">ユーザー名</label>
              <p className="mt-1 text-sm text-gray-900">{userInfo.user_name}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">メールアドレス</label>
              <p className="mt-1 text-sm text-gray-900">{userInfo.email || "未設定"}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">ユーザータイプ</label>
              <p className="mt-1 text-sm text-gray-900">
                {userInfo.type === 10 ? "管理者" : "一般ユーザー"}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">ファミリーID</label>
              <p className="mt-1 text-sm text-gray-900">{userInfo.family_id}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">ステータス</label>
              <p className="mt-1 text-sm text-gray-900">
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  userInfo.status === 1
                    ? "bg-green-100 text-green-800"
                    : "bg-red-100 text-red-800"
                }`}>
                  {userInfo.status === 1 ? "有効" : "無効"}
                </span>
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">作成日時</label>
              <p className="mt-1 text-sm text-gray-900">
                {new Date(userInfo.create_date).toLocaleString("ja-JP")}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">更新日時</label>
              <p className="mt-1 text-sm text-gray-900">
                {new Date(userInfo.update_date).toLocaleString("ja-JP")}
              </p>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-gray-50 border-t">
          <button
            onClick={handleLogout}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            ログアウト
          </button>
        </div>
      </div>
    </div>
  );
}