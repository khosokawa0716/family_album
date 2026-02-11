import Link from "next/link";
import { Image, LogOut, Upload } from "lucide-react";
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
        <div className="flex justify-between items-center py-4 sm:py-6">
          <div className="flex items-center space-x-8">
            <h1 className="text-xl sm:text-3xl font-bold text-gray-900">{title}</h1>
            <nav className="flex space-x-2 sm:space-x-4">
              <Link
                href="/photo/list"
                className="text-gray-600 hover:text-gray-900 px-2 sm:px-3 py-2 rounded-md text-sm font-medium inline-flex items-center"
              >
                <Image className="h-5 w-5 sm:mr-2" aria-hidden="true" />
                <span className="hidden sm:inline">写真一覧</span>
                <span className="sr-only">写真一覧</span>
              </Link>
              <Link
                href="/photo/upload"
                className="text-gray-600 hover:text-gray-900 px-2 sm:px-3 py-2 rounded-md text-sm font-medium inline-flex items-center"
              >
                <Upload className="h-5 w-5 sm:mr-2" aria-hidden="true" />
                <span className="hidden sm:inline">写真アップロード</span>
                <span className="sr-only">写真アップロード</span>
              </Link>
            </nav>
          </div>
          <div className="flex items-center space-x-2 sm:space-x-4">
            {children}
            {user && (
              <div className="flex items-center space-x-2 sm:space-x-3">
                <span className="hidden sm:inline text-sm text-gray-600">{user.user_name}</span>
                <button
                  onClick={logout}
                  className="bg-gray-600 hover:bg-gray-700 text-white px-2 sm:px-3 py-2 rounded-md text-sm font-medium inline-flex items-center"
                >
                  <LogOut className="h-4 w-4 sm:mr-2" aria-hidden="true" />
                  <span className="hidden sm:inline">ログアウト</span>
                  <span className="sr-only">ログアウト</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
