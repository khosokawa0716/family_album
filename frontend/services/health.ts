import { apiClient } from "../lib/api/client";
import { HealthResponse } from "../types/api";

export const healthService = {
  async getHealthStatus(): Promise<HealthResponse> {
    return apiClient.get<HealthResponse>("/health");
  },
};
