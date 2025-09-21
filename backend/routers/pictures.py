from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract, desc
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import Picture, User, Category
from schemas import PictureListResponse, PictureResponse
from dependencies import get_current_user

router = APIRouter()

@router.get("/pictures", response_model=PictureListResponse)
def get_pictures(
    limit: int = Query(20, ge=1, le=100, description="取得件数（最大100件）"),
    offset: int = Query(0, ge=0, description="開始位置"),
    category: Optional[str] = Query(None, description="カテゴリID（カンマ区切りで複数指定可）"),
    category_and: Optional[str] = Query(None, description="カテゴリID（AND検索、カンマ区切り）"),
    year: Optional[int] = Query(None, ge=1900, le=2100, description="撮影年"),
    month: Optional[int] = Query(None, ge=1, le=12, description="撮影月"),
    start_date: Optional[str] = Query(None, description="開始日（YYYY-MM-DD形式）"),
    end_date: Optional[str] = Query(None, description="終了日（YYYY-MM-DD形式）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    写真一覧取得API

    フィルタリング機能:
    - category: OR検索（「風景」または「人物」）
    - category_and: AND検索（「風景」かつ「夕日」）
    - year/month: 撮影年月での絞り込み
    - start_date/end_date: 日付範囲での絞り込み

    ページネーション:
    - limit: 取得件数（デフォルト20、最大100）
    - offset: 開始位置
    - has_more: 次ページ存在フラグ
    """

    # 基本クエリ: 自分の家族の有効な写真のみ
    query = db.query(Picture).filter(
        and_(
            Picture.family_id == current_user.family_id,
            Picture.status == 1
        )
    )

    # カテゴリフィルタ（OR検索）
    if category:
        try:
            category_ids = [int(cid.strip()) for cid in category.split(',')]
            query = query.filter(Picture.category_id.in_(category_ids))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category format")

    # カテゴリフィルタ（AND検索）
    if category_and:
        try:
            category_ids = [int(cid.strip()) for cid in category_and.split(',')]
            # AND検索の場合、複数のサブクエリで実現
            for cid in category_ids:
                subquery = db.query(Picture.id).filter(
                    and_(
                        Picture.family_id == current_user.family_id,
                        Picture.category_id == cid,
                        Picture.status == 1
                    )
                )
                query = query.filter(Picture.id.in_(subquery))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category_and format")

    # 年フィルタ
    if year:
        query = query.filter(extract('year', Picture.taken_date) == year)

    # 月フィルタ
    if month:
        if not year:
            raise HTTPException(status_code=400, detail="Year is required when filtering by month")
        query = query.filter(extract('month', Picture.taken_date) == month)

    # 日付範囲フィルタ
    if start_date or end_date:
        try:
            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(Picture.taken_date >= start_dt)
            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                # 終了日は23:59:59まで含める
                from datetime import timedelta
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(Picture.taken_date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # 総件数取得
    total = query.count()

    # ソート（撮影日降順、撮影日がない場合は作成日降順）
    query = query.order_by(
        desc(Picture.taken_date.is_(None)),  # taken_dateがNULLの場合は後ろに
        desc(Picture.taken_date),
        desc(Picture.create_date)
    )

    # ページネーション適用
    pictures = query.offset(offset).limit(limit).all()

    # 次ページ存在判定
    has_more = (offset + limit) < total

    return PictureListResponse(
        pictures=pictures,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more
    )