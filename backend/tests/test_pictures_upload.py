"""
POST /api/pictures APIのテストファイル（画像アップロード）

画像アップロードAPI仕様:
- 認証済みユーザーが自分の家族に画像をアップロード（1〜5枚同時）
- multipart/form-dataでファイル + メタデータを送信
- 同時投稿された写真は同じgroup_idでグループ化
- EXIF除去、サムネイル生成、ファイル検証を実行
- 家族スコープでのアクセス制御
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, mock_open, PropertyMock
from datetime import datetime, timedelta
from jose import jwt
from io import BytesIO
from PIL import Image
import uuid as uuid_module
import os

from main import app
from models import User, Picture, Category
from config import SECRET_KEY, ALGORITHM

client = TestClient(app)


class TestPicturesUploadAPI:
    """POST /api/pictures APIのテストクラス"""

    def create_test_token(self, user_id: int, family_id: int, user_type: int = 0,
                         status: int = 1, exp_minutes: int = 30):
        """テスト用JWTトークン作成"""
        payload = {
            "sub": str(user_id),
            "family_id": family_id,
            "user_type": user_type,
            "status": status,
            "exp": datetime.utcnow() + timedelta(minutes=exp_minutes)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def create_test_image(self, format="JPEG", size=(800, 600), color="RGB"):
        """テスト用画像作成"""
        image = Image.new(color, size, color=(255, 0, 0))
        image_bytes = BytesIO()
        image.save(image_bytes, format=format)
        image_bytes.seek(0)
        return image_bytes

    def create_test_files(self, count=1, format="JPEG", size=(800, 600)):
        """テスト用ファイルリスト作成（複数枚対応）"""
        files = []
        for i in range(count):
            img = self.create_test_image(format=format, size=size)
            ext = "jpg" if format == "JPEG" else format.lower()
            mime = f"image/{format.lower()}" if format != "JPEG" else "image/jpeg"
            files.append(("files", (f"test_{i}.{ext}", img, mime)))
        return files

    def setup_mock_db_for_upload(self, mock_category=None, save_success=True):
        """画像アップロード用のDBモック設定"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # カテゴリ検索のモック
        if mock_category:
            mock_query.first.return_value = mock_category
        else:
            mock_query.first.return_value = None

        # データベース保存のモック
        if save_success:
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()

            # refresh時にPictureオブジェクトに必要なフィールドを設定
            refresh_counter = [0]
            def mock_refresh(picture_obj):
                refresh_counter[0] += 1
                picture_obj.id = refresh_counter[0]
                picture_obj.create_date = datetime(2024, 1, 15, 12, 0, 0)
                picture_obj.update_date = datetime(2024, 1, 15, 12, 0, 0)
                return picture_obj

            mock_db.refresh = MagicMock(side_effect=mock_refresh)
        else:
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock(side_effect=Exception("Database error"))
            mock_db.rollback = MagicMock()

        return mock_db

    def setup_dependency_overrides(self, mock_db, mock_user, mock_storage_config=None):
        """依存注入のオーバーライド設定"""
        from database import get_db
        from dependencies import get_current_user
        from config.storage import get_storage_config

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

        if mock_storage_config:
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

    def teardown_dependency_overrides(self):
        """依存注入のオーバーライドクリーンアップ"""
        app.dependency_overrides.clear()

    def create_mock_user(self, user_id: int = 1, family_id: int = 1, user_type: int = 0, status: int = 1):
        """モックユーザー作成"""
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.family_id = family_id
        mock_user.user_name = f"test_user_{user_id}"
        mock_user.type = user_type
        mock_user.status = status
        return mock_user

    def create_mock_category(self, category_id: int = 1, family_id: int = 1):
        """モックカテゴリ作成"""
        mock_category = MagicMock(spec=Category)
        mock_category.id = category_id
        mock_category.family_id = family_id
        mock_category.name = "Test Category"
        mock_category.status = 1
        return mock_category

    def create_mock_storage_config(self):
        """モックストレージ設定作成"""
        mock_config = MagicMock()
        mock_config.get_photos_path.return_value = "/test/photos"
        mock_config.get_thumbnails_path.return_value = "/test/thumbnails"
        mock_config.is_allowed_image_type.return_value = True
        mock_config.is_valid_file_size.return_value = True
        mock_config.max_upload_size = 20971520  # 20MB
        mock_config.allowed_image_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/heic", "image/heif"]
        return mock_config

    def create_mock_pil_image(self, size=(800, 600), format="JPEG", mode="RGB", exif_data=None):
        """PILモック画像を作成（exif_transpose対応）"""
        mock_img = MagicMock()
        mock_img.size = size
        mock_img.format = format
        mock_img.mode = mode
        mock_img.copy.return_value = mock_img
        mock_img.thumbnail = MagicMock()
        mock_img.save = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img.split.return_value = [MagicMock()] * 4

        if exif_data:
            mock_img._getexif = MagicMock(return_value=exif_data)
        else:
            mock_img._getexif = MagicMock(return_value=None)

        return mock_img

    def patch_image_processing(self, mock_img):
        """画像処理関連のパッチをまとめて適用するコンテキストマネージャを返す"""
        from contextlib import contextmanager

        @contextmanager
        def _patch():
            with patch('routers.pictures.Image.open', return_value=mock_img) as mock_open, \
                 patch('routers.pictures.ImageOps.exif_transpose', return_value=mock_img) as mock_transpose:
                yield mock_open, mock_transpose

        return _patch()

    def get_response_picture(self, response_data, index=0):
        """レスポンスからPictureデータを取得（新形式対応）"""
        assert "group_id" in response_data
        assert "pictures" in response_data
        return response_data["pictures"][index]

    # ========== 認証・認可系テスト ==========

    def test_upload_picture_without_token(self):
        """未認証でアクセス → 403エラー"""
        test_image = self.create_test_image()
        files = [("files", ("test.jpg", test_image, "image/jpeg"))]

        response = client.post("/api/pictures", files=files)
        assert response.status_code == 403
        assert "Not authenticated" in response.json()["detail"]

    def test_upload_picture_with_invalid_token(self):
        """無効トークンでアクセス → 401エラー"""
        test_image = self.create_test_image()
        files = [("files", ("test.jpg", test_image, "image/jpeg"))]
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.post("/api/pictures", files=files, headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_upload_picture_with_deleted_user(self):
        """削除済みユーザーでアクセス → 401エラー"""
        test_image = self.create_test_image()
        files = [("files", ("test.jpg", test_image, "image/jpeg"))]

        token = self.create_test_token(1, 1, status=0)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/pictures", files=files, headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    # ========== 基本アップロード系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_success(self, mock_uuid, mock_file_open):
        """正常な画像アップロード（1枚）"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert "group_id" in data
            assert "pictures" in data
            assert len(data["pictures"]) == 1

            picture = data["pictures"][0]
            assert picture["family_id"] == 1
            assert picture["uploaded_by"] == 1
            assert picture["group_id"] == data["group_id"]

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_without_file(self):
        """ファイルなし → 422エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", headers=headers)

            assert response.status_code == 422  # FastAPIのバリデーションエラー

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_response_structure(self, mock_uuid, mock_file_open):
        """レスポンス構造の検証"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()

            # トップレベルのレスポンス構造
            assert "group_id" in data
            assert "pictures" in data
            assert isinstance(data["pictures"], list)

            # 各写真の必須フィールドの存在確認
            picture = data["pictures"][0]
            required_fields = [
                "id", "family_id", "uploaded_by", "group_id", "file_path",
                "thumbnail_path", "file_size", "mime_type",
                "width", "height", "status", "create_date", "update_date"
            ]

            for field in required_fields:
                assert field in picture, f"Required field '{field}' is missing"

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_with_metadata(self, mock_uuid, mock_file_open):
        """メタデータ付きアップロード"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_category = self.create_mock_category()
            mock_db = self.setup_mock_db_for_upload(mock_category)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            form_data = {
                "title": "Test Title",
                "description": "Test Description",
                "category_id": "1"
            }

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, data=form_data, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["title"] == "Test Title"
            assert picture["description"] == "Test Description"
            assert picture["category_id"] == 1

        finally:
            self.teardown_dependency_overrides()

    # ========== ファイル検証系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_jpeg_format(self, mock_uuid, mock_file_open):
        """JPEG画像の正常アップロード"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1, format="JPEG")
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image(format="JPEG")
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["mime_type"] == "image/jpeg"

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_png_format(self, mock_uuid, mock_file_open):
        """PNG画像の正常アップロード"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = [("files", ("test.png", self.create_test_image(format="PNG"), "image/png"))]
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image(format="PNG")
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["mime_type"] == "image/png"

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_invalid_format(self):
        """無効形式ファイル → 400エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()
            mock_storage.is_allowed_image_type.return_value = False

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_content = b"fake pdf content"
            files = [("files", ("test.pdf", BytesIO(test_content), "application/pdf"))]

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 400
            assert "not allowed" in response.json()["detail"].lower()

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_oversized_file(self):
        """ファイルサイズ超過 → 400エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()
            mock_storage.is_valid_file_size.return_value = False

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = [("files", ("huge.jpg", self.create_test_image(), "image/jpeg"))]
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 400
            assert "too large" in response.json()["detail"].lower()

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_corrupted_file(self):
        """破損ファイル → 400エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            corrupted_content = b"not an image"
            files = [("files", ("corrupted.jpg", BytesIO(corrupted_content), "image/jpeg"))]

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('routers.pictures.Image.open', side_effect=Exception("Cannot identify image")):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"].lower()

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_text_file(self):
        """テキストファイル → 400エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()
            mock_storage.is_allowed_image_type.return_value = False

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            text_content = b"This is just text"
            files = [("files", ("test.txt", BytesIO(text_content), "text/plain"))]

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 400

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_heic_format(self, mock_uuid, mock_file_open):
        """HEIC画像の正常アップロード（PNG変換）"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image(format="JPEG")
            files = [("files", ("test.heic", test_image, "image/heic"))]

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image(format="HEIC")
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["mime_type"] == "image/png"
            assert picture["file_path"].endswith(".png")
            mock_img.convert.assert_called_with("RGB")

        finally:
            self.teardown_dependency_overrides()

    # ========== カテゴリ関連系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_with_valid_category(self, mock_uuid, mock_file_open):
        """有効カテゴリでのアップロード"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_category = self.create_mock_category(category_id=5, family_id=1)
            mock_db = self.setup_mock_db_for_upload(mock_category)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            form_data = {"category_id": "5"}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, data=form_data, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["category_id"] == 5

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_with_invalid_category(self):
        """無効カテゴリ → 400エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload(None)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            form_data = {"category_id": "999"}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", files=files, data=form_data, headers=headers)

            assert response.status_code == 400
            assert "category" in response.json()["detail"].lower()

        finally:
            self.teardown_dependency_overrides()

    # ========== 画像処理系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_exif_removal(self, mock_uuid, mock_file_open):
        """EXIF除去の確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image(
                exif_data={274: 1, 306: "2024:01:15 10:30:00"}
            )
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            assert mock_img.save.called

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_thumbnail_generation(self, mock_uuid, mock_file_open):
        """サムネイル生成確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image(size=(1920, 1080))
            mock_thumbnail = MagicMock()
            mock_thumbnail.save = MagicMock()
            mock_thumbnail.thumbnail = MagicMock()
            mock_img.copy.return_value = mock_thumbnail

            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            mock_thumbnail.thumbnail.assert_called_once_with((300, 300), Image.Resampling.LANCZOS)

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_metadata_extraction(self, mock_uuid, mock_file_open):
        """メタデータ抽出確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image(
                size=(2048, 1536),
                exif_data={306: "2024:01:15 10:30:00"}
            )
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["width"] == 2048
            assert picture["height"] == 1536
            assert picture["mime_type"] == "image/jpeg"

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_large_image(self, mock_uuid, mock_file_open):
        """大容量画像の処理"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1, size=(4000, 3000))
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image(size=(4000, 3000))
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["width"] == 4000
            assert picture["height"] == 3000

        finally:
            self.teardown_dependency_overrides()

    # ========== ファイルシステム系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_file_storage(self, mock_uuid, mock_file_open):
        """ファイル保存確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            # ファイル保存が2回呼ばれる（オリジナル + サムネイル）
            assert mock_file_open.call_count == 2

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_unique_filename(self, mock_uuid, mock_file_open):
        """ファイル名一意性確認"""
        fake_uuid = uuid_module.UUID('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            # UUID hex is used in filename
            assert "aaaaaaaabbbbccccddddeeeeeeeeeeee" in picture["file_path"]
            assert "aaaaaaaabbbbccccddddeeeeeeeeeeee" in picture["thumbnail_path"]

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_storage_path_validation(self, mock_uuid, mock_file_open):
        """ストレージパス検証"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["file_path"].startswith("photos/")
            assert picture["thumbnail_path"].startswith("thumbnails/")

        finally:
            self.teardown_dependency_overrides()

    # ========== データベース系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_database_record(self, mock_uuid, mock_file_open):
        """データベースレコード作成確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_family_scope(self, mock_uuid, mock_file_open):
        """家族スコープ設定確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user(family_id=5)
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 5)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["family_id"] == 5

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_auto_fields(self, mock_uuid, mock_file_open):
        """自動設定フィールド確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user(user_id=3, family_id=2)
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(3, 2)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            picture = self.get_response_picture(response.json())
            assert picture["uploaded_by"] == 3
            assert picture["family_id"] == 2
            assert picture["status"] == 1

        finally:
            self.teardown_dependency_overrides()

    # ========== エラーハンドリング系テスト ==========

    @patch('builtins.open', side_effect=OSError("Permission denied"))
    @patch('uuid.uuid4')
    def test_upload_picture_storage_error(self, mock_uuid, mock_file_open):
        """ストレージエラー時の処理"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 500
            assert "Failed to save image files" in response.json()["detail"]

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_database_error(self, mock_uuid, mock_file_open):
        """DB保存エラー時の処理"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload(save_success=False)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 500
            assert "Failed to save picture information" in response.json()["detail"]
            mock_db.rollback.assert_called_once()

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_rollback_on_failure(self, mock_uuid, mock_file_open):
        """失敗時ロールバック確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload(save_success=False)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 500
            mock_db.rollback.assert_called_once()

        finally:
            self.teardown_dependency_overrides()

    # ========== 複数ファイルアップロード系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_multiple_pictures_success(self, mock_uuid, mock_file_open):
        """複数画像（3枚）の同時アップロード"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=3)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert len(data["pictures"]) == 3
            # 全写真が同じgroup_idを持つ
            group_id = data["group_id"]
            for pic in data["pictures"]:
                assert pic["group_id"] == group_id

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_five_pictures_max(self, mock_uuid, mock_file_open):
        """最大5枚の画像を同時アップロード"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=5)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert len(data["pictures"]) == 5

        finally:
            self.teardown_dependency_overrides()

    def test_upload_six_pictures_rejected(self):
        """6枚以上は拒否"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=6)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 400
            assert "too many" in response.json()["detail"].lower()

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_shared_metadata(self, mock_uuid, mock_file_open):
        """グループ内の全写真が同じtitle/descriptionを持つ"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_category = self.create_mock_category()
            mock_db = self.setup_mock_db_for_upload(mock_category)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=3)
            form_data = {
                "title": "Family Trip",
                "description": "Summer vacation photos",
                "category_id": "1"
            }

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, data=form_data, headers=headers)

            assert response.status_code == 201
            data = response.json()
            for pic in data["pictures"]:
                assert pic["title"] == "Family Trip"
                assert pic["description"] == "Summer vacation photos"
                assert pic["category_id"] == 1

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_shared_group_id(self, mock_uuid, mock_file_open):
        """グループ内の全写真が同じgroup_idを持つ"""
        fake_uuid = uuid_module.UUID('abcdef01-2345-6789-abcd-ef0123456789')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=2)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            group_id = data["group_id"]
            assert group_id  # not empty
            assert data["pictures"][0]["group_id"] == group_id
            assert data["pictures"][1]["group_id"] == group_id

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_multiple_db_records(self, mock_uuid, mock_file_open):
        """複数ファイルで複数DBレコードが作成される"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=3)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            # db.add が3回呼ばれる（1ファイルにつき1回）
            assert mock_db.add.call_count == 3
            # db.commit は1回のみ（1トランザクション）
            mock_db.commit.assert_called_once()

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_multiple_file_storage(self, mock_uuid, mock_file_open):
        """複数ファイルのストレージ保存確認"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=3)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            # ファイル保存が6回呼ばれる（3ファイル x (オリジナル + サムネイル)）
            assert mock_file_open.call_count == 6

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_multiple_db_error_rollback(self, mock_uuid, mock_file_open):
        """複数ファイルでDB保存失敗時にロールバックされる"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload(save_success=False)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=3)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 500
            assert "Failed to save picture information" in response.json()["detail"]
            mock_db.rollback.assert_called_once()

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_single_file_backward_compatible(self, mock_uuid, mock_file_open):
        """1枚アップロード時も新レスポンス形式で返却"""
        fake_uuid = uuid_module.UUID('12345678-1234-5678-1234-567812345678')
        mock_uuid.return_value = fake_uuid

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            files = self.create_test_files(count=1)
            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            mock_img = self.create_mock_pil_image()
            with self.patch_image_processing(mock_img):
                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            # 新形式: group_id + pictures配列
            assert "group_id" in data
            assert "pictures" in data
            assert len(data["pictures"]) == 1
            assert data["pictures"][0]["group_id"] == data["group_id"]

        finally:
            self.teardown_dependency_overrides()
