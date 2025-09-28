import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

interface PageHeaderProps {
  title: string;
  children?: React.ReactNode;
}

export default function PageHeader({ title, children }: PageHeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <div className="flex items-center space-x-8">
            <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
            <nav className="flex space-x-4">
              <Link
                href="/photo/list"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                写真一覧
              </Link>
              <Link
                href="/photo/upload"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                写真アップロード
              </Link>
            </nav>
          </div>
          <div className="flex items-center space-x-4">
            {children}
            {user && (
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-600">{user.user_name}</span>
                <button
                  onClick={logout}
                  className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  ログアウト
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
