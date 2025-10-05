export interface OperationLogResponse {
  id: number;
  user_id: number;
  user_name?: string;
  operation: string;
  target_type: string;
  target_id: number | null;
  detail: string | null;
  create_date: string; // ISO 8601 date string
}
