export interface CommentResponse {
  id: number;
  content: string;
  user_id: number;
  picture_id: number;
  user_name: string;
  nickname?: string | null;
  create_date: string; // ISO 8601 date string
  update_date: string; // ISO 8601 date string
}

export interface CommentCreateRequest {
  content: string;
}

export interface CommentUpdateRequest {
  content: string;
}
