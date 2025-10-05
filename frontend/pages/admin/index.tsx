import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { AdminGuard } from "@/components/AdminGuard";

export default function AdminMenu() {
  const adminMenuItems = [
    {
      title: "ユーザー管理",
      description: "ユーザーの追加・編集・削除",
      href: "/admin/user",
      icon: "👤",
    },
    {
      title: "カテゴリ管理",
      description: "カテゴリの追加・編集・削除・並び替え",
      href: "/admin/category",
      icon: "📁",
    },
    {
      title: "削除済み写真",
      description: "削除済み写真の確認・復元",
      href: "/admin/restore",
      icon: "🗑",
    },
    {
      title: "操作ログ",
      description: "ユーザーの操作履歴を確認",
      href: "/admin/log",
      icon: "📋",
    },
  ];

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="管理メニュー" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {adminMenuItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6"
              >
                <div className="flex items-start space-x-4">
                  <div className="text-4xl">{item.icon}</div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {item.title}
                    </h3>
                    <p className="text-sm text-gray-600">{item.description}</p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </AdminGuard>
  );
}
