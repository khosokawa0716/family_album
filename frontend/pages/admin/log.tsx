import PageHeader from "@/components/PageHeader";
import { AdminGuard } from "@/components/AdminGuard";
import { useAdminLogs } from "@/hooks/useAdminLogs";
import { OperationLogResponse } from "@/types/logs";

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}/${month}/${day} ${hours}:${minutes}`;
};

const formatDetail = (detail: string | null): string => {
  if (!detail) return "-";
  try {
    const parsed = JSON.parse(detail);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return detail;
  }
};

const getOperationClass = (operation: string): string => {
  switch (operation.toUpperCase()) {
    case "DELETE":
      return "text-red-600 font-medium";
    case "CREATE":
      return "text-green-600 font-medium";
    case "UPDATE":
      return "text-blue-600 font-medium";
    default:
      return "text-gray-700";
  }
};

const LogRow = ({ log }: { log: OperationLogResponse }) => {
  return (
    <tr className="border-b border-gray-200 hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
        {formatDate(log.create_date)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
        {log.user_name || `ID: ${log.user_id}`}
      </td>
      <td className={`px-6 py-4 whitespace-nowrap text-sm ${getOperationClass(log.operation)}`}>
        {log.operation}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
        {log.target_type}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
        {log.target_id ?? "-"}
      </td>
      <td className="px-6 py-4 text-sm text-gray-700 max-w-md truncate">
        <span className="whitespace-pre-wrap break-all">
          {formatDetail(log.detail)}
        </span>
      </td>
    </tr>
  );
};

export default function AdminLog() {
  const { logs, loading, error } = useAdminLogs();

  if (error) {
    alert(error);
  }

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="操作ログ" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow">
            {loading ? (
              <div className="p-6 text-center text-gray-600">Loading...</div>
            ) : logs.length === 0 ? (
              <div className="p-6 text-center text-gray-600">
                操作ログはありません
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        日時
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ユーザー
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作内容
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        対象タイプ
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        対象ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        詳細
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {logs.map((log) => (
                      <LogRow key={log.id} log={log} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminGuard>
  );
}
