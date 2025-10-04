import PageHeader from "@/components/PageHeader";
import { AdminGuard } from "@/components/AdminGuard";

export default function AdminLog() {
  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="Í\í°" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600">
              Í\í°;boŸÅˆšgY
            </p>
          </div>
        </div>
      </div>
    </AdminGuard>
  );
}
