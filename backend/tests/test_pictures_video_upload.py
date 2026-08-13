"""
POST /api/pictures/video APIのテストファイル（動画アップロード）

動画アップロードAPI仕様:
- 認証済みユーザーが自分の家族に動画をアップロード（1回1本のみ）
- multipart/form-dataでファイル + メタデータを送信
- 長さ・サイズ検証、位置情報メタデータ除去、サムネイル生成を実行
- 家族スコープでのアクセス制御

実際のffmpeg/ffprobeは呼び出さず、routers.pictures内の
probe_video / strip_metadata_and_copy / extract_thumbnail_frame をパッチして、
ファイルI/Oのみ実物（tmp_path配下）で行う。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from jose import jwt
from io import BytesIO
from pathlib import Path
from PIL import Image

from main import app
from models import User, Category
from config import SECRET_KEY, ALGORITHM

client = TestClient(app)


class TestPicturesVideoUploadAPI:
    """POST /api/pictures/video APIのテストクラス"""

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

    def create_fake_jpeg_bytes(self) -> bytes:
        """サムネイル抽出結果として使う、実在する小さなJPEGバイト列を作成"""
        image = Image.new("RGB", (640, 480), color=(0, 128, 255))
        buf = BytesIO()
        image.save(buf, format="JPEG")
        return buf.getvalue()

    def create_mock_user(self, user_id: int = 1, family_id: int = 1, user_type: int = 0, status: int = 1):
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.family_id = family_id
        mock_user.user_name = f"test_user_{user_id}"
        mock_user.type = user_type
        mock_user.status = status
        return mock_user

    def create_mock_category(self, category_id: int = 1, family_id: int = 1):
        mock_category = MagicMock(spec=Category)
        mock_category.id = category_id
        mock_category.family_id = family_id
        mock_category.name = "Test Category"
        mock_category.status = 1
        return mock_category

    def create_mock_storage_config(self, tmp_path: Path):
        """モックストレージ設定作成。ファイルパスはtmp_path配下の実パスを返す"""
        mock_config = MagicMock()
        mock_config.is_allowed_video_type.return_value = True
        mock_config.is_valid_video_size.return_value = True
        mock_config.is_valid_video_duration.return_value = True
        mock_config.max_video_size = 104857600  # 100MB
        mock_config.max_video_duration_seconds = 30
        mock_config.allowed_video_types = ["video/mp4", "video/quicktime"]
        mock_config.get_photo_file_path.side_effect = lambda name: tmp_path / name
        mock_config.get_thumbnail_file_path.side_effect = lambda name: tmp_path / name
        return mock_config

    def setup_mock_db_for_upload(self, mock_category=None, save_success=True):
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_category

        if save_success:
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()

            def mock_refresh(picture_obj):
                picture_obj.id = 1
                picture_obj.create_date = datetime(2026, 1, 15, 12, 0, 0)
                picture_obj.update_date = datetime(2026, 1, 15, 12, 0, 0)
                return picture_obj

            mock_db.refresh = MagicMock(side_effect=mock_refresh)
        else:
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock(side_effect=Exception("Database error"))
            mock_db.rollback = MagicMock()

        return mock_db

    def setup_dependency_overrides(self, mock_db, mock_user, mock_storage_config):
        from database import get_db
        from dependencies import get_current_user
        from config.storage import get_storage_config

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

    def teardown_dependency_overrides(self):
        app.dependency_overrides.clear()

    def probe_side_effect(self, duration=10.0, width=1920, height=1080,
                           has_video_stream=True, creation_time="2026-08-13T01:02:03.000000Z"):
        def _probe(path):
            return {
                "duration_seconds": duration,
                "width": width,
                "height": height,
                "creation_time": creation_time,
                "has_video_stream": has_video_stream,
            }
        return _probe

    def strip_side_effect(self, video_bytes: bytes = b"stripped-video-bytes"):
        def _strip(input_path, output_path):
            Path(output_path).write_bytes(video_bytes)
        return _strip

    def thumbnail_side_effect(self, jpeg_bytes: bytes):
        def _extract(video_path, output_path):
            Path(output_path).write_bytes(jpeg_bytes)
        return _extract

    # ========== 認証・認可系テスト ==========

    def test_upload_video_without_token(self):
        files = {"file": ("test.mp4", BytesIO(b"fake mp4 content"), "video/mp4")}
        response = client.post("/api/pictures/video", files=files)
        assert response.status_code == 403

    def test_upload_video_with_invalid_token(self):
        files = {"file": ("test.mp4", BytesIO(b"fake mp4 content"), "video/mp4")}
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/pictures/video", files=files, headers=headers)
        assert response.status_code == 401

    # ========== 正常系テスト ==========

    def test_upload_video_success(self, tmp_path):
        mock_user = self.create_mock_user()
        mock_category = self.create_mock_category()
        mock_db = self.setup_mock_db_for_upload(mock_category=mock_category)
        mock_storage = self.create_mock_storage_config(tmp_path)
        self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

        jpeg_bytes = self.create_fake_jpeg_bytes()
        token = self.create_test_token(1, 1)
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.mp4", BytesIO(b"fake mp4 content"), "video/mp4")}
        data = {"category_id": "1", "title": "テスト動画"}

        try:
            with patch('routers.pictures.probe_video', side_effect=self.probe_side_effect()), \
                 patch('routers.pictures.strip_metadata_and_copy', side_effect=self.strip_side_effect()), \
                 patch('routers.pictures.extract_thumbnail_frame', side_effect=self.thumbnail_side_effect(jpeg_bytes)):
                response = client.post("/api/pictures/video", files=files, data=data, headers=headers)
        finally:
            self.teardown_dependency_overrides()

        assert response.status_code == 201
        body = response.json()
        assert "group_id" in body
        picture = body["pictures"][0]
        assert picture["mime_type"] == "video/mp4"
        assert picture["duration"] == 10
        assert picture["width"] == 1920
        assert picture["height"] == 1080
        assert picture["title"] == "テスト動画"

    # ========== バリデーション系テスト ==========

    def test_upload_video_duration_exceeded(self, tmp_path):
        mock_user = self.create_mock_user()
        mock_db = self.setup_mock_db_for_upload(mock_category=None)
        mock_storage = self.create_mock_storage_config(tmp_path)
        mock_storage.is_valid_video_duration.return_value = False
        self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

        token = self.create_test_token(1, 1)
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.mp4", BytesIO(b"fake mp4 content"), "video/mp4")}

        try:
            with patch('routers.pictures.probe_video', side_effect=self.probe_side_effect(duration=45.0)):
                response = client.post("/api/pictures/video", files=files, headers=headers)
        finally:
            self.teardown_dependency_overrides()

        assert response.status_code == 400
        assert "too long" in response.json()["detail"]

    def test_upload_video_size_exceeded(self, tmp_path):
        mock_user = self.create_mock_user()
        mock_db = self.setup_mock_db_for_upload(mock_category=None)
        mock_storage = self.create_mock_storage_config(tmp_path)
        mock_storage.is_valid_video_size.return_value = False
        self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

        token = self.create_test_token(1, 1)
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.mp4", BytesIO(b"fake mp4 content"), "video/mp4")}

        try:
            response = client.post("/api/pictures/video", files=files, headers=headers)
        finally:
            self.teardown_dependency_overrides()

        assert response.status_code == 400
        assert "too large" in response.json()["detail"]

    def test_upload_video_invalid_type(self, tmp_path):
        mock_user = self.create_mock_user()
        mock_db = self.setup_mock_db_for_upload(mock_category=None)
        mock_storage = self.create_mock_storage_config(tmp_path)
        mock_storage.is_allowed_video_type.return_value = False
        self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

        token = self.create_test_token(1, 1)
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.avi", BytesIO(b"fake avi content"), "video/x-msvideo")}

        try:
            response = client.post("/api/pictures/video", files=files, headers=headers)
        finally:
            self.teardown_dependency_overrides()

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    def test_upload_video_no_video_stream(self, tmp_path):
        """映像ストリームがない（音声のみ等）ファイル → 400エラー"""
        mock_user = self.create_mock_user()
        mock_db = self.setup_mock_db_for_upload(mock_category=None)
        mock_storage = self.create_mock_storage_config(tmp_path)
        self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

        token = self.create_test_token(1, 1)
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.mp4", BytesIO(b"fake mp4 content"), "video/mp4")}

        try:
            with patch('routers.pictures.probe_video',
                       side_effect=self.probe_side_effect(has_video_stream=False, width=None, height=None)):
                response = client.post("/api/pictures/video", files=files, headers=headers)
        finally:
            self.teardown_dependency_overrides()

        assert response.status_code == 400

    def test_upload_video_category_not_found(self, tmp_path):
        mock_user = self.create_mock_user()
        mock_db = self.setup_mock_db_for_upload(mock_category=None)
        mock_storage = self.create_mock_storage_config(tmp_path)
        self.setup_dependency_overrides(mock_db, mock_user, mock_storage)

        token = self.create_test_token(1, 1)
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.mp4", BytesIO(b"fake mp4 content"), "video/mp4")}
        data = {"category_id": "999"}

        try:
            response = client.post("/api/pictures/video", files=files, data=data, headers=headers)
        finally:
            self.teardown_dependency_overrides()

        assert response.status_code == 400
        assert "not found" in response.json()["detail"]
