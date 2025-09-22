"""
POST /api/pictures APIのテストファイル（画像アップロード）

画像アップロードAPI仕様:
- 認証済みユーザーが自分の家族に画像をアップロード
- multipart/form-dataでファイル + メタデータを送信
- EXIF除去、サムネイル生成、ファイル検証を実行
- 家族スコープでのアクセス制御

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 無効・期限切れトークンでのアクセス拒否
   - 削除済みユーザーでのアクセス拒否

2. ファイルアップロード基本テスト
   - 有効な画像ファイルでの正常アップロード
   - ファイルなしでのエラー（400）
   - レスポンス構造の検証

3. ファイル検証テスト
   - 許可されたMIME型（JPEG, PNG, GIF, WebP）
   - 許可されていないMIME型でのエラー（400）
   - ファイルサイズ制限（20MB）超過でのエラー（400）
   - 破損ファイルでのエラー（400）

4. メタデータ処理テスト
   - タイトル、説明、カテゴリIDの正常処理
   - 不正なカテゴリIDでのエラー（400）
   - EXIF除去の確認
   - 画像サイズ・MIME型の自動取得

5. ファイル保存テスト
   - オリジナル画像の保存確認
   - サムネイル生成・保存確認
   - ファイル名の一意性確保
   - ストレージパスの正確性

6. データベース操作テスト
   - Pictureレコードの正常作成
   - 必要フィールドの自動設定（family_id, uploaded_by等）
   - 撮影日時の自動抽出（EXIF）

7. エラーハンドリングテスト
   - ストレージ書き込みエラー時の処理
   - データベース保存エラー時の処理
   - 部分的失敗時のロールバック確認

テスト項目一覧:

認証・認可系 (3項目):
1. test_upload_picture_without_token - 未認証でアクセス → 403エラー
2. test_upload_picture_with_invalid_token - 無効トークンでアクセス → 401エラー
3. test_upload_picture_with_deleted_user - 削除済みユーザーでアクセス → 401エラー

基本アップロード系 (4項目):
4. test_upload_picture_success - 正常な画像アップロード
5. test_upload_picture_without_file - ファイルなし → 400エラー
6. test_upload_picture_response_structure - レスポンス構造の検証
7. test_upload_picture_with_metadata - メタデータ付きアップロード

ファイル検証系 (6項目):
8. test_upload_picture_jpeg_format - JPEG画像の正常アップロード
9. test_upload_picture_png_format - PNG画像の正常アップロード
10. test_upload_picture_invalid_format - 無効形式ファイル → 400エラー
11. test_upload_picture_oversized_file - ファイルサイズ超過 → 400エラー
12. test_upload_picture_corrupted_file - 破損ファイル → 400エラー
13. test_upload_picture_text_file - テキストファイル → 400エラー

画像処理系 (4項目):
14. test_upload_picture_exif_removal - EXIF除去の確認
15. test_upload_picture_thumbnail_generation - サムネイル生成確認
16. test_upload_picture_metadata_extraction - メタデータ抽出確認
17. test_upload_picture_large_image - 大容量画像の処理

ファイルシステム系 (3項目):
18. test_upload_picture_file_storage - ファイル保存確認
19. test_upload_picture_unique_filename - ファイル名一意性確認
20. test_upload_picture_storage_path_validation - ストレージパス検証

データベース系 (3項目):
21. test_upload_picture_database_record - データベースレコード作成確認
22. test_upload_picture_family_scope - 家族スコープ設定確認
23. test_upload_picture_auto_fields - 自動設定フィールド確認

エラーハンドリング系 (3項目):
24. test_upload_picture_storage_error - ストレージエラー時の処理
25. test_upload_picture_database_error - DB保存エラー時の処理
26. test_upload_picture_rollback_on_failure - 失敗時ロールバック確認

カテゴリ関連系 (2項目):
27. test_upload_picture_with_valid_category - 有効カテゴリでのアップロード
28. test_upload_picture_with_invalid_category - 無効カテゴリ → 400エラー
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta
from jose import jwt
from io import BytesIO
from PIL import Image
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

    def create_test_file(self, content: bytes, filename: str, content_type: str):
        """テスト用ファイル作成"""
        return {
            "file": (filename, BytesIO(content), content_type)
        }

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
            def mock_refresh(picture_obj):
                picture_obj.id = 1
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
        mock_config.allowed_image_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        return mock_config

    # ========== 認証・認可系テスト ==========

    def test_upload_picture_without_token(self):
        """未認証でアクセス → 403エラー"""
        test_image = self.create_test_image()
        files = {"file": ("test.jpg", test_image, "image/jpeg")}

        response = client.post("/api/pictures", files=files)
        assert response.status_code == 403
        assert "Not authenticated" in response.json()["detail"]

    def test_upload_picture_with_invalid_token(self):
        """無効トークンでアクセス → 401エラー"""
        test_image = self.create_test_image()
        files = {"file": ("test.jpg", test_image, "image/jpeg")}
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.post("/api/pictures", files=files, headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_upload_picture_with_deleted_user(self):
        """削除済みユーザーでアクセス → 401エラー"""
        test_image = self.create_test_image()
        files = {"file": ("test.jpg", test_image, "image/jpeg")}

        token = self.create_test_token(1, 1, status=0)  # status=0（削除済み）
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/pictures", files=files, headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    # ========== 基本アップロード系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_success(self, mock_uuid, mock_exists, mock_file_open):
        """正常な画像アップロード"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["family_id"] == 1
            assert data["uploaded_by"] == 1

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_without_file(self):
        """ファイルなし → 400エラー"""
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
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_response_structure(self, mock_uuid, mock_exists, mock_file_open):
        """レスポンス構造の検証"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()

            # 必須フィールドの存在確認
            required_fields = [
                "id", "family_id", "uploaded_by", "file_path",
                "thumbnail_path", "file_size", "mime_type",
                "width", "height", "status", "create_date", "update_date"
            ]

            for field in required_fields:
                assert field in data, f"Required field '{field}' is missing"

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_with_metadata(self, mock_uuid, mock_exists, mock_file_open):
        """メタデータ付きアップロード"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_category = self.create_mock_category()
            mock_db = self.setup_mock_db_for_upload(mock_category)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}
            data = {
                "title": "Test Title",
                "description": "Test Description",
                "category_id": "1"
            }

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, data=data, headers=headers)

            assert response.status_code == 201
            response_data = response.json()
            assert response_data["title"] == "Test Title"
            assert response_data["description"] == "Test Description"
            assert response_data["category_id"] == 1

        finally:
            self.teardown_dependency_overrides()

    # ========== ファイル検証系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_jpeg_format(self, mock_uuid, mock_exists, mock_file_open):
        """JPEG画像の正常アップロード"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image(format="JPEG")
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["mime_type"] == "image/jpeg"

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_png_format(self, mock_uuid, mock_exists, mock_file_open):
        """PNG画像の正常アップロード"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image(format="PNG")
            files = {"file": ("test.png", test_image, "image/png")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "PNG"
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["mime_type"] == "image/png"

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_invalid_format(self):
        """無効形式ファイル → 400エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()
            mock_storage.is_allowed_image_type.return_value = False  # 無効形式

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            # PDF ファイルとして送信
            test_content = b"fake pdf content"
            files = {"file": ("test.pdf", BytesIO(test_content), "application/pdf")}

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
            mock_storage.is_valid_file_size.return_value = False  # サイズ超過

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("huge.jpg", test_image, "image/jpeg")}

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

            # 破損した画像ファイル
            corrupted_content = b"not an image"
            files = {"file": ("corrupted.jpg", BytesIO(corrupted_content), "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open', side_effect=Exception("Cannot identify image")):
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

            # テキストファイル
            text_content = b"This is just text"
            files = {"file": ("test.txt", BytesIO(text_content), "text/plain")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 400

        finally:
            self.teardown_dependency_overrides()

    # ========== カテゴリ関連系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_with_valid_category(self, mock_uuid, mock_exists, mock_file_open):
        """有効カテゴリでのアップロード"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_category = self.create_mock_category(category_id=5, family_id=1)
            mock_db = self.setup_mock_db_for_upload(mock_category)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}
            data = {"category_id": "5"}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, data=data, headers=headers)

            assert response.status_code == 201
            response_data = response.json()
            assert response_data["category_id"] == 5

        finally:
            self.teardown_dependency_overrides()

    def test_upload_picture_with_invalid_category(self):
        """無効カテゴリ → 400エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload(None)  # カテゴリが見つからない
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}
            data = {"category_id": "999"}  # 存在しないカテゴリID

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/api/pictures", files=files, data=data, headers=headers)

            assert response.status_code == 400
            assert "category" in response.json()["detail"].lower()

        finally:
            self.teardown_dependency_overrides()

    # ========== 画像処理系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_exif_removal(self, mock_uuid, mock_exists, mock_file_open):
        """EXIF除去の確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img._getexif.return_value = {274: 1, 306: "2024:01:15 10:30:00"}  # EXIF data
                mock_img.save = MagicMock()
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            # EXIF除去のため、save が呼ばれることを確認
            assert mock_img.save.called

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_thumbnail_generation(self, mock_uuid, mock_exists, mock_file_open):
        """サムネイル生成確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (1920, 1080)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_thumbnail = MagicMock()
                mock_img.copy.return_value = mock_thumbnail
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            # サムネイル生成確認
            mock_thumbnail.thumbnail.assert_called_once_with((300, 300), Image.Resampling.LANCZOS)

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_metadata_extraction(self, mock_uuid, mock_exists, mock_file_open):
        """メタデータ抽出確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (2048, 1536)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                # EXIF DateTime を設定
                mock_img._getexif.return_value = {306: "2024:01:15 10:30:00"}
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["width"] == 2048
            assert data["height"] == 1536
            assert data["mime_type"] == "image/jpeg"

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_large_image(self, mock_uuid, mock_exists, mock_file_open):
        """大容量画像の処理"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            # 大きな画像を模擬
            large_image = self.create_test_image(size=(4000, 3000))
            files = {"file": ("large.jpg", large_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (4000, 3000)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["width"] == 4000
            assert data["height"] == 3000

        finally:
            self.teardown_dependency_overrides()

    # ========== ファイルシステム系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_file_storage(self, mock_uuid, mock_exists, mock_file_open):
        """ファイル保存確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            # ファイル保存が2回呼ばれる（オリジナル + サムネイル）
            assert mock_file_open.call_count == 2

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_unique_filename(self, mock_uuid, mock_exists, mock_file_open):
        """ファイル名一意性確認"""
        mock_uuid.return_value.hex = "uniquetest123"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert "uniquetest123" in data["file_path"]
            assert "uniquetest123" in data["thumbnail_path"]

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_storage_path_validation(self, mock_uuid, mock_exists, mock_file_open):
        """ストレージパス検証"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["file_path"].startswith("photos/")
            assert data["thumbnail_path"].startswith("thumbnails/")

        finally:
            self.teardown_dependency_overrides()

    # ========== データベース系テスト ==========

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_database_record(self, mock_uuid, mock_exists, mock_file_open):
        """データベースレコード作成確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            # データベース操作が呼ばれることを確認
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_family_scope(self, mock_uuid, mock_exists, mock_file_open):
        """家族スコープ設定確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user(family_id=5)
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 5)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["family_id"] == 5

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_auto_fields(self, mock_uuid, mock_exists, mock_file_open):
        """自動設定フィールド確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user(user_id=3, family_id=2)
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(3, 2)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["uploaded_by"] == 3
            assert data["family_id"] == 2
            assert data["status"] == 1

        finally:
            self.teardown_dependency_overrides()

    # ========== エラーハンドリング系テスト ==========

    @patch('builtins.open', side_effect=OSError("Permission denied"))
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_storage_error(self, mock_uuid, mock_exists, mock_file_open):
        """ストレージエラー時の処理"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload()
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 500
            assert "Failed to save image files" in response.json()["detail"]

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=False)
    @patch('uuid.uuid4')
    def test_upload_picture_database_error(self, mock_uuid, mock_exists, mock_file_open):
        """DB保存エラー時の処理"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload(save_success=False)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 500
            assert "Failed to save picture information" in response.json()["detail"]
            # ロールバックが呼ばれることを確認
            mock_db.rollback.assert_called_once()

        finally:
            self.teardown_dependency_overrides()

    @patch('builtins.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_upload_picture_rollback_on_failure(self, mock_uuid, mock_file_open):
        """失敗時ロールバック確認"""
        mock_uuid.return_value.hex = "test123456"

        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_upload(save_success=False)
            mock_storage = self.create_mock_storage_config()

            self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_img.size = (800, 600)
                mock_img.format = "JPEG"
                mock_img.mode = "RGB"
                mock_img.copy.return_value = mock_img
                mock_img.thumbnail = MagicMock()
                mock_pil.return_value = mock_img

                response = client.post("/api/pictures", files=files, headers=headers)

            assert response.status_code == 500
            # データベースロールバックが呼ばれることを確認
            mock_db.rollback.assert_called_once()

        finally:
            self.teardown_dependency_overrides()