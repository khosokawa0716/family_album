import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { AdminGuard } from "@/components/AdminGuard";

export default function AdminMenu() {
  const adminMenuItems = [
    {
      title: "æü¶ü¡",
      description: "æü¶ünı ûèÆûJd)P¡",
      href: "/admin/user",
      icon: "=e",
    },
    {
      title: "«Æ´ê¡",
      description: "«Æ´ênı ûèÆûJdh:	ô",
      href: "/admin/category",
      icon: "=Á",
    },
    {
      title: "™©C¡",
      description: "JdUŒ_™n©C",
      href: "/admin/restore",
      icon: "=",
    },
    {
      title: "Í\í°",
      description: "·¹ÆànÍ\et’º",
      href: "/admin/log",
      icon: "=Ë",
    },
  ];

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="¡(áËåü" />

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
