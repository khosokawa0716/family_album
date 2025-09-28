"""
ファイルストレージ設定モジュール

環境に応じて画像保存先を適切に設定し、必要なディレクトリを自動作成する。
- 開発環境（Mac）: ./storage/photos, ./storage/thumbnails
- 本番環境（Raspberry Pi）: /mnt/photos, /mnt/photos/thumbnails
"""

import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


class StorageConfig:
    """ファイルストレージ設定クラス"""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.photos_path = Path(os.getenv("PHOTOS_STORAGE_PATH", "./storage/photos"))
        self.thumbnails_path = Path(os.getenv("THUMBNAILS_STORAGE_PATH", "./storage/thumbnails"))
        self.auto_create_dirs = os.getenv("AUTO_CREATE_DIRS", "true").lower() == "true"
        self.max_upload_size = int(os.getenv("MAX_UPLOAD_SIZE", "20971520"))  # 20MB
        self.allowed_image_types = self._parse_allowed_types()

        # 初期化時にディレクトリを作成
        if self.auto_create_dirs:
            self._ensure_directories_exist()

    def _parse_allowed_types(self) -> List[str]:
        """許可する画像タイプの解析"""
        types_str = os.getenv("ALLOWED_IMAGE_TYPES", "image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif")
        return [t.strip() for t in types_str.split(",")]

    def _ensure_directories_exist(self):
        """必要なディレクトリが存在することを確認し、なければ作成"""
        directories = [self.photos_path, self.thumbnails_path]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise

    def get_photos_path(self) -> Path:
        """写真保存パスを取得"""
        return self.photos_path

    def get_thumbnails_path(self) -> Path:
        """サムネイル保存パスを取得"""
        return self.thumbnails_path

    def get_photo_file_path(self, filename: str) -> Path:
        """指定ファイル名の写真保存パスを取得"""
        return self.photos_path / filename

    def get_thumbnail_file_path(self, filename: str) -> Path:
        """指定ファイル名のサムネイル保存パスを取得"""
        return self.thumbnails_path / filename

    def is_allowed_image_type(self, mime_type: str) -> bool:
        """許可されている画像タイプかチェック"""
        return mime_type in self.allowed_image_types

    def is_valid_file_size(self, file_size: int) -> bool:
        """ファイルサイズが制限内かチェック"""
        return file_size <= self.max_upload_size

    def get_storage_info(self) -> dict:
        """ストレージ設定情報を辞書で返す"""
        return {
            "environment": self.environment,
            "photos_path": str(self.photos_path),
            "thumbnails_path": str(self.thumbnails_path),
            "max_upload_size": self.max_upload_size,
            "allowed_image_types": self.allowed_image_types,
            "auto_create_dirs": self.auto_create_dirs
        }


# グローバルインスタンス
storage_config = StorageConfig()


def get_storage_config() -> StorageConfig:
    """ストレージ設定インスタンスを取得（dependency injection用）"""
    return storage_config