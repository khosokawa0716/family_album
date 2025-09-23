from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from database import get_db
from models import Category, User
from schemas import CategoryResponse, CategoryCreateRequest
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


@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(
    category_data: CategoryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    カテゴリ追加API（管理者のみ）

    管理者権限を持つ認証済みユーザーがカテゴリを追加できます。
    - 管理者権限（type=10）が必要
    - family_idは認証ユーザーの家族IDが自動設定
    - 同一家族内での重複カテゴリ名は禁止
    - 新規作成時はstatus=1（有効）で自動設定
    """
    try:
        # 管理者権限チェック
        if current_user.type != 10:
            raise HTTPException(status_code=403, detail="Admin access required")

        # 同一家族内での重複カテゴリ名チェック
        existing_category = db.query(Category).filter(
            Category.family_id == current_user.family_id,
            Category.name == category_data.name,
            Category.status == 1
        ).first()

        if existing_category:
            raise HTTPException(
                status_code=409,
                detail=f"Category with name '{category_data.name}' already exists in this family"
            )

        # 新しいカテゴリの作成
        new_category = Category(
            family_id=current_user.family_id,
            name=category_data.name,
            description=category_data.description,
            status=1  # 新規作成時は有効状態
        )

        db.add(new_category)
        db.commit()
        db.refresh(new_category)

        return new_category

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Category name already exists or database constraint violation"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create category: {str(e)}")