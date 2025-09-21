from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from models import User, OperationLog
from schemas import UserCreate, UserUpdate, UserResponse
from auth import pwd_context
from dependencies import get_current_user
from typing import List
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import json

router = APIRouter(prefix="/api", tags=["users"])

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(user.password)

    db_user = User(
        user_name=user.user_name,
        password=hashed_password,
        email=user.email,
        type=user.type,
        family_id=user.family_id
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"User creation failed: {str(e)}")

@router.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # ユーザーが無効化されている場合のチェック
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    # 管理者権限チェック (type = 10 が管理者)
    if current_user.type != 10:
        raise HTTPException(status_code=403, detail="Insufficient permissions. Admin access required.")

    # 全ユーザーを取得（無効化されたユーザーも含む）
    try:
        users = db.query(User).all()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {str(e)}")

@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # ユーザーが無効化されている場合のチェック
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    # 編集対象ユーザーを取得
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 権限チェック
    is_admin = current_user.type == 10
    is_self = current_user.id == user_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Insufficient permissions. You can only edit your own profile.")

    # 一般ユーザーが権限フィールドを変更しようとした場合のチェック
    if not is_admin:
        if user_update.type is not None:
            raise HTTPException(status_code=403, detail="Insufficient permissions. You cannot change user type.")
        if user_update.family_id is not None:
            raise HTTPException(status_code=403, detail="Insufficient permissions. You cannot change family ID.")
        if user_update.status is not None:
            raise HTTPException(status_code=403, detail="Insufficient permissions. You cannot change user status.")

    # フィールドの更新（提供されたフィールドのみ）
    update_data = user_update.model_dump(exclude_unset=True)

    try:
        for field, value in update_data.items():
            if field == "password":
                # パスワードはハッシュ化して保存
                setattr(target_user, field, pwd_context.hash(value))
            else:
                setattr(target_user, field, value)

        db.commit()
        db.refresh(target_user)
        return target_user

    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig)
        if "user_name" in error_msg:
            raise HTTPException(status_code=409, detail="Username already exists")
        elif "email" in error_msg:
            raise HTTPException(status_code=409, detail="Email already exists")
        else:
            raise HTTPException(status_code=409, detail="Data integrity violation")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@router.get("/users/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")
    return current_user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # ユーザーが無効化されている場合のチェック
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    # 管理者権限チェック (type = 10 が管理者)
    if current_user.type != 10:
        raise HTTPException(status_code=403, detail="Insufficient permissions. Admin access required.")

    # 削除対象ユーザーを取得
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 既に削除済み（status=0）の場合
    if target_user.status == 0:
        raise HTTPException(status_code=409, detail="User is already deleted")

    # 削除前のユーザー情報をスナップショットとして保存
    user_snapshot = {
        "user_name": target_user.user_name,
        "email": target_user.email,
        "type": target_user.type,
        "family_id": target_user.family_id,
        "status": target_user.status
    }

    try:
        # 論理削除: statusを0に変更
        target_user.status = 0

        # 操作ログを記録
        operation_log = OperationLog(
            user_id=current_user.id,
            operation="DELETE",
            target_type="user",
            target_id=user_id,
            detail=json.dumps(user_snapshot)
        )
        db.add(operation_log)

        db.commit()

        return {
            "message": "User deleted successfully",
            "deleted_user_id": user_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")