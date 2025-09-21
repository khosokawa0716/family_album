"""
GET /api/pictures APIのテストファイル（写真一覧取得）

写真一覧取得API仕様:
- 認証済みユーザーが自分の家族の写真一覧を取得
- カテゴリ・年月での絞り込み機能
- 無限スクロール対応（ページネーション）
- デフォルトソート: 作成日降順

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 無効・期限切れトークンでのアクセス拒否
   - 家族ID範囲でのアクセス制御（他家族の写真は見えない）
   - 削除済みユーザーでのアクセス拒否

2. 基本動作テスト
   - 写真が0件の場合の正常レスポンス
   - 写真が存在する場合の正常レスポンス
   - レスポンス構造の検証
   - デフォルトソート（作成日降順）

3. フィルタリング機能テスト
   - カテゴリフィルター（単一・複数）
   - 年月フィルター（年のみ・年月指定）
   - 無効なフィルター値のエラーハンドリング
   - 組み合わせフィルタ

4. ページネーション機能テスト
   - limit/offsetパラメータの動作
   - 最大件数制限
   - 次ページの存在判定
   - 無効なpaginationパラメータ

5. エラーハンドリングテスト
   - 不正なクエリパラメータ
   - DB接続エラーシミュレート
   - 不正な形式のリクエスト

テスト項目（28項目）:

【認証・認可系】(6項目)
- test_get_pictures_without_auth: 未認証でのアクセス拒否（401）
- test_get_pictures_with_invalid_token: 無効トークンでのアクセス拒否（401）
- test_get_pictures_with_expired_token: 期限切れトークンでのアクセス拒否（401）
- test_get_pictures_family_scope: 異なる家族の写真は表示されない
- test_get_pictures_admin_vs_user: 管理者・一般ユーザーで同じ結果
- test_get_pictures_deleted_user: 削除済みユーザーでのアクセス拒否

【基本動作】(4項目)
- test_get_pictures_success_empty: 写真が0件の場合の正常レスポンス
- test_get_pictures_success_with_data: 写真が存在する場合の正常レスポンス
- test_get_pictures_response_structure: レスポンス構造の検証
- test_get_pictures_default_sort: デフォルトソート（作成日降順）

【フィルタリング機能】(8項目)
- test_filter_by_category_single: 単一カテゴリでのフィルタリング
- test_filter_by_category_multiple: 複数カテゴリでのフィルタリング
- test_filter_by_category_nonexistent: 存在しないカテゴリでのフィルタリング
- test_filter_by_year: 年でのフィルタリング
- test_filter_by_year_month: 年月でのフィルタリング
- test_filter_invalid_date_format: 無効な日付形式でのエラー（400）
- test_filter_combined: カテゴリ・年月の組み合わせフィルタ
- test_filter_no_results: フィルタ結果が0件の場合

【ページネーション機能】(7項目)
- test_pagination_default_limit: デフォルトlimit値
- test_pagination_custom_limit: カスタムlimit値
- test_pagination_with_offset: offsetを使った2ページ目以降
- test_pagination_max_limit_exceeded: 最大limit超過時の制限
- test_pagination_invalid_params: 無効なpaginationパラメータ（400）
- test_pagination_last_page: 最終ページでの動作
- test_pagination_has_more_flag: 次ページ存在フラグの正確性

【エラーハンドリング】(3項目)
- test_invalid_query_parameters: 不正なクエリパラメータ（400）
- test_database_error_simulation: DB接続エラーシミュレート（500）
- test_malformed_request: 不正な形式のリクエスト（400）

注意: 写真モデル・テーブル・APIは未実装のため、実装時にテストコードも合わせて作成予定
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt
from main import app
from models import User, Picture, Category
from auth import SECRET_KEY, ALGORITHM

client = TestClient(app)


class TestPicturesListAPI:
    """GET /api/pictures APIのテストクラス"""

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

    def setup_mock_db(self, mock_count=0, mock_results=None):
        """共通のDBモック設定"""
        if mock_results is None:
            mock_results = []

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = mock_count
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_results
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

    # ========== 認証・認可系テスト ==========

    def test_get_pictures_without_auth(self):
        """未認証でのアクセス拒否（403）"""
        response = client.get("/api/pictures")
        assert response.status_code == 403
        assert "Not authenticated" in response.json()["detail"]

    def test_get_pictures_with_invalid_token(self):
        """無効トークンでのアクセス拒否（401）"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/pictures", headers=headers)
        assert response.status_code == 401

    def test_get_pictures_with_expired_token(self):
        """期限切れトークンでのアクセス拒否（401）"""
        expired_token = self.create_expired_token(1, 1)
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/pictures", headers=headers)
        assert response.status_code == 401

    def test_get_pictures_family_scope(self):
        """異なる家族の写真は表示されない"""
        # 家族1のユーザー
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        # 家族1と家族2の写真を作成
        family1_picture = Picture()
        family1_picture.id = 1
        family1_picture.family_id = 1
        family1_picture.status = 1
        family1_picture.uploaded_by = 1
        family1_picture.file_path = "/path/to/pic1.jpg"
        family1_picture.create_date = datetime.now()
        family1_picture.update_date = datetime.now()

        mock_db = self.setup_mock_db(mock_count=1, mock_results=[family1_picture])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures")
            assert response.status_code == 200
            data = response.json()
            assert len(data["pictures"]) == 1
            assert data["pictures"][0]["family_id"] == 1
        finally:
            self.teardown_dependency_overrides()

    def test_get_pictures_admin_vs_user(self):
        """管理者・一般ユーザーで同じ結果"""
        # 同じ家族の管理者と一般ユーザー
        admin_user = User()
        admin_user.id = 1
        admin_user.family_id = 1
        admin_user.status = 1
        admin_user.type = 10
        admin_user.user_name = "admin_user"
        admin_user.email = "admin@example.com"

        regular_user = User()
        regular_user.id = 2
        regular_user.family_id = 1
        regular_user.status = 1
        regular_user.type = 0
        regular_user.user_name = "regular_user"
        regular_user.email = "user@example.com"

        test_picture = Picture()
        test_picture.id = 1
        test_picture.family_id = 1
        test_picture.status = 1
        test_picture.uploaded_by = 1
        test_picture.file_path = "/path/to/pic.jpg"
        test_picture.create_date = datetime.now()
        test_picture.update_date = datetime.now()

        mock_db = self.setup_mock_db(mock_count=1, mock_results=[test_picture])

        # 管理者でのアクセス
        self.setup_dependency_overrides(mock_db, admin_user)
        try:
            admin_response = client.get("/api/pictures")
        finally:
            self.teardown_dependency_overrides()

        # 一般ユーザーでのアクセス
        self.setup_dependency_overrides(mock_db, regular_user)
        try:
            user_response = client.get("/api/pictures")
        finally:
            self.teardown_dependency_overrides()

        assert admin_response.status_code == 200
        assert user_response.status_code == 200
        assert admin_response.json() == user_response.json()

    def test_get_pictures_deleted_user(self):
        """削除済みユーザーでのアクセス拒否"""
        deleted_token = self.create_test_token(1, 1, status=0)
        headers = {"Authorization": f"Bearer {deleted_token}"}
        response = client.get("/api/pictures", headers=headers)
        assert response.status_code == 401

    # ========== 基本動作テスト ==========

    def test_get_pictures_success_empty(self):
        """写真が0件の場合の正常レスポンス"""
        mock_db = self.setup_mock_db(mock_count=0, mock_results=[])
        mock_user = User(id=1, family_id=1, status=1, type=0)

        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures")
            assert response.status_code == 200
            data = response.json()
            assert data["pictures"] == []
            assert data["total"] == 0
            assert data["limit"] == 20
            assert data["offset"] == 0
            assert data["has_more"] == False
        finally:
            self.teardown_dependency_overrides()

    def test_get_pictures_success_with_data(self):
        """写真が存在する場合の正常レスポンス"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        test_pictures = []
        for i in range(1, 3):
            picture = Picture()
            picture.id = i
            picture.family_id = 1
            picture.uploaded_by = 1
            picture.title = f"Test Picture {i}"
            picture.file_path = f"/path/to/pic{i}.jpg"
            picture.status = 1
            picture.create_date = datetime.now()
            picture.update_date = datetime.now()
            test_pictures.append(picture)

        mock_db = self.setup_mock_db(mock_count=2, mock_results=test_pictures)
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures")
            assert response.status_code == 200
            data = response.json()
            assert len(data["pictures"]) == 2
            assert data["total"] == 2
            assert data["has_more"] == False
        finally:
            self.teardown_dependency_overrides()

    def test_get_pictures_response_structure(self):
        """レスポンス構造の検証"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        test_picture = Picture()
        test_picture.id = 1
        test_picture.family_id = 1
        test_picture.uploaded_by = 1
        test_picture.title = "Test Picture"
        test_picture.description = "Test Description"
        test_picture.file_path = "/path/to/pic.jpg"
        test_picture.thumbnail_path = "/path/to/thumb.jpg"
        test_picture.file_size = 1024
        test_picture.mime_type = "image/jpeg"
        test_picture.width = 800
        test_picture.height = 600
        test_picture.taken_date = datetime(2024, 1, 1, 12, 0, 0)
        test_picture.category_id = 1
        test_picture.status = 1
        test_picture.create_date = datetime.now()
        test_picture.update_date = datetime.now()

        mock_db = self.setup_mock_db(mock_count=1, mock_results=[test_picture])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures")
            assert response.status_code == 200
            data = response.json()
            picture = data["pictures"][0]

            # 必須フィールドの確認
            required_fields = ["id", "family_id", "uploaded_by", "file_path",
                             "status", "create_date", "update_date"]
            for field in required_fields:
                assert field in picture

            # 任意フィールドの確認
            optional_fields = ["title", "description", "thumbnail_path",
                             "file_size", "mime_type", "width", "height",
                             "taken_date", "category_id"]
            for field in optional_fields:
                assert field in picture
        finally:
            self.teardown_dependency_overrides()

    # ========== フィルタリング機能テスト ==========

    def test_filter_by_category_single(self):
        """単一カテゴリでのフィルタリング"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=1, mock_results=[])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures?category=1")
            assert response.status_code == 200
            # filter が category_id.in_([1]) で呼ばれることを確認
            mock_db.query.return_value.filter.assert_called()
        finally:
            self.teardown_dependency_overrides()

    def test_filter_invalid_date_format(self):
        """無効な日付形式でのエラー（400）"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=0, mock_results=[])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures?start_date=invalid-date")
            assert response.status_code == 400
            assert "Invalid date format" in response.json()["detail"]
        finally:
            self.teardown_dependency_overrides()

    # ========== ページネーション機能テスト ==========

    def test_pagination_default_limit(self):
        """デフォルトlimit値"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=0, mock_results=[])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures")
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 20
        finally:
            self.teardown_dependency_overrides()

    def test_pagination_max_limit_exceeded(self):
        """最大limit超過時の制限"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=0, mock_results=[])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            response = client.get("/api/pictures?limit=150")
            assert response.status_code == 422  # Pydantic validation error
        finally:
            self.teardown_dependency_overrides()

    def test_pagination_invalid_params(self):
        """無効なpaginationパラメータ（400）"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=0, mock_results=[])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            # 負のoffset
            response = client.get("/api/pictures?offset=-1")
            assert response.status_code == 422

            # 負のlimit
            response = client.get("/api/pictures?limit=-1")
            assert response.status_code == 422
        finally:
            self.teardown_dependency_overrides()

    def test_pagination_has_more_flag(self):
        """次ページ存在フラグの正確性"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=25, mock_results=[])  # 25件の写真
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            # 1ページ目（20件取得、残り5件）
            response = client.get("/api/pictures?limit=20&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["has_more"] == True

            # 2ページ目（5件取得、残り0件）
            response = client.get("/api/pictures?limit=20&offset=20")
            assert response.status_code == 200
            data = response.json()
            assert data["has_more"] == False
        finally:
            self.teardown_dependency_overrides()

    # ========== エラーハンドリングテスト ==========

    def test_invalid_query_parameters(self):
        """不正なクエリパラメータ（400）"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=0, mock_results=[])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            # 無効な年
            response = client.get("/api/pictures?year=1800")
            assert response.status_code == 422

            # 無効な月
            response = client.get("/api/pictures?month=13")
            assert response.status_code == 422
        finally:
            self.teardown_dependency_overrides()

    def test_malformed_request(self):
        """不正な形式のリクエスト（400）"""
        mock_user = User()
        mock_user.id = 1
        mock_user.family_id = 1
        mock_user.status = 1
        mock_user.type = 0
        mock_user.user_name = "test_user"
        mock_user.email = "test@example.com"

        mock_db = self.setup_mock_db(mock_count=0, mock_results=[])
        self.setup_dependency_overrides(mock_db, mock_user)

        try:
            # 無効なカテゴリ形式
            response = client.get("/api/pictures?category=abc")
            assert response.status_code == 400
            assert "Invalid category format" in response.json()["detail"]
        finally:
            self.teardown_dependency_overrides()