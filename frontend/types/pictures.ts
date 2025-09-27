export interface PictureRequest {
  limit?: number; // 取得件数（最大100件）
  offset?: number; // 開始位置
  category?: string; // カテゴリID（カンマ区切りで複数指定可）
  category_and?: string; // カテゴリID（AND検索、カンマ区切り）
  year?: number; // 撮影年
  month?: number; // 撮影月
  start_date?: string; // 開始日（YYYY-MM-DD形式）
  end_date?: string; // 終了日（YYYY-MM-DD形式）
}

export interface PictureResponse {
  id: number;
  family_id: number;
  uploaded_by: number;
  title: string | null;
  description: string | null;
  file_path: string;
  thumbnail_path: string | null;
  file_size: number | null;
  mime_type: string | null;
  width: number | null;
  height: number | null;
  taken_date: string | null; // ISO 8601 date string
  category_id: number | null;
  status: number;
  create_date: string; // ISO 8601 date string
  update_date: string; // ISO 8601 date string
}

export interface PictureListResponse {
  pictures: PictureResponse[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PictureCreateRequest {
  title?: string | null;
  description?: string | null;
  category_id?: number | null;
}

export interface PictureRestoreResponse {
  message: string;
}
