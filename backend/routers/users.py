from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from database import get_db
from models import User, OperationLog
from schemas import UserCreate, UserUpdate, UserResponse
from auth import pwd_context
from dependencies import get_current_user
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
import json
import uuid
import mimetypes
import logging

from config.storage import get_storage_config, StorageConfig
from utils.url_signature import build_avatar_url, verify_url_signature, get_signature_info

router = APIRouter(prefix="/api", tags=["users"])
logger = logging.getLogger(__name__)

# HEIC画像サポートを有効化
register_heif_opener()

AVATAR_SIZE = 256


def _to_user_response(user: User) -> UserResponse:
    """User ORM オブジェクトから、avatar_pathを署名付きURLに変換したUserResponseを作成する。"""
    return UserResponse(
        id=user.id,
        user_name=user.user_name,
        nickname=user.nickname,
        avatar_path=build_avatar_url(user.avatar_path),
        email=user.email,
        type=user.type,
        family_id=user.family_id,
        status=user.status,
        create_date=user.create_date,
        update_date=user.update_date,
    )


async def process_and_save_avatar(file: UploadFile, storage_config: StorageConfig) -> str:
    """
    アバター画像のバリデーション・正方形リサイズ・保存を行うヘルパー関数。

    中央を正方形にクロップしAVATAR_SIZE四方のJPEGとして保存する
    （写真と異なりサムネイル生成は不要なファイル1枚構成）。

    Returns:
        str: 保存した相対パス（例: "avatars/xxxx.jpg"）

    Raises:
        HTTPException: バリデーションエラーまたは保存エラー
    """
    content_type = file.content_type or ""
    file_extension = Path(file.filename).suffix.lower() if file.filename else ""

    if file_extension in ['.heic', '.heif'] and content_type in ['', 'application/octet-stream']:
        content_type = 'image/heic' if file_extension == '.heic' else 'image/heif'

    if not content_type:
        raise HTTPException(status_code=400, detail="File content type is required")

    if not storage_config.is_allowed_image_type(content_type):
        raise HTTPException(
            status_code=400,
            detail=f"File type {content_type} is not allowed. "
                   f"Allowed types: {', '.join(storage_config.allowed_image_types)}"
        )

    file_content = await file.read()
    file_size = len(file_content)

    if not storage_config.is_valid_avatar_size(file_size):
        max_size_mb = storage_config.max_avatar_upload_size / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"File size ({file_size} bytes) is too large. "
                   f"Maximum allowed: {max_size_mb:.1f}MB"
        )

    try:
        image = Image.open(BytesIO(file_content))
        image = ImageOps.exif_transpose(image)

        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
            image = background
        else:
            image = image.convert('RGB')

        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar image validation failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid image file or unsupported format")

    unique_filename = f"{uuid.uuid4().hex}.jpg"
    avatar_file_path = storage_config.get_avatar_file_path(unique_filename)

    try:
        with open(avatar_file_path, 'wb') as f:
            image.save(f, format='JPEG', quality=88)
    except Exception as e:
        logger.error(f"Avatar save failed: {e}")
        if avatar_file_path.exists():
            try:
                avatar_file_path.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="Failed to save avatar file")

    return str(Path("avatars") / unique_filename)


def _delete_avatar_file(storage_config: StorageConfig, avatar_path: Optional[str]) -> None:
    """avatar_pathが指すファイルを物理削除する（存在しない場合は何もしない）。"""
    if not avatar_path:
        return
    file_path = storage_config.get_avatars_path() / Path(avatar_path).name
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete avatar file {file_path}: {e}")


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
        return _to_user_response(db_user)
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

    # 自家族のユーザーを取得（無効化されたユーザーも含む）
    try:
        users = db.query(User).filter(User.family_id == current_user.family_id).all()
        return [_to_user_response(u) for u in users]
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
        return _to_user_response(target_user)

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
    return _to_user_response(current_user)


@router.post("/users/{user_id}/avatar", response_model=UserResponse)
async def upload_avatar(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_config: StorageConfig = Depends(get_storage_config)
):
    """
    プロフィール画像（アバター）アップロードAPI

    multipart/form-dataで画像ファイルを受信し、正方形にクロップ・リサイズして保存する。
    自分自身のアバターのみ変更可能（管理者は家族内の他ユーザーも変更可能）。
    差し替え時は旧ファイルを削除する。
    """
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    is_admin = current_user.type == 10
    is_self = current_user.id == user_id
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Insufficient permissions. You can only edit your own profile.")

    relative_avatar_path = await process_and_save_avatar(file, storage_config)
    old_avatar_path = target_user.avatar_path

    try:
        target_user.avatar_path = relative_avatar_path
        db.commit()
        db.refresh(target_user)
    except Exception as e:
        db.rollback()
        _delete_avatar_file(storage_config, relative_avatar_path)
        raise HTTPException(status_code=500, detail=f"Failed to update avatar: {str(e)}")

    _delete_avatar_file(storage_config, old_avatar_path)

    return _to_user_response(target_user)


@router.delete("/users/{user_id}/avatar", response_model=UserResponse)
def delete_avatar(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_config: StorageConfig = Depends(get_storage_config)
):
    """
    プロフィール画像（アバター）削除API

    設定済みのアバターを削除し、未設定状態（イニシャルアバター表示）に戻す。
    """
    if current_user.status == 0:
        raise HTTPException(status_code=403, detail="User account is disabled")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    is_admin = current_user.type == 10
    is_self = current_user.id == user_id
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Insufficient permissions. You can only edit your own profile.")

    old_avatar_path = target_user.avatar_path
    if not old_avatar_path:
        raise HTTPException(status_code=409, detail="Avatar is not set")

    try:
        target_user.avatar_path = None
        db.commit()
        db.refresh(target_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete avatar: {str(e)}")

    _delete_avatar_file(storage_config, old_avatar_path)

    return _to_user_response(target_user)


@router.get("/avatars/{filename}")
def get_avatar_by_filename(
    filename: str,
    signature: Optional[str] = Query(None),
    expires: Optional[str] = Query(None),
    storage_config: StorageConfig = Depends(get_storage_config)
):
    """
    アバター画像配信API（ファイル名指定）

    署名付きURLによる安全なアバター画像配信。
    有効な署名と期限内のリクエストのみアクセス可能。
    """
    sig, exp = get_signature_info(signature, expires)
    if not sig or not exp:
        raise HTTPException(status_code=403, detail="Missing or invalid signature parameters")

    if not verify_url_signature(filename, "avatars", sig, exp):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    avatar_file_path = storage_config.get_avatar_file_path(filename)

    if not avatar_file_path.exists():
        raise HTTPException(status_code=404, detail="Avatar file not found")

    try:
        with open(avatar_file_path, 'rb') as f:
            f.read(1)
    except (OSError, IOError) as e:
        logger.error(f"Failed to read avatar file {avatar_file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read avatar file")

    media_type = mimetypes.guess_type(str(avatar_file_path))[0] or "image/jpeg"

    return FileResponse(
        path=str(avatar_file_path),
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )

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