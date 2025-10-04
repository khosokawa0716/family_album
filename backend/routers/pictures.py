from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, desc
from typing import Optional, Union
from datetime import datetime
from PIL import Image, ExifTags
from pillow_heif import register_heif_opener
import uuid
import os
from pathlib import Path
import logging
from io import BytesIO

from database import get_db
from models import Picture, User, Category
from schemas import PictureListResponse, PictureResponse
from dependencies import get_current_user
from config.storage import get_storage_config, StorageConfig
from utils.url_signature import verify_url_signature, get_signature_info, create_signed_url

router = APIRouter(prefix="/api", tags=["pictures"])
logger = logging.getLogger(__name__)

# HEIC画像サポートを有効化
register_heif_opener()

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
            print("Fetched categories:", category_ids)
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

    # 署名付きURLを生成するため、レスポンス用のデータを作成
    picture_responses = []
    for picture in pictures:
        # ファイル名を取得して署名付きURLを生成
        filename = os.path.basename(picture.file_path)

        # 署名付きURL生成（30分有効）
        thumbnail_url = create_signed_url(f"thumb_{filename}", "thumbnails", expires_in=1800)
        photo_url = create_signed_url(filename, "photos", expires_in=1800)

        # PictureResponseオブジェクトを作成（署名付きURLを設定）
        picture_data = {
            "id": picture.id,
            "family_id": picture.family_id,
            "uploaded_by": picture.uploaded_by,
            "title": picture.title,
            "description": picture.description,
            "file_path": photo_url,  # 署名付きオリジナル画像URL
            "thumbnail_path": thumbnail_url,  # 署名付きサムネイルURL
            "file_size": picture.file_size,
            "mime_type": picture.mime_type,
            "width": picture.width,
            "height": picture.height,
            "taken_date": picture.taken_date,
            "category_id": picture.category_id,
            "status": picture.status,
            "create_date": picture.create_date,
            "update_date": picture.update_date
        }
        picture_responses.append(picture_data)

    # 次ページ存在判定
    has_more = (offset + limit) < total

    return PictureListResponse(
        pictures=picture_responses,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more
    )


@router.get("/pictures/{picture_id}", response_model=PictureResponse)
def get_picture_detail(
    picture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    写真詳細取得API

    指定されたIDの写真詳細情報を取得する。
    家族スコープでのアクセス制御により、自分の家族の写真のみ取得可能。

    Args:
        picture_id: 取得する写真のID
        db: データベースセッション
        current_user: 認証済みユーザー情報

    Returns:
        PictureResponse: 写真詳細情報

    Raises:
        HTTPException:
            - 404: 写真が見つからない、または他家族の写真
            - 404: 削除済み写真(status=0)
    """

    # 家族スコープでの写真取得（削除済みは除外）
    picture = db.query(Picture).filter(
        and_(
            Picture.id == picture_id,
            Picture.family_id == current_user.family_id,
            Picture.status == 1
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Picture not found")

    # 署名付きURLを生成してレスポンスデータを作成
    filename = os.path.basename(picture.file_path)

    # 署名付きURL生成（30分有効）
    thumbnail_url = create_signed_url(f"thumb_{filename}", "thumbnails", expires_in=1800)
    photo_url = create_signed_url(filename, "photos", expires_in=1800)

    # PictureResponseオブジェクトを作成（署名付きURLを設定）
    picture_data = {
        "id": picture.id,
        "family_id": picture.family_id,
        "uploaded_by": picture.uploaded_by,
        "title": picture.title,
        "description": picture.description,
        "file_path": photo_url,  # 署名付きオリジナル画像URL
        "thumbnail_path": thumbnail_url,  # 署名付きサムネイルURL
        "file_size": picture.file_size,
        "mime_type": picture.mime_type,
        "width": picture.width,
        "height": picture.height,
        "taken_date": picture.taken_date,
        "category_id": picture.category_id,
        "status": picture.status,
        "create_date": picture.create_date,
        "update_date": picture.update_date
    }

    return picture_data


@router.post("/pictures", response_model=PictureResponse, status_code=201)
async def upload_picture(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_config: StorageConfig = Depends(get_storage_config)
):
    """
    画像アップロードAPI

    multipart/form-dataで画像ファイルとメタデータを受信し、
    EXIF除去、サムネイル生成、ファイル検証を実行して保存する。

    Args:
        file: アップロードする画像ファイル
        title: 写真のタイトル（任意）
        description: 写真の説明（任意）
        category_id: カテゴリID（任意）
        db: データベースセッション
        current_user: 認証済みユーザー情報
        storage_config: ストレージ設定

    Returns:
        PictureResponse: 保存された写真情報

    Raises:
        HTTPException:
            - 400: ファイル検証エラー、カテゴリエラー等
            - 500: ファイル保存エラー、データベースエラー
    """

    # 1. ファイル基本検証
    # HEIC/HEIFファイルはブラウザでContent-Typeが正しく設定されない場合があるため
    # ファイル拡張子もチェックして補完する
    content_type = file.content_type or ""
    file_extension = Path(file.filename).suffix.lower() if file.filename else ""

    # HEIC/HEIFファイルの場合、Content-Typeを補正
    if file_extension in ['.heic', '.heif'] and not content_type:
        content_type = 'image/heic' if file_extension == '.heic' else 'image/heif'
    elif file_extension in ['.heic', '.heif'] and content_type in ['application/octet-stream', '']:
        content_type = 'image/heic' if file_extension == '.heic' else 'image/heif'

    if not content_type:
        raise HTTPException(status_code=400, detail="File content type is required")

    if not storage_config.is_allowed_image_type(content_type):
        raise HTTPException(
            status_code=400,
            detail=f"File type {content_type} is not allowed. "
                   f"Allowed types: {', '.join(storage_config.allowed_image_types)}"
        )

    # ファイル内容を読み込み
    file_content = await file.read()
    file_size = len(file_content)

    if not storage_config.is_valid_file_size(file_size):
        max_size_mb = storage_config.max_upload_size / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"File size ({file_size} bytes) is too large. "
                   f"Maximum allowed: {max_size_mb:.1f}MB"
        )

    # 2. カテゴリ検証（指定された場合）
    if category_id is not None:
        category = db.query(Category).filter(
            and_(
                Category.id == category_id,
                Category.family_id == current_user.family_id,
                Category.status == 1
            )
        ).first()

        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with ID {category_id} not found or not accessible"
            )

    # 3. 画像検証・メタデータ抽出
    try:
        # PIL で画像を開いて検証
        image = Image.open(BytesIO(file_content))

        # 画像サイズ取得
        width, height = image.size

        # HEIC/HEIF画像の場合はPNG形式に変換
        pil_format = image.format
        if pil_format in ["HEIC", "HEIF"]:
            image = image.convert("RGB")
            pil_format = "PNG"
            detected_mime = "image/png"
        else:
            # MIME型の再確認（PIL の format から）
            if pil_format:
                format_to_mime = {
                    'JPEG': 'image/jpeg',
                    'PNG': 'image/png',
                    'GIF': 'image/gif',
                    'WEBP': 'image/webp'
                }
                detected_mime = format_to_mime.get(pil_format, file.content_type)
            else:
                detected_mime = file.content_type

        # EXIF から撮影日時を抽出
        taken_date = None
        if hasattr(image, '_getexif') and image._getexif():
            exif_data = image._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == "DateTime":
                        try:
                            taken_date = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                            break
                        except ValueError:
                            logger.warning(f"Invalid EXIF DateTime format: {value}")

    except Exception as e:
        logger.error(f"Image validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid image file or unsupported format"
        )

    # 4. ユニークファイル名生成
    file_extension = Path(file.filename).suffix.lower()

    # HEIC画像の場合は強制的にPNG拡張子を使用
    if pil_format == "PNG" and (file_extension == '.heic' or file_extension == '.heif' or detected_mime == 'image/png'):
        file_extension = '.png'
    elif not file_extension:
        # MIME型から拡張子を推定
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp'
        }
        file_extension = mime_to_ext.get(detected_mime, '.jpg')

    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    thumb_filename = f"thumb_{unique_filename}"

    # ファイルパス生成
    photo_path = storage_config.get_photo_file_path(unique_filename)
    thumb_path = storage_config.get_thumbnail_file_path(thumb_filename)

    # 5. ファイル保存処理
    try:
        # EXIF除去処理
        if image.mode in ('RGBA', 'LA', 'P'):
            # アルファチャンネルがある場合は適切に変換
            if detected_mime == 'image/jpeg':
                # JPEGはアルファチャンネルをサポートしないため、白背景で合成
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
                image = background
            else:
                image = image.convert('RGB')

        # オリジナル画像保存（EXIF除去）
        with open(photo_path, 'wb') as f:
            image.save(f, format=pil_format, quality=95 if pil_format == 'JPEG' else None)

        # サムネイル生成・保存
        thumbnail = image.copy()
        thumbnail.thumbnail((300, 300), Image.Resampling.LANCZOS)

        with open(thumb_path, 'wb') as f:
            thumbnail.save(f, format=pil_format, quality=85 if pil_format == 'JPEG' else None)

        logger.info(f"Files saved: {photo_path}, {thumb_path}")

    except Exception as e:
        logger.error(f"File save failed: {e}")
        # 保存済みファイルがあれば削除
        for path in [photo_path, thumb_path]:
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass
        raise HTTPException(status_code=500, detail="Failed to save image files")

    # 6. データベース保存
    try:
        # 相対パスで保存（ストレージルートからの相対パス）
        relative_photo_path = str(Path("photos") / unique_filename)
        relative_thumb_path = str(Path("thumbnails") / thumb_filename)

        picture = Picture(
            family_id=current_user.family_id,
            uploaded_by=current_user.id,
            title=title.strip() if title and title.strip() else None,
            description=description.strip() if description and description.strip() else None,
            file_path=relative_photo_path,
            thumbnail_path=relative_thumb_path,
            file_size=file_size,
            mime_type=detected_mime,
            width=width,
            height=height,
            taken_date=taken_date,
            category_id=category_id,
            status=1
        )

        db.add(picture)
        db.commit()
        db.refresh(picture)

        logger.info(f"Picture saved to database: ID={picture.id}, User={current_user.id}")
        return picture

    except Exception as e:
        logger.error(f"Database save failed: {e}")
        db.rollback()

        # 保存済みファイルを削除
        for path in [photo_path, thumb_path]:
            if path.exists():
                try:
                    path.unlink()
                    logger.info(f"Cleaned up file: {path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup file {path}: {cleanup_error}")

        raise HTTPException(status_code=500, detail="Failed to save picture information")


@router.delete("/pictures/{picture_id}", status_code=204)
def delete_picture(
    picture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    写真削除API（論理削除）

    指定されたIDの写真を論理削除する。
    statusを0に変更し、deleted_atを現在時刻に設定する。
    家族スコープでのアクセス制御により、自分の家族の写真のみ削除可能。

    Args:
        picture_id: 削除する写真のID
        db: データベースセッション
        current_user: 認証済みユーザー情報

    Returns:
        204 No Content: 削除成功

    Raises:
        HTTPException:
            - 404: 写真が見つからない、または他家族の写真
            - 404: 既に削除済み写真(status=0)
            - 500: データベース更新エラー
    """

    # 家族スコープでの写真取得（削除済みは除外）
    picture = db.query(Picture).filter(
        and_(
            Picture.id == picture_id,
            Picture.family_id == current_user.family_id,
            Picture.status == 1
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Picture not found")

    # 論理削除実行
    try:
        picture.status = 0
        picture.deleted_at = datetime.utcnow()
        picture.update_date = datetime.utcnow()

        db.commit()
        logger.info(f"Picture deleted: ID={picture_id}, User={current_user.id}")

    except Exception as e:
        logger.error(f"Failed to delete picture {picture_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete picture")


@router.patch("/pictures/{picture_id}/restore", status_code=200)
def restore_picture(
    picture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    写真復元API

    指定されたIDの写真を復元する。
    statusを1に変更し、deleted_atをNULLに設定する。
    家族スコープでのアクセス制御により、自分の家族の写真のみ復元可能。

    Args:
        picture_id: 復元する写真のID
        db: データベースセッション
        current_user: 認証済みユーザー情報

    Returns:
        200 OK: 復元成功メッセージ

    Raises:
        HTTPException:
            - 404: 写真が見つからない、または他家族の写真
            - 400: 既に有効な写真(status=1)
            - 500: データベース更新エラー
    """

    # 家族スコープでの写真取得（削除済みの写真のみ対象）
    picture = db.query(Picture).filter(
        and_(
            Picture.id == picture_id,
            Picture.family_id == current_user.family_id,
            Picture.status == 0
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Picture not found or already restored")

    # 復元処理実行
    try:
        picture.status = 1
        picture.deleted_at = None
        picture.update_date = datetime.utcnow()

        db.commit()
        logger.info(f"Picture restored: ID={picture_id}, User={current_user.id}")

        return {"message": "Picture restored successfully"}

    except Exception as e:
        logger.error(f"Failed to restore picture {picture_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to restore picture")


@router.get("/pictures/{picture_id}/download")
def download_picture(
    picture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_config: StorageConfig = Depends(get_storage_config)
):
    """
    写真原本ダウンロードAPI

    指定されたIDの写真の原本ファイルをダウンロードする。
    適切なContent-TypeとContent-Dispositionヘッダーを設定してファイルを返却する。
    家族スコープでのアクセス制御により、自分の家族の写真のみダウンロード可能。

    Args:
        picture_id: ダウンロードする写真のID
        db: データベースセッション
        current_user: 認証済みユーザー情報
        storage_config: ストレージ設定

    Returns:
        FileResponse: 写真ファイル

    Raises:
        HTTPException:
            - 404: 写真が見つからない、または他家族の写真
            - 404: 削除済み写真(status=0)
            - 404: ファイルが物理的に存在しない
            - 500: ファイル読み込みエラー
    """

    # 家族スコープでの写真取得（削除済みは除外）
    picture = db.query(Picture).filter(
        and_(
            Picture.id == picture_id,
            Picture.family_id == current_user.family_id,
            Picture.status == 1
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Picture not found")

    # ファイルパス取得（絶対パス）
    file_path = storage_config.get_photo_file_path(os.path.basename(picture.file_path))

    # ファイル存在確認
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    # ファイル読み込み可能性確認
    try:
        # ファイルサイズ確認とアクセステスト
        file_stat = file_path.stat()
        file_size = file_stat.st_size

        # ファイルが読み込み可能かテスト
        with open(file_path, 'rb') as f:
            f.read(1)  # 1バイト読み込みテスト

    except (OSError, IOError) as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file")

    # ファイル名の準備（安全性のため、元のファイル名を使用）
    safe_filename = os.path.basename(picture.file_path) or f"picture_{picture_id}.jpg"

    try:
        # FileResponseを返す
        return FileResponse(
            path=str(file_path),
            media_type=picture.mime_type,
            filename=safe_filename,
            headers={
                "Content-Length": str(file_size),
                "Cache-Control": "private, max-age=3600"  # 1時間キャッシュ
            }
        )

    except Exception as e:
        logger.error(f"Failed to create file response for {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve file")


@router.get("/thumbnails/{filename}")
def get_thumbnail_by_filename(
    filename: str,
    signature: Optional[str] = Query(None),
    expires: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    storage_config: StorageConfig = Depends(get_storage_config)
):
    """
    サムネイル画像配信API（ファイル名指定）

    署名付きURLによる安全なサムネイル画像配信。
    有効な署名と期限内のリクエストのみアクセス可能。

    Args:
        filename: サムネイルファイル名
        signature: URL署名（HMAC-SHA256）
        expires: 有効期限（UNIX時間）
        db: データベースセッション
        storage_config: ストレージ設定

    Returns:
        FileResponse: サムネイル画像ファイル

    Raises:
        HTTPException:
            - 403: 署名が無効または期限切れ
            - 404: ファイルが見つからない
            - 404: ファイルが物理的に存在しない
            - 500: ファイル読み込みエラー
    """

    # 署名検証
    sig, exp = get_signature_info(signature, expires)
    if not sig or not exp:
        raise HTTPException(status_code=403, detail="Missing or invalid signature parameters")

    if not verify_url_signature(filename, "thumbnails", sig, exp):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    # サムネイルファイル名から元の写真ファイル名を推定
    # サムネイルは通常 "thumb_original_filename.ext" の形式
    original_filename = filename
    if filename.startswith("thumb_"):
        original_filename = filename[6:]  # "thumb_" を除去

    # 写真の存在確認（削除済みは除外）
    picture = db.query(Picture).filter(
        and_(
            Picture.file_path.endswith(original_filename),
            Picture.status == 1
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    # サムネイルファイルパス取得
    thumbnail_path = storage_config.get_thumbnail_file_path(filename)

    # ファイル存在確認
    if not thumbnail_path.exists():
        logger.error(f"Thumbnail file not found: {thumbnail_path}")
        raise HTTPException(status_code=404, detail="Thumbnail file not found")

    # ファイル読み込み可能性確認
    try:
        file_stat = thumbnail_path.stat()
        file_size = file_stat.st_size

        # ファイルが読み込み可能かテスト
        with open(thumbnail_path, 'rb') as f:
            f.read(1)  # 1バイト読み込みテスト

    except (OSError, IOError) as e:
        logger.error(f"Failed to read thumbnail file {thumbnail_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read thumbnail file")

    try:
        # FileResponseを返す（サムネイル用の適切なヘッダー設定）
        return FileResponse(
            path=str(thumbnail_path),
            media_type=picture.mime_type,
            headers={
                "Content-Length": str(file_size),
                "Cache-Control": "public, max-age=86400"  # 24時間キャッシュ（サムネイルは長期キャッシュ）
            }
        )

    except Exception as e:
        logger.error(f"Failed to create file response for thumbnail {thumbnail_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve thumbnail file")


@router.get("/photos/{filename}")
def get_photo_by_filename(
    filename: str,
    signature: Optional[str] = Query(None),
    expires: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    storage_config: StorageConfig = Depends(get_storage_config)
):
    """
    オリジナル画像配信API（ファイル名指定）

    署名付きURLによる安全なオリジナル画像配信。
    有効な署名と期限内のリクエストのみアクセス可能。

    Args:
        filename: 画像ファイル名
        signature: URL署名（HMAC-SHA256）
        expires: 有効期限（UNIX時間）
        db: データベースセッション
        storage_config: ストレージ設定

    Returns:
        FileResponse: オリジナル画像ファイル

    Raises:
        HTTPException:
            - 403: 署名が無効または期限切れ
            - 404: ファイルが見つからない
            - 404: ファイルが物理的に存在しない
            - 500: ファイル読み込みエラー
    """

    # 署名検証
    sig, exp = get_signature_info(signature, expires)
    if not sig or not exp:
        raise HTTPException(status_code=403, detail="Missing or invalid signature parameters")

    if not verify_url_signature(filename, "photos", sig, exp):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    # 写真の存在確認（削除済みは除外）
    picture = db.query(Picture).filter(
        and_(
            Picture.file_path.endswith(filename),
            Picture.status == 1
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Photo not found")

    # ファイルパス取得（絶対パス）
    file_path = storage_config.get_photo_file_path(filename)

    # ファイル存在確認
    if not file_path.exists():
        logger.error(f"Photo file not found: {file_path}")
        raise HTTPException(status_code=404, detail="Photo file not found")

    # ファイル読み込み可能性確認
    try:
        file_stat = file_path.stat()
        file_size = file_stat.st_size

        # ファイルが読み込み可能かテスト
        with open(file_path, 'rb') as f:
            f.read(1)  # 1バイト読み込みテスト

    except (OSError, IOError) as e:
        logger.error(f"Failed to read photo file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read photo file")

    # ファイル名の準備（安全性のため、元のファイル名を使用）
    safe_filename = os.path.basename(picture.file_path) or filename

    try:
        # FileResponseを返す
        return FileResponse(
            path=str(file_path),
            media_type=picture.mime_type,
            filename=safe_filename,
            headers={
                "Content-Length": str(file_size),
                "Cache-Control": "private, max-age=3600"  # 1時間キャッシュ
            }
        )

    except Exception as e:
        logger.error(f"Failed to create file response for photo {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve photo file")


