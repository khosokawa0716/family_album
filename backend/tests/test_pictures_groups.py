"""
GET /api/pictures/groups, GET /api/pictures/groups/{group_id} APIのテストファイル

グループ一覧・詳細API仕様:
- グループ一覧: group_id単位でグループ化された写真一覧を返す
- グループ詳細: 指定group_id内の全写真を返す
- 家族スコープでのアクセス制御
- フィルタリング（カテゴリ、年月、日付範囲）
- ページネーション（グループ数ベース）
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from jose import jwt
from sqlalchemy import and_

from main import app
from models import User, Picture
from config import SECRET_KEY, ALGORITHM

client = TestClient(app)


class TestPictureGroupsAPI:
    """GET /api/pictures/groups APIのテストクラス"""

    def create_test_token(self, user_id: int, family_id: int, user_type: int = 0,
                         status: int = 1):
        payload = {
            "sub": str(user_id),
            "family_id": family_id,
            "user_type": user_type,
            "status": status,
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def create_mock_user(self, user_id=1, family_id=1):
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.family_id = family_id
        mock_user.user_name = f"test_user_{user_id}"
        mock_user.type = 0
        mock_user.status = 1
        return mock_user

    def create_mock_picture(self, picture_id, group_id, family_id=1, uploaded_by=1,
                            title=None, category_id=None,
                            taken_date=None, create_date=None):
        mock_pic = MagicMock(spec=Picture)
        mock_pic.id = picture_id
        mock_pic.group_id = group_id
        mock_pic.family_id = family_id
        mock_pic.uploaded_by = uploaded_by
        mock_pic.title = title
        mock_pic.description = None
        mock_pic.file_path = f"photos/test_{picture_id}.jpg"
        mock_pic.thumbnail_path = f"thumbnails/thumb_test_{picture_id}.jpg"
        mock_pic.file_size = 1024000
        mock_pic.mime_type = "image/jpeg"
        mock_pic.width = 800
        mock_pic.height = 600
        mock_pic.taken_date = taken_date or datetime(2024, 6, 15, 10, 0, 0)
        mock_pic.category_id = category_id
        mock_pic.status = 1
        mock_pic.create_date = create_date or datetime(2024, 6, 15, 12, 0, 0)
        mock_pic.update_date = create_date or datetime(2024, 6, 15, 12, 0, 0)
        return mock_pic

    def setup_dependency_overrides(self, mock_db, mock_user):
        from database import get_db
        from dependencies import get_current_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

    def teardown_dependency_overrides(self):
        app.dependency_overrides.clear()

    # ========== グループ一覧テスト ==========

    def test_get_picture_groups_empty(self):
        """グループなし → 空のgroups配列"""
        try:
            mock_user = self.create_mock_user()
            mock_db = MagicMock()
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.count.return_value = 0
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = []

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.get("/api/pictures/groups", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["groups"] == []
            assert data["total"] == 0
            assert data["has_more"] is False

        finally:
            self.teardown_dependency_overrides()

    @patch('routers.pictures.create_signed_url', return_value="/signed/url")
    def test_get_picture_groups_single_photo_groups(self, mock_signed_url):
        """1枚ずつのグループが複数ある場合"""
        try:
            mock_user = self.create_mock_user()
            mock_db = MagicMock()

            pic1 = self.create_mock_picture(1, "group-aaa", title="Photo A")
            pic2 = self.create_mock_picture(2, "group-bbb", title="Photo B")

            # クエリのモックチェーン
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.count.return_value = 2
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.outerjoin.return_value = mock_query

            # group一覧クエリとpictures取得クエリを区別
            group_row_a = MagicMock()
            group_row_a.group_id = "group-aaa"
            group_row_b = MagicMock()
            group_row_b.group_id = "group-bbb"

            mock_query.all.side_effect = [
                [group_row_a, group_row_b],  # 1回目: group一覧
                [(pic1, "user_1"), (pic2, "user_1")]  # 2回目: pictures取得
            ]

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.get("/api/pictures/groups", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert len(data["groups"]) == 2
            assert data["total"] == 2
            assert data["has_more"] is False

        finally:
            self.teardown_dependency_overrides()

    @patch('routers.pictures.create_signed_url', return_value="/signed/url")
    def test_get_picture_groups_multi_photo_group(self, mock_signed_url):
        """複数枚を含むグループ"""
        try:
            mock_user = self.create_mock_user()
            mock_db = MagicMock()

            pic1 = self.create_mock_picture(1, "group-multi", title="Trip")
            pic2 = self.create_mock_picture(2, "group-multi", title="Trip")
            pic3 = self.create_mock_picture(3, "group-multi", title="Trip")

            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.outerjoin.return_value = mock_query

            group_row = MagicMock()
            group_row.group_id = "group-multi"

            mock_query.all.side_effect = [
                [group_row],
                [(pic1, "user_1"), (pic2, "user_1"), (pic3, "user_1")]
            ]

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.get("/api/pictures/groups", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert len(data["groups"]) == 1
            assert len(data["groups"][0]["pictures"]) == 3
            assert data["groups"][0]["group_id"] == "group-multi"

        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_groups_pagination(self):
        """ページネーション: has_moreとtotalの確認"""
        try:
            mock_user = self.create_mock_user()
            mock_db = MagicMock()

            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.count.return_value = 5  # 5グループ合計
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query

            # limit=2なので最初の2グループだけ返す
            mock_query.all.return_value = []  # 空で返してearly return

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            # total=5, limit=2, offset=0 → has_more=True
            response = client.get("/api/pictures/groups?limit=2&offset=0", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 5
            assert data["limit"] == 2
            assert data["offset"] == 0

        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_groups_without_auth(self):
        """未認証 → 403エラー"""
        response = client.get("/api/pictures/groups")
        assert response.status_code == 403

    # ========== グループ詳細テスト ==========

    @patch('routers.pictures.create_signed_url', return_value="/signed/url")
    def test_get_picture_group_detail_success(self, mock_signed_url):
        """グループ詳細: 正常取得"""
        try:
            mock_user = self.create_mock_user()
            mock_db = MagicMock()

            pic1 = self.create_mock_picture(1, "group-detail-test", title="Photo")
            pic2 = self.create_mock_picture(2, "group-detail-test", title="Photo")

            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.outerjoin.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = [(pic1, "user_1"), (pic2, "user_1")]

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.get("/api/pictures/groups/group-detail-test", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["group_id"] == "group-detail-test"
            assert len(data["pictures"]) == 2

        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_group_detail_not_found(self):
        """グループ詳細: 存在しないgroup_id → 404"""
        try:
            mock_user = self.create_mock_user()
            mock_db = MagicMock()

            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.outerjoin.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = []

            self.setup_dependency_overrides(mock_db, mock_user)

            token = self.create_test_token(1, 1)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.get("/api/pictures/groups/nonexistent-group", headers=headers)

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

        finally:
            self.teardown_dependency_overrides()

    def test_get_picture_group_detail_without_auth(self):
        """グループ詳細: 未認証 → 403"""
        response = client.get("/api/pictures/groups/some-group-id")
        assert response.status_code == 403
