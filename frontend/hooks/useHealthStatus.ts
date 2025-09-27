import { useState, useEffect } from "react";
import { healthService } from "@/services/health";
import { HealthResponse } from "@/types/api";
import { ApiError } from "@/lib/api/client";

export const useHealthStatus = () => {
  const [healthStatus, setHealthStatus] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealthStatus = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await healthService.getHealthStatus();
        setHealthStatus(data);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(`API Error: ${err.message} (Status: ${err.status})`);
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchHealthStatus();
  }, []);

  const refetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await healthService.getHealthStatus();
      setHealthStatus(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API Error: ${err.message} (Status: ${err.status})`);
      } else {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    } finally {
      setLoading(false);
    }
  };

  return {
    healthStatus,
    loading,
    error,
    refetch,
  };
};
