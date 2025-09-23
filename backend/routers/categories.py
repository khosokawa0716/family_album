from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from database import get_db
from models import Category, User
from schemas import CategoryResponse, CategoryCreateRequest, CategoryUpdateRequest
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


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_data: CategoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    カテゴリ編集API（管理者のみ）

    管理者権限を持つ認証済みユーザーがカテゴリを編集できます。
    - 管理者権限（type=10）が必要
    - 編集対象カテゴリは認証ユーザーと同じfamily_idのもののみ
    - カテゴリ名と説明を編集可能（いずれも任意）
    - 重複するカテゴリ名は同一家族内で禁止（自分自身を除く）
    - 削除済み（status=0）カテゴリは編集不可
    - 編集時はupdate_dateが自動更新される
    """
    try:
        # 管理者権限チェック
        if current_user.type != 10:
            raise HTTPException(status_code=403, detail="Admin access required")

        # IDの妥当性チェック
        if category_id <= 0:
            raise HTTPException(status_code=422, detail="Category ID must be a positive integer")

        # 編集対象カテゴリの取得（家族スコープで制限）
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.family_id == current_user.family_id
        ).first()

        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # 削除済みカテゴリのチェック
        if category.status == 0:
            raise HTTPException(status_code=410, detail="Category has been deleted")

        # 更新項目がない場合のチェック
        if category_data.name is None and category_data.description is None:
            raise HTTPException(status_code=422, detail="At least one field (name or description) must be provided for update")

        # 名前が変更される場合、重複チェック（自分自身を除く）
        if category_data.name is not None and category_data.name != category.name:
            existing_category = db.query(Category).filter(
                Category.family_id == current_user.family_id,
                Category.name == category_data.name,
                Category.status == 1,
                Category.id != category_id  # 自分自身を除く
            ).first()

            if existing_category:
                raise HTTPException(
                    status_code=409,
                    detail=f"Category with name '{category_data.name}' already exists in this family"
                )

        # カテゴリの更新
        if category_data.name is not None:
            category.name = category_data.name
        if category_data.description is not None:
            category.description = category_data.description

        db.commit()
        db.refresh(category)

        return category

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update category: {str(e)}")