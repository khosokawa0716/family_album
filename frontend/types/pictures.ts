export interface PictureRequest {
  limit?: number;           // 取得件数（最大100件）
  offset?: number;          // 開始位置
  category?: string;        // カテゴリID（カンマ区切りで複数指定可）
  category_and?: string;    // カテゴリID（AND検索、カンマ区切り）
  year?: number;            // 撮影年
  month?: number;           // 撮影月
  start_date?: string;      // 開始日（YYYY-MM-DD形式）
  end_date?: string;        // 終了日（YYYY-MM-DD形式）
}

export interface Picture {
  id: number;
  family_id: number;
  uploaded_by: number;
  title: string;
  description: string;
  file_path: string;
  thumbnail_path: string;
  file_size: number;
  mime_type: string;
  width: number;
  height: number;
  taken_date: string; // ISO 8601 date string
  category_id: number;
  status: number;
  create_date: string; // ISO 8601 date string
  update_date: string; // ISO 8601 date string
}

export interface PictureResponse {
  pictures: Picture[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}
