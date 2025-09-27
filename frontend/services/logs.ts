import { apiClient } from "@/lib/api/client";
import { OperationLogResponse } from "@/types/logs";

export const logService = {
  async getLogs(): Promise<OperationLogResponse[]> {
    return apiClient.get<OperationLogResponse[]>("/logs");
  },
};
