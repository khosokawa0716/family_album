export interface CategoryResponse {
  id: number;
  family_id: number;
  name: string;
  description: string | null;
  status: number;
  create_date: string; // ISO 8601 date string
  update_date: string; // ISO 8601 date string
}

export interface CategoryCreateRequest {
  name: string;
  description?: string | null;
}

export interface CategoryUpdateRequest {
  name?: string;
  description?: string | null;
}

export interface CategoryDeleteResponse {
  message: string;
  category_id: number;
}
