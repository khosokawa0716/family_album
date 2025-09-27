"""
GET /api/thumbnails/{filename} および GET /api/photos/{filename} APIのテストファイル

ファイル名指定画像配信API仕様:
- 認証済みユーザーが自分の家族の有効な写真ファイルにアクセス
- サムネイルとオリジナル画像の直接配信
- 適切なContent-TypeとCache-Controlヘッダーを設定
- 家族スコープでのアクセス制御
- 削除済み写真はアクセス不可

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 他ファミリーの写真へのアクセス拒否
   - 存在しないユーザーでのアクセス拒否

2. ファイルアクセステスト
   - 自分の家族の有効写真のアクセス成功
   - 他の家族の写真アクセス試行の拒否（404）
   - 存在しないファイル名での404エラー
   - 削除済み写真へのアクセス拒否

3. ファイル名マッチングテスト
   - 正確なファイル名でのマッチング
   - サムネイルファイル名（thumb_プレフィックス）のマッチング
   - 大文字小文字の区別

4. レスポンステスト
   - 適切なContent-Typeヘッダーの設定
   - 適切なCache-Controlヘッダーの設定
   - ファイルサイズの正確性
   - ファイル内容の正確性

5. セキュリティテスト
   - パストラバーサル攻撃への耐性
   - ファイルアクセス制御の確認
   - 不正なファイル拡張子での攻撃防止
"""

from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime, timezone
import tempfile
import os
from pathlib import Path

from main import app
from models import User, Picture
from database import get_db
from dependencies import get_current_user
from config.storage import get_storage_config


class TestPicturesFilenameEndpoints:
    """GET /api/thumbnails/{filename} と GET /api/photos/{filename} APIのテストクラス"""

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

        # 有効な写真（アクセス対象）
        self.active_picture = MagicMock(spec=Picture)
        self.active_picture.id = 1
        self.active_picture.family_id = self.test_user.family_id
        self.active_picture.title = "Test Picture"
        self.active_picture.file_path = "/storage/test-family/picture1.jpg"
        # file_nameフィールドは存在しないため削除
        self.active_picture.mime_type = "image/jpeg"
        self.active_picture.file_size = 1024000
        self.active_picture.status = 1  # 有効
        self.active_picture.uploaded_by = self.test_user.id
        self.active_picture.create_date = datetime.now(timezone.utc)
        self.active_picture.update_date = datetime.now(timezone.utc)
        self.active_picture.deleted_at = None

        # PNG画像
        self.png_picture = MagicMock(spec=Picture)
        self.png_picture.id = 2
        self.png_picture.family_id = self.test_user.family_id
        self.png_picture.title = "PNG Picture"
        self.png_picture.file_path = "/storage/test-family/image.png"
        # file_nameフィールドは存在しないため削除
        self.png_picture.mime_type = "image/png"
        self.png_picture.file_size = 512000
        self.png_picture.status = 1
        self.png_picture.uploaded_by = self.test_user.id
        self.png_picture.create_date = datetime.now(timezone.utc)
        self.png_picture.update_date = datetime.now(timezone.utc)
        self.png_picture.deleted_at = None

        # 削除済み写真（アクセス不可）
        self.deleted_picture = MagicMock(spec=Picture)
        self.deleted_picture.id = 3
        self.deleted_picture.family_id = self.test_user.family_id
        self.deleted_picture.title = "Deleted Picture"
        self.deleted_picture.file_path = "/storage/test-family/deleted.jpg"
        # file_nameフィールドは存在しないため削除
        self.deleted_picture.mime_type = "image/jpeg"
        self.deleted_picture.file_size = 256000
        self.deleted_picture.status = 0  # 削除済み
        self.deleted_picture.uploaded_by = self.test_user.id
        self.deleted_picture.create_date = datetime.now(timezone.utc)
        self.deleted_picture.update_date = datetime.now(timezone.utc)
        self.deleted_picture.deleted_at = datetime.now(timezone.utc)

        # 他の家族の写真
        self.other_family_picture = MagicMock(spec=Picture)
        self.other_family_picture.id = 4
        self.other_family_picture.family_id = 999  # 異なる家族ID
        self.other_family_picture.title = "Other Family Picture"
        self.other_family_picture.file_path = "/storage/other-family/other.jpg"
        # file_nameフィールドは存在しないため削除
        self.other_family_picture.mime_type = "image/jpeg"
        self.other_family_picture.file_size = 2048000
        self.other_family_picture.status = 1
        self.other_family_picture.uploaded_by = 999
        self.other_family_picture.create_date = datetime.now(timezone.utc)
        self.other_family_picture.update_date = datetime.now(timezone.utc)
        self.other_family_picture.deleted_at = None

        # テスト用ファイル内容
        self.test_file_content = b"fake image content for testing"
        self.test_thumbnail_content = b"fake thumbnail content for testing"

    def teardown_method(self):
        """各テストメソッド実行後のクリーンアップ"""
        app.dependency_overrides.clear()

    # ========================================
    # サムネイル配信エンドポイント (/api/thumbnails/{filename})
    # ========================================

    def test_get_thumbnail_success(self):
        """サムネイル配信成功: 有効なサムネイルファイルの正常配信"""
        # 一時ファイルを作成（サムネイル用）
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(self.test_thumbnail_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_thumbnail_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"/api/thumbnails/thumb_picture1.jpg")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "image/jpeg"
            assert len(response.content) == len(self.test_thumbnail_content)
            # サムネイルは長期キャッシュ
            assert "Cache-Control" in response.headers
            assert "public" in response.headers["Cache-Control"]
            assert "max-age=86400" in response.headers["Cache-Control"]

        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_get_thumbnail_thumb_prefix_handling(self):
        """サムネイル配信: thumb_プレフィックスの適切な処理"""
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
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            # thumb_プレフィックス付きでアクセス
            response = self.client.get(f"/api/thumbnails/thumb_picture1.jpg")
            assert response.status_code == status.HTTP_200_OK

            # プレフィックスなしでもアクセス可能であることを確認
            response2 = self.client.get(f"/api/thumbnails/picture1.jpg")
            assert response2.status_code == status.HTTP_200_OK

        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_get_thumbnail_without_auth(self):
        """サムネイル配信: 未認証でのアクセス拒否"""
        response = self.client.get(f"/api/thumbnails/picture1.jpg")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_thumbnail_other_family(self):
        """サムネイル配信: 他ファミリーの写真へのアクセス拒否"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.get(f"/api/thumbnails/other.jpg")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Thumbnail not found"

    def test_get_thumbnail_deleted_picture(self):
        """サムネイル配信: 削除済み写真のサムネイルアクセス拒否"""
        mock_db = Mock()
        # 削除済み写真はstatus=1フィルターで除外されるためNoneが返される
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.get(f"/api/thumbnails/deleted.jpg")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Thumbnail not found"

    def test_get_thumbnail_file_not_exists(self):
        """サムネイル配信: 物理サムネイルファイルが存在しない場合"""
        mock_storage_config = Mock()
        mock_file_path = Mock()
        mock_file_path.exists.return_value = False  # ファイルが存在しない
        mock_storage_config.get_thumbnail_file_path.return_value = mock_file_path

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

        response = self.client.get(f"/api/thumbnails/picture1.jpg")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Thumbnail file not found"

    def test_get_thumbnail_read_error(self):
        """サムネイル配信: ファイル読み込みエラー処理"""
        mock_storage_config = Mock()
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.stat.side_effect = IOError("Cannot access file")
        mock_storage_config.get_thumbnail_file_path.return_value = mock_file_path

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

        response = self.client.get(f"/api/thumbnails/picture1.jpg")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to read thumbnail file"

    # ========================================
    # オリジナル画像配信エンドポイント (/api/photos/{filename})
    # ========================================

    def test_get_photo_success(self):
        """オリジナル画像配信成功: 有効な写真ファイルの正常配信"""
        # 一時ファイルを作成（オリジナル用）
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(self.test_file_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"/api/photos/picture1.jpg")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "image/jpeg"
            assert len(response.content) == len(self.test_file_content)
            # オリジナル画像はプライベートキャッシュ
            assert "Cache-Control" in response.headers
            assert "private" in response.headers["Cache-Control"]
            assert "max-age=3600" in response.headers["Cache-Control"]
            # ダウンロード用ファイル名設定
            assert "content-disposition" in response.headers

        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_get_photo_png_format(self):
        """オリジナル画像配信: PNG形式での適切な配信"""
        # 一時ファイルを作成（PNG用）
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(b"png image content")
            temp_file_path = temp_file.name

        try:
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.png_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"/api/photos/image.png")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "image/png"

        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_get_photo_without_auth(self):
        """オリジナル画像配信: 未認証でのアクセス拒否"""
        response = self.client.get(f"/api/photos/picture1.jpg")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_photo_other_family(self):
        """オリジナル画像配信: 他ファミリーの写真へのアクセス拒否"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.get(f"/api/photos/other.jpg")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Photo not found"

    def test_get_photo_deleted_picture(self):
        """オリジナル画像配信: 削除済み写真へのアクセス拒否"""
        mock_db = Mock()
        # 削除済み写真はstatus=1フィルターで除外されるためNoneが返される
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.get(f"/api/photos/deleted.jpg")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Photo not found"

    def test_get_photo_file_not_exists(self):
        """オリジナル画像配信: 物理ファイルが存在しない場合"""
        mock_storage_config = Mock()
        mock_file_path = Mock()
        mock_file_path.exists.return_value = False  # ファイルが存在しない
        mock_storage_config.get_photo_file_path.return_value = mock_file_path

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

        response = self.client.get(f"/api/photos/picture1.jpg")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Photo file not found"

    def test_get_photo_read_error(self):
        """オリジナル画像配信: ファイル読み込みエラー処理"""
        mock_storage_config = Mock()
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.stat.side_effect = IOError("Cannot access file")
        mock_storage_config.get_photo_file_path.return_value = mock_file_path

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

        response = self.client.get(f"/api/photos/picture1.jpg")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to read photo file"

    # ========================================
    # セキュリティテスト
    # ========================================

    def test_path_traversal_protection_thumbnails(self):
        """セキュリティ: サムネイルエンドポイントでのパストラバーサル攻撃への耐性"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]

        for filename in malicious_filenames:
            response = self.client.get(f"/api/thumbnails/{filename}")
            # パストラバーサル攻撃は失敗すべき
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_path_traversal_protection_photos(self):
        """セキュリティ: オリジナル画像エンドポイントでのパストラバーサル攻撃への耐性"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]

        for filename in malicious_filenames:
            response = self.client.get(f"/api/photos/{filename}")
            # パストラバーサル攻撃は失敗すべき
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_family_scope_access_control(self):
        """セキュリティ: 家族スコープでのアクセス制御確認"""
        # 同一ファミリーの別ユーザー
        family_user = MagicMock(spec=User)
        family_user.id = 2
        family_user.family_id = self.test_user.family_id  # 同じファミリー
        family_user.status = 1

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(self.test_file_content)
            temp_file_path = temp_file.name

        try:
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)
            mock_storage_config.get_thumbnail_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: family_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            # 同一ファミリーならアクセス可能
            response1 = self.client.get(f"/api/photos/picture1.jpg")
            assert response1.status_code == status.HTTP_200_OK

            response2 = self.client.get(f"/api/thumbnails/picture1.jpg")
            assert response2.status_code == status.HTTP_200_OK

        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_filename_case_sensitivity(self):
        """ファイル名マッチング: 大文字小文字の区別"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        # 大文字小文字が異なるファイル名ではマッチしない
        response1 = self.client.get(f"/api/photos/PICTURE1.JPG")
        assert response1.status_code == status.HTTP_404_NOT_FOUND

        response2 = self.client.get(f"/api/thumbnails/PICTURE1.JPG")
        assert response2.status_code == status.HTTP_404_NOT_FOUND

    def test_method_not_allowed(self):
        """HTTPメソッド: GETメソッド以外は許可されない"""
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        # POST, PUT, DELETE等は許可されない
        post_response1 = self.client.post(f"/api/photos/picture1.jpg")
        assert post_response1.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        post_response2 = self.client.post(f"/api/thumbnails/picture1.jpg")
        assert post_response2.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        put_response1 = self.client.put(f"/api/photos/picture1.jpg")
        assert put_response1.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        put_response2 = self.client.put(f"/api/thumbnails/picture1.jpg")
        assert put_response2.status_code == status.HTTP_405_METHOD_NOT_ALLOWED