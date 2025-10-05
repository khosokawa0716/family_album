import { useState, useEffect } from "react";
import { logService } from "@/services/logs";
import { OperationLogResponse } from "@/types/logs";

export const useAdminLogs = () => {
  const [logs, setLogs] = useState<OperationLogResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await logService.getLogs();
        // 降順ソート（最新のログが上）
        const sortedLogs = response.sort((a, b) =>
          new Date(b.create_date).getTime() - new Date(a.create_date).getTime()
        );
        setLogs(sortedLogs);
      } catch (err) {
        console.error("Error fetching logs:", err);
        setError("操作ログの取得に失敗しました");
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  return {
    logs,
    loading,
    error,
  };
};
