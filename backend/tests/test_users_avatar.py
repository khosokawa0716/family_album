"""
プロフィール画像（アバター）関連APIのテストファイル

- POST /api/users/{user_id}/avatar: アバターアップロード
- DELETE /api/users/{user_id}/avatar: アバター削除
- GET /api/avatars/{filename}: 署名付きURLによるアバター配信
"""

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from io import BytesIO
from PIL import Image

from main import app
from models import User
from database import get_db
from dependencies import get_current_user
from config.storage import get_storage_config
from utils.url_signature import create_signed_url

client = TestClient(app)


class FakeAvatarStorageConfig:
    """avatarsディレクトリを実ファイルシステム(tmp_path)に向けたテスト用ストレージ設定"""

    def __init__(self, avatars_path, max_avatar_upload_size=5 * 1024 * 1024):
        self.avatars_path = avatars_path
        self.max_avatar_upload_size = max_avatar_upload_size
        self.allowed_image_types = [
            "image/jpeg", "image/png", "image/gif", "image/webp", "image/heic", "image/heif"
        ]

    def is_allowed_image_type(self, mime_type):
        return mime_type in self.allowed_image_types

    def is_valid_avatar_size(self, file_size):
        return file_size <= self.max_avatar_upload_size

    def get_avatars_path(self):
        return self.avatars_path

    def get_avatar_file_path(self, filename):
        return self.avatars_path / filename


def create_test_image_bytes(size=(400, 300), format="JPEG"):
    image = Image.new("RGB", size, color=(120, 200, 80))
    buf = BytesIO()
    image.save(buf, format=format)
    buf.seek(0)
    return buf


def create_mock_user(user_id=1, family_id=1, user_type=0, status=1, avatar_path=None):
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.family_id = family_id
    mock_user.user_name = f"test_user_{user_id}"
    mock_user.nickname = None
    mock_user.theme_color = None
    mock_user.type = user_type
    mock_user.status = status
    mock_user.avatar_path = avatar_path
    mock_user.email = f"user{user_id}@example.com"
    mock_user.create_date = "2026-01-01T00:00:00"
    mock_user.update_date = "2026-01-01T00:00:00"
    return mock_user


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


class TestUploadAvatar:
    def test_upload_avatar_success_self(self, tmp_path):
        mock_user = create_mock_user()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        files = {"file": ("avatar.jpg", create_test_image_bytes(), "image/jpeg")}
        response = client.post("/api/users/1/avatar", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["avatar_path"] is not None
        assert "/api/avatars/" in data["avatar_path"]
        assert "signature=" in data["avatar_path"]

        # 実際に正方形JPEGが保存されていること
        saved_files = list(tmp_path.glob("*.jpg"))
        assert len(saved_files) == 1
        with Image.open(saved_files[0]) as saved_image:
            assert saved_image.size == (256, 256)

    def test_upload_avatar_replaces_old_file(self, tmp_path):
        mock_user = create_mock_user()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        files = {"file": ("avatar.jpg", create_test_image_bytes(), "image/jpeg")}
        first_response = client.post("/api/users/1/avatar", files=files)
        assert first_response.status_code == 200
        assert len(list(tmp_path.glob("*.jpg"))) == 1

        # mock_userはエンドポイント内でtarget_userとして直接更新されるため、
        # 1回目アップロード後は既にavatar_pathが新しいパスに書き換わっている

        files2 = {"file": ("avatar2.jpg", create_test_image_bytes(), "image/jpeg")}
        second_response = client.post("/api/users/1/avatar", files=files2)
        assert second_response.status_code == 200

        # 旧ファイルが削除され、新しいファイル1つだけが残る
        assert len(list(tmp_path.glob("*.jpg"))) == 1

    def test_upload_avatar_other_user_forbidden(self, tmp_path):
        mock_current_user = create_mock_user(user_id=2, user_type=0)
        mock_target_user = create_mock_user(user_id=3)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_target_user
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        files = {"file": ("avatar.jpg", create_test_image_bytes(), "image/jpeg")}
        response = client.post("/api/users/3/avatar", files=files)

        assert response.status_code == 403
        assert len(list(tmp_path.glob("*.jpg"))) == 0

    def test_upload_avatar_admin_can_set_for_other_user(self, tmp_path):
        mock_admin = create_mock_user(user_id=1, user_type=10)
        mock_target_user = create_mock_user(user_id=2)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_target_user
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        files = {"file": ("avatar.jpg", create_test_image_bytes(), "image/jpeg")}
        response = client.post("/api/users/2/avatar", files=files)

        assert response.status_code == 200

    def test_upload_avatar_invalid_type(self, tmp_path):
        mock_user = create_mock_user()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        files = {"file": ("avatar.txt", BytesIO(b"not an image"), "text/plain")}
        response = client.post("/api/users/1/avatar", files=files)

        assert response.status_code == 400
        assert len(list(tmp_path.glob("*"))) == 0

    def test_upload_avatar_too_large(self, tmp_path):
        mock_user = create_mock_user()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        storage_config = FakeAvatarStorageConfig(tmp_path, max_avatar_upload_size=10)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        files = {"file": ("avatar.jpg", create_test_image_bytes(), "image/jpeg")}
        response = client.post("/api/users/1/avatar", files=files)

        assert response.status_code == 400
        assert "too large" in response.json()["detail"]

    def test_upload_avatar_no_token(self, tmp_path):
        files = {"file": ("avatar.jpg", create_test_image_bytes(), "image/jpeg")}
        response = client.post("/api/users/1/avatar", files=files)

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_upload_avatar_nonexistent_user(self, tmp_path):
        mock_user = create_mock_user()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        files = {"file": ("avatar.jpg", create_test_image_bytes(), "image/jpeg")}
        response = client.post("/api/users/99999/avatar", files=files)

        assert response.status_code == 404


class TestDeleteAvatar:
    def test_delete_avatar_success(self, tmp_path):
        avatar_file = tmp_path / "existing.jpg"
        avatar_file.write_bytes(b"fake avatar content")

        mock_user = create_mock_user(avatar_path="avatars/existing.jpg")
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        response = client.delete("/api/users/1/avatar")

        assert response.status_code == 200
        assert response.json()["avatar_path"] is None
        assert not avatar_file.exists()

    def test_delete_avatar_not_set(self, tmp_path):
        mock_user = create_mock_user(avatar_path=None)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        response = client.delete("/api/users/1/avatar")

        assert response.status_code == 409

    def test_delete_avatar_other_user_forbidden(self, tmp_path):
        mock_current_user = create_mock_user(user_id=2, user_type=0)
        mock_target_user = create_mock_user(user_id=3, avatar_path="avatars/x.jpg")
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_target_user
        storage_config = FakeAvatarStorageConfig(tmp_path)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        response = client.delete("/api/users/3/avatar")

        assert response.status_code == 403


class TestGetAvatar:
    def test_get_avatar_missing_signature(self, tmp_path):
        storage_config = FakeAvatarStorageConfig(tmp_path)
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        response = client.get("/api/avatars/somefile.jpg")

        assert response.status_code == 403

    def test_get_avatar_invalid_signature(self, tmp_path):
        avatar_file = tmp_path / "avatar.jpg"
        avatar_file.write_bytes(b"fake avatar content")
        storage_config = FakeAvatarStorageConfig(tmp_path)
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        response = client.get(
            "/api/avatars/avatar.jpg",
            params={"signature": "invalid", "expires": "9999999999"}
        )

        assert response.status_code == 403

    def test_get_avatar_valid_signature_serves_file(self, tmp_path):
        avatar_file = tmp_path / "avatar.jpg"
        avatar_file.write_bytes(b"fake avatar content")
        storage_config = FakeAvatarStorageConfig(tmp_path)
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        signed_url = create_signed_url("avatar.jpg", "avatars")
        query_params = parse_qs(urlparse(signed_url).query)

        response = client.get(
            "/api/avatars/avatar.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )

        assert response.status_code == 200
        assert response.content == b"fake avatar content"

    def test_get_avatar_file_not_found(self, tmp_path):
        storage_config = FakeAvatarStorageConfig(tmp_path)
        app.dependency_overrides[get_storage_config] = lambda: storage_config

        signed_url = create_signed_url("missing.jpg", "avatars")
        query_params = parse_qs(urlparse(signed_url).query)

        response = client.get(
            "/api/avatars/missing.jpg",
            params={
                "signature": query_params["signature"][0],
                "expires": query_params["expires"][0]
            }
        )

        assert response.status_code == 404
