from fastapi import APIRouter, HTTPException, Depends
from datetime import timedelta
from schemas import LoginRequest, LoginResponse, UserResponse, LogoutResponse
from auth import authenticate_user, create_access_token
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from dependencies import get_current_user
from models import User

router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(login_request: LoginRequest):
    user = authenticate_user(login_request.user_name, login_request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != 1:
        raise HTTPException(
            status_code=403,
            detail="User account is disabled",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_name, "user_id": user.id},
        expires_delta=access_token_expires
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/logout", response_model=LogoutResponse)
def logout(current_user: User = Depends(get_current_user)):
    # ユーザーが無効化されていないかチェック
    if current_user.status != 1:
        raise HTTPException(
            status_code=403,
            detail="User account is disabled"
        )

    # 現在の実装では、JWT はステートレスなので
    # サーバー側でトークンを無効化する必要はない
    # 実際のログアウト処理はクライアント側でトークンを削除することで行う

    return LogoutResponse(message="Successfully logged out")