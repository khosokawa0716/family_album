from fastapi import APIRouter, HTTPException, Depends
from database import db
from models import User
from schemas import UserCreate, UserResponse
from auth import pwd_context
from dependencies import get_current_user
from typing import List

router = APIRouter(prefix="/api", tags=["users"])

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    hashed_password = pwd_context.hash(user.password)

    db_user = User(
        user_name=user.user_name,
        password=hashed_password,
        email=user.email,
        type=user.type,
        family_id=user.family_id
    )

    try:
        db.session.add(db_user)
        db.session.commit()
        db.session.refresh(db_user)
        return db_user
    except Exception as e:
        db.session.rollback()
        raise HTTPException(status_code=400, detail=f"User creation failed: {str(e)}")

@router.get("/users", response_model=List[UserResponse])
def get_users(current_user: User = Depends(get_current_user)):
    # ユーザーが無効化されている場合のチェック
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    # 管理者権限チェック (type = 10 が管理者)
    if current_user.type != 10:
        raise HTTPException(status_code=403, detail="Insufficient permissions. Admin access required.")

    # 全ユーザーを取得（無効化されたユーザーも含む）
    try:
        users = db.session.query(User).all()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {str(e)}")

@router.get("/users/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")
    return current_user