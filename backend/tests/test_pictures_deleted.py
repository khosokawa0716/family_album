"""
GET /api/pictures/deleted APIのテストファイル（削除済み写真一覧取得）

削除済み写真一覧取得API仕様:
- 管理者ユーザー（type=10）のみアクセス可能
- 自家族の削除済み写真のみ取得（family_id == current_user.family_id かつ status=0）
- 削除日時（deleted_at）の降順でソート
- レスポンス形式は既存の GET /api/pictures と同様
- ページネーション対応（limit/offset）

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 管理者以外のアクセス拒否（type != 10）
   - 管理者ユーザーのアクセス許可
   - 家族ID範囲でのアクセス制御

2. 基本動作テスト
   - 削除済み写真が0件の場合の正常レスポンス
   - 削除済み写真が存在する場合の正常レスポンス
   - レスポンス構造の検証
   - deleted_at降順ソートの確認

3. データフィルタリングテスト
   - 削除済み写真（status=0）のみ表示
   - 有効な写真（status=1）は非表示
   - 異なる家族の削除済み写真は非表示

4. ページネーションテスト
   - limit/offset パラメータの動作
   - has_more フラグの正確性

テスト項目:

【認証・認可系】
- test_get_deleted_pictures_without_auth: 未認証でのアクセス拒否（403）
- test_get_deleted_pictures_non_admin: 管理者以外のアクセス拒否（403）
- test_get_deleted_pictures_admin_success: 管理者のアクセス成功
- test_get_deleted_pictures_family_scope: 異なる家族の削除済み写真は表示されない

【基本動作】
- test_get_deleted_pictures_empty_list: 削除済み写真0件時の正常レスポンス
- test_get_deleted_pictures_success: 削除済み写真存在時の正常レスポンス
- test_get_deleted_pictures_response_format: レスポンス形式の検証
- test_get_deleted_pictures_sort_order: deleted_at降順ソート確認

【データフィルタリング】
- test_get_deleted_pictures_deleted_only: 削除済み写真（status=0）のみ表示
- test_get_deleted_pictures_exclude_active: 有効な写真（status=1）除外

【ページネーション】
- test_get_deleted_pictures_pagination: limit/offset パラメータの動作
- test_get_deleted_pictures_has_more: has_more フラグの正確性
"""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime

from main import app
from database import get_db
from dependencies import get_current_user


# ========================
# 認証・認可系テスト
# ========================

def test_get_deleted_pictures_without_auth():
    """未認証でのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.get("/api/pictures/deleted")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_get_deleted_pictures_non_admin():
    """管理者以外のアクセス拒否（403）"""
    client = TestClient(app)

    # 一般ユーザー（type=1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 1
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"
    finally:
        app.dependency_overrides.clear()


def test_get_deleted_pictures_admin_success():
    """管理者のアクセス成功"""
    client = TestClient(app)

    # 管理者ユーザー（type=10）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（空のリスト）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 0
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        assert "pictures" in response_data
        assert "total" in response_data
        assert response_data["total"] == 0
    finally:
        app.dependency_overrides.clear()


def test_get_deleted_pictures_family_scope():
    """異なる家族の削除済み写真は表示されない"""
    client = TestClient(app)

    # 管理者ユーザー（family_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（family_idでフィルタされるため他家族の写真は返らない）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 0
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["pictures"] == []  # 他家族の削除済み写真は見えない
    finally:
        app.dependency_overrides.clear()


# ========================
# 基本動作テスト
# ========================

def test_get_deleted_pictures_empty_list():
    """削除済み写真0件時の正常レスポンス"""
    client = TestClient(app)

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（空のリスト）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 0
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["pictures"] == []
        assert response_data["total"] == 0
        assert response_data["limit"] == 20
        assert response_data["offset"] == 0
        assert response_data["has_more"] == False
    finally:
        app.dependency_overrides.clear()


@patch('routers.pictures.create_signed_url')
def test_get_deleted_pictures_success(mock_create_signed_url):
    """削除済み写真存在時の正常レスポンス"""
    client = TestClient(app)

    # 署名付きURL生成のモック
    mock_create_signed_url.return_value = "https://example.com/signed_url"

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除済み写真のモック
    mock_picture1 = MagicMock()
    mock_picture1.id = 1
    mock_picture1.family_id = 1
    mock_picture1.uploaded_by = 1
    mock_picture1.title = "削除済み写真1"
    mock_picture1.description = "テスト用の削除済み写真"
    mock_picture1.file_path = "photos/test1.jpg"
    mock_picture1.thumbnail_path = "thumbnails/thumb_test1.jpg"
    mock_picture1.file_size = 1024000
    mock_picture1.mime_type = "image/jpeg"
    mock_picture1.width = 1920
    mock_picture1.height = 1080
    mock_picture1.taken_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture1.category_id = 1
    mock_picture1.status = 0
    mock_picture1.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture1.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture1.deleted_at = datetime(2024, 1, 2, 10, 0, 0)

    mock_picture2 = MagicMock()
    mock_picture2.id = 2
    mock_picture2.family_id = 1
    mock_picture2.uploaded_by = 1
    mock_picture2.title = "削除済み写真2"
    mock_picture2.description = None
    mock_picture2.file_path = "photos/test2.jpg"
    mock_picture2.thumbnail_path = "thumbnails/thumb_test2.jpg"
    mock_picture2.file_size = 2048000
    mock_picture2.mime_type = "image/jpeg"
    mock_picture2.width = 1920
    mock_picture2.height = 1080
    mock_picture2.taken_date = datetime(2024, 1, 3, 10, 0, 0)
    mock_picture2.category_id = None
    mock_picture2.status = 0
    mock_picture2.create_date = datetime(2024, 1, 3, 10, 0, 0)
    mock_picture2.update_date = datetime(2024, 1, 4, 10, 0, 0)
    mock_picture2.deleted_at = datetime(2024, 1, 4, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 2
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        mock_picture2, mock_picture1  # deleted_at降順
    ]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["pictures"]) == 2
        assert response_data["pictures"][0]["id"] == 2
        assert response_data["pictures"][0]["title"] == "削除済み写真2"
        assert response_data["pictures"][1]["id"] == 1
        assert response_data["pictures"][1]["title"] == "削除済み写真1"
        assert response_data["total"] == 2
    finally:
        app.dependency_overrides.clear()


@patch('routers.pictures.create_signed_url')
def test_get_deleted_pictures_response_format(mock_create_signed_url):
    """レスポンス形式の検証"""
    client = TestClient(app)

    # 署名付きURL生成のモック
    mock_create_signed_url.return_value = "https://example.com/signed_url"

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除済み写真のモック
    mock_picture = MagicMock()
    mock_picture.id = 1
    mock_picture.family_id = 1
    mock_picture.uploaded_by = 1
    mock_picture.title = "テスト写真"
    mock_picture.description = "テスト用"
    mock_picture.file_path = "photos/test.jpg"
    mock_picture.thumbnail_path = "thumbnails/thumb_test.jpg"
    mock_picture.file_size = 1024000
    mock_picture.mime_type = "image/jpeg"
    mock_picture.width = 1920
    mock_picture.height = 1080
    mock_picture.taken_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture.category_id = 1
    mock_picture.status = 0
    mock_picture.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture.deleted_at = datetime(2024, 1, 2, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 1
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_picture]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        response_data = response.json()

        # トップレベルのフィールド確認
        assert "pictures" in response_data
        assert "total" in response_data
        assert "limit" in response_data
        assert "offset" in response_data
        assert "has_more" in response_data

        # 写真オブジェクトのフィールド確認
        picture = response_data["pictures"][0]
        required_fields = ["id", "family_id", "uploaded_by", "title", "description",
                          "file_path", "thumbnail_path", "file_size", "mime_type",
                          "width", "height", "taken_date", "category_id", "status",
                          "create_date", "update_date"]
        for field in required_fields:
            assert field in picture, f"Required field '{field}' missing from response"

        # データ型の確認
        assert isinstance(picture["id"], int)
        assert isinstance(picture["status"], int)
        assert picture["status"] == 0  # 削除済み
    finally:
        app.dependency_overrides.clear()


@patch('routers.pictures.create_signed_url')
def test_get_deleted_pictures_sort_order(mock_create_signed_url):
    """deleted_at降順ソート確認"""
    client = TestClient(app)

    # 署名付きURL生成のモック
    mock_create_signed_url.return_value = "https://example.com/signed_url"

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 異なる削除日時の写真モック（deleted_at降順でソート済み）
    mock_picture_new = MagicMock()
    mock_picture_new.id = 2
    mock_picture_new.family_id = 1
    mock_picture_new.uploaded_by = 1
    mock_picture_new.title = "新しく削除された写真"
    mock_picture_new.description = None
    mock_picture_new.file_path = "photos/new.jpg"
    mock_picture_new.thumbnail_path = "thumbnails/thumb_new.jpg"
    mock_picture_new.file_size = 1024000
    mock_picture_new.mime_type = "image/jpeg"
    mock_picture_new.width = 1920
    mock_picture_new.height = 1080
    mock_picture_new.taken_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture_new.category_id = None
    mock_picture_new.status = 0
    mock_picture_new.create_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture_new.update_date = datetime(2024, 1, 3, 10, 0, 0)
    mock_picture_new.deleted_at = datetime(2024, 1, 3, 10, 0, 0)

    mock_picture_old = MagicMock()
    mock_picture_old.id = 1
    mock_picture_old.family_id = 1
    mock_picture_old.uploaded_by = 1
    mock_picture_old.title = "古く削除された写真"
    mock_picture_old.description = None
    mock_picture_old.file_path = "photos/old.jpg"
    mock_picture_old.thumbnail_path = "thumbnails/thumb_old.jpg"
    mock_picture_old.file_size = 1024000
    mock_picture_old.mime_type = "image/jpeg"
    mock_picture_old.width = 1920
    mock_picture_old.height = 1080
    mock_picture_old.taken_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture_old.category_id = None
    mock_picture_old.status = 0
    mock_picture_old.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture_old.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture_old.deleted_at = datetime(2024, 1, 2, 10, 0, 0)

    # データベースモック（deleted_at降順でソート済み）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 2
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        mock_picture_new, mock_picture_old
    ]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["pictures"]) == 2
        # 新しく削除された写真が最初
        assert response_data["pictures"][0]["title"] == "新しく削除された写真"
        # 古く削除された写真が次
        assert response_data["pictures"][1]["title"] == "古く削除された写真"
    finally:
        app.dependency_overrides.clear()


# ========================
# データフィルタリングテスト
# ========================

@patch('routers.pictures.create_signed_url')
def test_get_deleted_pictures_deleted_only(mock_create_signed_url):
    """削除済み写真（status=0）のみ表示"""
    client = TestClient(app)

    # 署名付きURL生成のモック
    mock_create_signed_url.return_value = "https://example.com/signed_url"

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除済み写真のみのモック
    mock_picture = MagicMock()
    mock_picture.id = 1
    mock_picture.family_id = 1
    mock_picture.uploaded_by = 1
    mock_picture.title = "削除済み写真"
    mock_picture.description = None
    mock_picture.file_path = "photos/deleted.jpg"
    mock_picture.thumbnail_path = "thumbnails/thumb_deleted.jpg"
    mock_picture.file_size = 1024000
    mock_picture.mime_type = "image/jpeg"
    mock_picture.width = 1920
    mock_picture.height = 1080
    mock_picture.taken_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture.category_id = None
    mock_picture.status = 0
    mock_picture.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture.deleted_at = datetime(2024, 1, 2, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 1
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_picture]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["pictures"]) == 1
        assert response_data["pictures"][0]["status"] == 0
    finally:
        app.dependency_overrides.clear()


def test_get_deleted_pictures_exclude_active():
    """有効な写真（status=1）除外"""
    client = TestClient(app)

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（status=0のフィルタにより有効な写真は除外済み）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 0
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        # 有効な写真は含まれない
        assert response_data["pictures"] == []
    finally:
        app.dependency_overrides.clear()


# ========================
# ページネーションテスト
# ========================

@patch('routers.pictures.create_signed_url')
def test_get_deleted_pictures_pagination(mock_create_signed_url):
    """limit/offset パラメータの動作"""
    client = TestClient(app)

    # 署名付きURL生成のモック
    mock_create_signed_url.return_value = "https://example.com/signed_url"

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除済み写真のモック
    mock_picture = MagicMock()
    mock_picture.id = 2
    mock_picture.family_id = 1
    mock_picture.uploaded_by = 1
    mock_picture.title = "写真2"
    mock_picture.description = None
    mock_picture.file_path = "photos/pic2.jpg"
    mock_picture.thumbnail_path = "thumbnails/thumb_pic2.jpg"
    mock_picture.file_size = 1024000
    mock_picture.mime_type = "image/jpeg"
    mock_picture.width = 1920
    mock_picture.height = 1080
    mock_picture.taken_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture.category_id = None
    mock_picture.status = 0
    mock_picture.create_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture.update_date = datetime(2024, 1, 3, 10, 0, 0)
    mock_picture.deleted_at = datetime(2024, 1, 3, 10, 0, 0)

    # データベースモック（総数3件、offset=1, limit=1で2番目の写真を返す）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 3
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_picture]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted?limit=1&offset=1")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["pictures"]) == 1
        assert response_data["total"] == 3
        assert response_data["limit"] == 1
        assert response_data["offset"] == 1
        assert response_data["has_more"] == True  # (1 + 1) < 3
    finally:
        app.dependency_overrides.clear()


@patch('routers.pictures.create_signed_url')
def test_get_deleted_pictures_has_more(mock_create_signed_url):
    """has_more フラグの正確性"""
    client = TestClient(app)

    # 署名付きURL生成のモック
    mock_create_signed_url.return_value = "https://example.com/signed_url"

    # 管理者ユーザー
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除済み写真のモック
    mock_picture1 = MagicMock()
    mock_picture1.id = 1
    mock_picture1.family_id = 1
    mock_picture1.uploaded_by = 1
    mock_picture1.title = "写真1"
    mock_picture1.description = None
    mock_picture1.file_path = "photos/pic1.jpg"
    mock_picture1.thumbnail_path = "thumbnails/thumb_pic1.jpg"
    mock_picture1.file_size = 1024000
    mock_picture1.mime_type = "image/jpeg"
    mock_picture1.width = 1920
    mock_picture1.height = 1080
    mock_picture1.taken_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture1.category_id = None
    mock_picture1.status = 0
    mock_picture1.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_picture1.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_picture1.deleted_at = datetime(2024, 1, 2, 10, 0, 0)

    # データベースモック（総数1件、offset=0, limit=20で全件取得）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 1
    mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_picture1]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/pictures/deleted")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["has_more"] == False  # (0 + 20) >= 1
    finally:
        app.dependency_overrides.clear()
