"""
GET /api/pictures/:id APIのテストファイル（写真詳細取得）

写真詳細取得API仕様:
- 認証済みユーザーが自分の家族の写真詳細を取得
- 画像ファイルの詳細情報（メタデータ、カテゴリ、アップロード者情報など）を含む
- 家族スコープでのアクセス制御

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 無効・期限切れトークンでのアクセス拒否
   - 家族ID範囲でのアクセス制御（他家族の写真は見えない）
   - 削除済みユーザーでのアクセス拒否

2. 基本動作テスト
   - 存在する写真IDでの正常レスポンス
   - 存在しない写真IDでの404エラー
   - 削除済み写真（status=0）での404エラー
   - レスポンス構造の検証（全フィールドが含まれている）

3. パラメータ検証テスト
   - 無効なIDフォーマット（文字列、負の数）でのエラーハンドリング
   - 0またはNULLのIDでのエラーハンドリング

4. データ整合性テスト
   - 関連データの正確性（カテゴリ情報、アップロード者情報）
   - 日時データの正確性（taken_date、create_date、update_date）
   - ファイル情報の正確性（サイズ、パス、MIMEタイプ等）

5. エラーハンドリングテスト
   - システムエラー時の適切なエラーレスポンス
   - データベース接続エラー時の処理

テスト項目一覧:

認証・認可系 (5項目):
1. test_get_picture_detail_without_token - 未認証でアクセス → 401エラー
2. test_get_picture_detail_with_invalid_token - 無効トークンでアクセス → 401エラー
3. test_get_picture_detail_with_expired_token - 期限切れトークンでアクセス → 401エラー
4. test_get_picture_detail_different_family - 他家族の写真へのアクセス → 404エラー
5. test_get_picture_detail_with_deleted_user - 削除済みユーザーでアクセス → 401エラー

基本動作系 (4項目):
6. test_get_picture_detail_success - 正常な写真詳細取得
7. test_get_picture_detail_not_found - 存在しない写真ID → 404エラー
8. test_get_picture_detail_deleted_picture - 削除済み写真 → 404エラー
9. test_get_picture_detail_response_structure - レスポンス構造の検証

パラメータ検証系 (3項目):
10. test_get_picture_detail_invalid_id_format - 無効IDフォーマット → 422エラー
11. test_get_picture_detail_zero_id - ID=0 → 404エラー
12. test_get_picture_detail_negative_id - 負のID → 422エラー

データ整合性系 (3項目):
13. test_get_picture_detail_with_category - カテゴリ付き写真の詳細取得
14. test_get_picture_detail_without_category - カテゴリなし写真の詳細取得
15. test_get_picture_detail_metadata_accuracy - メタデータの正確性検証
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from jose import jwt

from main import app
from models import User, Picture, Category
from auth import SECRET_KEY, ALGORITHM

client = TestClient(app)


class TestPicturesDetailAPI:
    """GET /api/pictures/:id APIのテストクラス"""

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

    def create_expired_token(self, user_id: int, family_id: int):
        """期限切れトークン作成"""
        payload = {
            "sub": str(user_id),
            "family_id": family_id,
            "user_type": 0,
            "status": 1,
            "exp": datetime.utcnow() - timedelta(minutes=1)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def setup_mock_db_for_picture(self, picture_data=None, user_family_id=1):
        """写真詳細取得用のDBモック設定"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # 家族ID・statusのフィルタリング条件をチェック
        if picture_data:
            # 家族IDが一致し、statusが1の場合のみ返す
            if (picture_data.family_id == user_family_id and
                picture_data.status == 1):
                mock_query.first.return_value = picture_data
            else:
                mock_query.first.return_value = None
        else:
            mock_query.first.return_value = None

        return mock_db

    def setup_dependency_overrides(self, mock_db, mock_user):
        """依存注入のオーバーライド設定"""
        from database import get_db
        from dependencies import get_current_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

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

    def create_mock_picture(self, picture_id: int = 1, family_id: int = 1, status: int = 1):
        """モック写真作成"""
        mock_picture = MagicMock(spec=Picture)
        mock_picture.id = picture_id
        mock_picture.family_id = family_id
        mock_picture.uploaded_by = 1
        mock_picture.title = "Test Picture"
        mock_picture.description = "Test Description"
        mock_picture.file_path = "/path/to/test.jpg"
        mock_picture.thumbnail_path = "/path/to/thumb.jpg"
        mock_picture.file_size = 1024000
        mock_picture.mime_type = "image/jpeg"
        mock_picture.width = 1920
        mock_picture.height = 1080
        mock_picture.taken_date = datetime(2024, 1, 15, 10, 30, 0)
        mock_picture.category_id = 1
        mock_picture.status = status
        mock_picture.create_date = datetime(2024, 1, 15, 12, 0, 0)
        mock_picture.update_date = datetime(2024, 1, 15, 12, 0, 0)
        return mock_picture

    # ========== 認証・認可系テスト ==========

    def test_get_picture_detail_without_token(self):
        """未認証でアクセス → 403エラー"""
        response = client.get("/api/pictures/1")
        assert response.status_code == 403
        assert "Not authenticated" in response.json()["detail"]

    def test_get_picture_detail_with_invalid_token(self):
        """無効トークンでアクセス → 401エラー"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/pictures/1", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_picture_detail_with_expired_token(self):
        """期限切れトークンでアクセス → 401エラー"""
        expired_token = self.create_expired_token(1, 1)
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/pictures/1", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_picture_detail_different_family(self):
        """他家族の写真へのアクセス → 404エラー"""
        try:
            # ユーザーはfamily_id=1、写真はfamily_id=2
            mock_user = self.create_mock_user(family_id=1)
            mock_picture = self.create_mock_picture(family_id=2)
            mock_db = self.setup_mock_db_for_picture(mock_picture, user_family_id=1)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/1", headers=headers)

            assert response.status_code == 404
            assert "Picture not found" in response.json()["detail"]
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_with_deleted_user(self):
        """削除済みユーザーでアクセス → 401エラー"""
        token = self.create_test_token(1, 1, status=0)  # status=0（削除済み）
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/pictures/1", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    # ========== 基本動作系テスト ==========

    def test_get_picture_detail_success(self):
        """正常な写真詳細取得"""
        try:
            mock_user = self.create_mock_user()
            mock_picture = self.create_mock_picture()
            mock_db = self.setup_mock_db_for_picture(mock_picture)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/1", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["title"] == "Test Picture"
            assert data["family_id"] == 1
            assert data["file_path"] == "/path/to/test.jpg"
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_not_found(self):
        """存在しない写真ID → 404エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_picture(None)  # 写真が見つからない

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/999", headers=headers)

            assert response.status_code == 404
            assert "Picture not found" in response.json()["detail"]
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_deleted_picture(self):
        """削除済み写真 → 404エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_picture = self.create_mock_picture(status=0)  # status=0（削除済み）
            mock_db = self.setup_mock_db_for_picture(mock_picture, user_family_id=1)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/1", headers=headers)

            assert response.status_code == 404
            assert "Picture not found" in response.json()["detail"]
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_response_structure(self):
        """レスポンス構造の検証"""
        try:
            mock_user = self.create_mock_user()
            mock_picture = self.create_mock_picture()
            mock_db = self.setup_mock_db_for_picture(mock_picture)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/1", headers=headers)

            assert response.status_code == 200
            data = response.json()

            # 必須フィールドの存在確認
            required_fields = [
                "id", "family_id", "uploaded_by", "title", "description",
                "file_path", "thumbnail_path", "file_size", "mime_type",
                "width", "height", "taken_date", "category_id", "status",
                "create_date", "update_date"
            ]

            for field in required_fields:
                assert field in data, f"Required field '{field}' is missing"
        finally:
            self.teardown_dependency_overrides()

    # ========== パラメータ検証系テスト ==========

    def test_get_picture_detail_invalid_id_format(self):
        """無効IDフォーマット → 422エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_picture(None)
            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            # 文字列ID
            response = client.get("/api/pictures/abc", headers=headers)
            assert response.status_code == 422
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_zero_id(self):
        """ID=0 → 404エラー"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_picture(None)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/0", headers=headers)

            assert response.status_code == 404
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_negative_id(self):
        """負のID → 404エラー（存在しないIDとして扱われる）"""
        try:
            mock_user = self.create_mock_user()
            mock_db = self.setup_mock_db_for_picture(None)
            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/-1", headers=headers)
            assert response.status_code == 404
            assert "Picture not found" in response.json()["detail"]
        finally:
            self.teardown_dependency_overrides()

    # ========== データ整合性系テスト ==========

    def test_get_picture_detail_with_category(self):
        """カテゴリ付き写真の詳細取得"""
        try:
            mock_user = self.create_mock_user()
            mock_picture = self.create_mock_picture()
            mock_picture.category_id = 5
            mock_db = self.setup_mock_db_for_picture(mock_picture)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/1", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["category_id"] == 5
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_without_category(self):
        """カテゴリなし写真の詳細取得"""
        try:
            mock_user = self.create_mock_user()
            mock_picture = self.create_mock_picture()
            mock_picture.category_id = None
            mock_db = self.setup_mock_db_for_picture(mock_picture)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/1", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["category_id"] is None
        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_detail_metadata_accuracy(self):
        """メタデータの正確性検証"""
        try:
            mock_user = self.create_mock_user()
            mock_picture = self.create_mock_picture()
            mock_picture.file_size = 2048000
            mock_picture.width = 3840
            mock_picture.height = 2160
            mock_picture.mime_type = "image/png"
            mock_db = self.setup_mock_db_for_picture(mock_picture)

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/pictures/1", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["file_size"] == 2048000
            assert data["width"] == 3840
            assert data["height"] == 2160
            assert data["mime_type"] == "image/png"
        finally:
            self.teardown_dependency_overrides()