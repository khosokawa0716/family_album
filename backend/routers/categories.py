from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Category, User
from schemas import CategoryResponse
from dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["categories"])


@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    カテゴリ一覧取得API

    認証済みユーザーが自分の家族のカテゴリ一覧を取得します。
    - 有効なカテゴリ（status=1）のみ表示
    - 家族スコープでフィルタリング（family_id）
    - 作成日昇順でソート
    """
    try:
        # 有効なカテゴリを家族IDでフィルタし、作成日昇順でソート
        categories = db.query(Category).filter(
            Category.family_id == current_user.family_id,
            Category.status == 1
        ).order_by(Category.create_date.asc()).all()

        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve categories: {str(e)}")