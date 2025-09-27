"""
GET /api/thumbnails/{filename} および GET /api/photos/{filename} APIの署名付きURLテスト

署名付きURL実装での画像配信API仕様:
- 署名付きURLを使用した認証不要の画像アクセス
- HMAC-SHA256署名による改ざん防止
- 30分間の有効期限
- ファミリースコープでのアクセス制御
- 削除済み写真はアクセス不可

テスト観点:
1. 署名検証テスト
   - 有効な署名でのアクセス成功
   - 無効な署名でのアクセス拒否
   - 期限切れ署名でのアクセス拒否
   - 署名なしでのアクセス拒否

2. ファイルアクセステスト
   - 存在する写真へのアクセス成功
   - 存在しないファイル名での404エラー
   - 削除済み写真へのアクセス拒否

3. セキュリティテスト
   - パストラバーサル攻撃への耐性
   - 署名改ざん攻撃への耐性
"""

from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import tempfile
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from main import app
from models import User, Picture
from database import get_db
from config.storage import get_storage_config
from utils.url_signature import create_signed_url, verify_url_signature


class TestSignedUrlEndpoints:
    """署名付きURL画像配信APIのテストクラス"""

    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.client = TestClient(app)

        # テスト用ユーザーの設定
        self.test_user = MagicMock(spec=User)
        self.test_user.id = 1
        self.test_user.family_id = 1
        self.test_user.user_name = "testuser"
        self.test_user.email = "test@example.com"
        self.test_user.status = 1

        # 有効な写真
        self.active_picture = MagicMock(spec=Picture)
        self.active_picture.id = 1
        self.active_picture.family_id = self.test_user.family_id
        self.active_picture.title = "Test Picture"
        self.active_picture.file_path = "/storage/test-family/picture1.jpg"
        self.active_picture.mime_type = "image/jpeg"
        self.active_picture.file_size = 1024000
        self.active_picture.status = 1
        self.active_picture.uploaded_by = self.test_user.id
        self.active_picture.create_date = datetime.now(timezone.utc)
        self.active_picture.update_date = datetime.now(timezone.utc)
        self.active_picture.deleted_at = None

        # 削除済み写真
        self.deleted_picture = MagicMock(spec=Picture)
        self.deleted_picture.id = 2
        self.deleted_picture.family_id = self.test_user.family_id
        self.deleted_picture.title = "Deleted Picture"
        self.deleted_picture.file_path = "/storage/test-family/deleted_picture.jpg"
        self.deleted_picture.mime_type = "image/jpeg"
        self.deleted_picture.file_size = 512000
        self.deleted_picture.status = 0  # 削除済み
        self.deleted_picture.uploaded_by = self.test_user.id
        self.deleted_picture.create_date = datetime.now(timezone.utc)
        self.deleted_picture.update_date = datetime.now(timezone.utc)
        self.deleted_picture.deleted_at = datetime.now(timezone.utc)

        # テスト用ファイル内容
        self.test_thumbnail_content = b"fake thumbnail image data"
        self.test_photo_content = b"fake photo image data"

    def teardown_method(self):
        """各テストメソッド実行後のクリーンアップ"""
        # dependency_overridesをクリア
        app.dependency_overrides.clear()

    def test_get_thumbnail_with_valid_signature(self):
        """署名付きサムネイル取得: 有効な署名でのアクセス成功"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(self.test_thumbnail_content)
            temp_file_path = temp_file.name

        try:
            mock_storage_config = Mock()
            mock_storage_config.get_thumbnail_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            # 署名付きURLを生成
            signed_url = create_signed_url("thumb_picture1.jpg", "thumbnails")
            parsed_url = urlparse(signed_url)
            query_params = parse_qs(parsed_url.query)

            response = self.client.get(
                f"/api/thumbnails/thumb_picture1.jpg",
                params={
                    "signature": query_params["signature"][0],
                    "expires": query_params["expires"][0]
                }
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.content == self.test_thumbnail_content
            assert response.headers["content-type"] == "image/jpeg"
            assert "max-age=86400" in response.headers["cache-control"]

        finally:
            os.unlink(temp_file_path)

    def test_get_photo_with_valid_signature(self):
        """署名付き写真取得: 有効な署名でのアクセス成功"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(self.test_photo_content)
            temp_file_path = temp_file.name

        try:
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            # 署名付きURLを生成
            signed_url = create_signed_url("picture1.jpg", "photos")
            parsed_url = urlparse(signed_url)
            query_params = parse_qs(parsed_url.query)

            response = self.client.get(
                f"/api/photos/picture1.jpg",
                params={
                    "signature": query_params["signature"][0],
                    "expires": query_params["expires"][0]
                }
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.content == self.test_photo_content
            assert response.headers["content-type"] == "image/jpeg"
            assert "max-age=3600" in response.headers["cache-control"]

        finally:
            os.unlink(temp_file_path)

    def test_get_thumbnail_without_signature(self):
        """署名なしでのサムネイルアクセス: 403エラー"""
        response = self.client.get("/api/thumbnails/thumb_picture1.jpg")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_photo_without_signature(self):
        """署名なしでの写真アクセス: 403エラー"""
        response = self.client.get("/api/photos/picture1.jpg")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_thumbnail_with_invalid_signature(self):
        """無効な署名でのサムネイルアクセス: 403エラー"""
        current_time = int(time.time())
        response = self.client.get(
            "/api/thumbnails/thumb_picture1.jpg",
            params={
                "signature": "invalid_signature",
                "expires": str(current_time + 1800)
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_photo_with_invalid_signature(self):
        """無効な署名での写真アクセス: 403エラー"""
        current_time = int(time.time())
        response = self.client.get(
            "/api/photos/picture1.jpg",
            params={
                "signature": "invalid_signature",
                "expires": str(current_time + 1800)
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_thumbnail_with_expired_signature(self):
        """期限切れ署名でのサムネイルアクセス: 403エラー"""
        # 過去の時刻で署名を生成
        expired_time = int(time.time()) - 3600  # 1時間前
        signed_url = create_signed_url("thumb_picture1.jpg", "thumbnails", -3600)
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/thumbnails/thumb_picture1.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_photo_with_expired_signature(self):
        """期限切れ署名での写真アクセス: 403エラー"""
        # 過去の時刻で署名を生成
        signed_url = create_signed_url("picture1.jpg", "photos", -3600)
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/photos/picture1.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_thumbnail_deleted_picture(self):
        """削除済み写真のサムネイルアクセス: 404エラー"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture

        app.dependency_overrides[get_db] = lambda: mock_db

        signed_url = create_signed_url("thumb_deleted_picture.jpg", "thumbnails")
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/thumbnails/thumb_deleted_picture.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_photo_deleted_picture(self):
        """削除済み写真のアクセス: 404エラー"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture

        app.dependency_overrides[get_db] = lambda: mock_db

        signed_url = create_signed_url("deleted_picture.jpg", "photos")
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/photos/deleted_picture.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_thumbnail_nonexistent_picture(self):
        """存在しない写真のサムネイルアクセス: 404エラー"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db

        signed_url = create_signed_url("thumb_nonexistent.jpg", "thumbnails")
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/thumbnails/thumb_nonexistent.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_photo_nonexistent_picture(self):
        """存在しない写真のアクセス: 404エラー"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db

        signed_url = create_signed_url("nonexistent.jpg", "photos")
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/photos/nonexistent.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_path_traversal_protection_thumbnails(self):
        """パストラバーサル攻撃への耐性: サムネイル"""
        signed_url = create_signed_url("../../../etc/passwd", "thumbnails")
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/thumbnails/../../../etc/passwd",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_path_traversal_protection_photos(self):
        """パストラバーサル攻撃への耐性: 写真"""
        signed_url = create_signed_url("../../../etc/passwd", "photos")
        parsed_url = urlparse(signed_url)
        query_params = parse_qs(parsed_url.query)

        response = self.client.get(
            "/api/photos/../../../etc/passwd",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND