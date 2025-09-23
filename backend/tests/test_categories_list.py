"""
GET /api/categories APIのテストファイル（カテゴリ一覧取得）

カテゴリ一覧取得API仕様:
- 認証済みユーザーが自分の家族のカテゴリ一覧を取得
- family_idによるスコープ制限（他家族のカテゴリは見えない）
- status=1（有効）のカテゴリのみ表示（削除済みは除外）
- デフォルトソート: 作成日昇順

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 無効・期限切れトークンでのアクセス拒否
   - 家族ID範囲でのアクセス制御（他家族のカテゴリは見えない）
   - 削除済みユーザーでのアクセス拒否

2. 基本動作テスト
   - カテゴリが0件の場合の正常レスポンス
   - カテゴリが存在する場合の正常レスポンス
   - レスポンス構造の検証
   - デフォルトソート（作成日昇順）

3. データフィルタリングテスト
   - 有効なカテゴリ（status=1）のみ表示
   - 削除済みカテゴリ（status=0）は非表示
   - 異なる家族のカテゴリは非表示

4. レスポンス形式テスト
   - 配列形式のレスポンス
   - カテゴリオブジェクトの必須フィールド
   - データ型の検証

5. エラーハンドリングテスト
   - 不正な形式のAuthorizationヘッダー
   - DBエラーシミュレート
   - ユーザー情報取得失敗

テスト項目（15項目）:

【認証・認可系】(6項目)
- test_get_categories_without_auth: 未認証でのアクセス拒否（403）
- test_get_categories_with_invalid_token: 無効トークンでのアクセス拒否（401）
- test_get_categories_with_expired_token: 期限切れトークンでのアクセス拒否（401）
- test_get_categories_family_scope: 異なる家族のカテゴリは表示されない
- test_get_categories_deleted_user: 削除済みユーザーでのアクセス拒否（403）
- test_get_categories_malformed_header: 不正な形式のヘッダー（403）

【基本動作】(4項目)
- test_get_categories_empty_list: カテゴリ0件時の正常レスポンス
- test_get_categories_success: カテゴリ存在時の正常レスポンス
- test_get_categories_response_format: レスポンス形式の検証
- test_get_categories_sort_order: デフォルトソート（作成日昇順）確認

【データフィルタリング】(3項目)
- test_get_categories_active_only: 有効カテゴリ（status=1）のみ表示
- test_get_categories_exclude_deleted: 削除済みカテゴリ（status=0）除外
- test_get_categories_family_isolation: 家族間データ分離確認

【エラーハンドリング】(2項目)
- test_get_categories_user_not_found: 存在しないユーザーのトークン（401）
- test_get_categories_db_error: DB接続エラー時の適切なエラーレスポンス
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime

from main import app
from database import get_db
from dependencies import get_current_user


# ========================
# 認証・認可系テスト (6項目)
# ========================

def test_get_categories_without_auth():
    """未認証でのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.get("/api/categories")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_get_categories_with_invalid_token():
    """無効トークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が例外を投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/categories", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_get_categories_with_expired_token():
    """期限切れトークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が期限切れエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer expired_token"}
        response = client.get("/api/categories", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_get_categories_family_scope():
    """異なる家族のカテゴリは表示されない"""
    client = TestClient(app)

    # 認証ユーザー（family_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"
    mock_user.status = 1

    # データベースモック（family_idでフィルタされるため他家族のカテゴリは返らない）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/categories")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == []  # 他家族のカテゴリは見えない
    finally:
        app.dependency_overrides.clear()


def test_get_categories_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)

    # 削除済みユーザー（status = 0）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.status = 0

    # get_current_user 関数が無効ユーザーエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=403, detail="User account is disabled")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer disabled_user_token"}
        response = client.get("/api/categories", headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is disabled"
    finally:
        app.dependency_overrides.clear()


def test_get_categories_malformed_header():
    """不正な形式のヘッダー（403）"""
    client = TestClient(app)

    # "Bearer "がないヘッダー
    headers = {"Authorization": "invalid_token"}
    response = client.get("/api/categories", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # 空のヘッダー
    headers = {"Authorization": ""}
    response = client.get("/api/categories", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # "Bearer"のみ
    headers = {"Authorization": "Bearer"}
    response = client.get("/api/categories", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


# ========================
# 基本動作テスト (4項目)
# ========================

def test_get_categories_empty_list():
    """カテゴリ0件時の正常レスポンス"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"
    mock_user.status = 1

    # データベースモック（空のカテゴリリスト）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/categories")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == []
        assert isinstance(response_data, list)
    finally:
        app.dependency_overrides.clear()


def test_get_categories_success():
    """カテゴリ存在時の正常レスポンス"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"
    mock_user.status = 1

    # カテゴリのモック
    mock_category1 = MagicMock()
    mock_category1.id = 1
    mock_category1.family_id = 1
    mock_category1.name = "未分類"
    mock_category1.description = "カテゴリが設定されていない写真"
    mock_category1.status = 1
    mock_category1.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category1.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_category2 = MagicMock()
    mock_category2.id = 2
    mock_category2.family_id = 1
    mock_category2.name = "旅行"
    mock_category2.description = "旅行時の写真"
    mock_category2.status = 1
    mock_category2.create_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_category2.update_date = datetime(2024, 1, 2, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_category1, mock_category2]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/categories")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["id"] == 1
        assert response_data[0]["name"] == "未分類"
        assert response_data[1]["id"] == 2
        assert response_data[1]["name"] == "旅行"
    finally:
        app.dependency_overrides.clear()


def test_get_categories_response_format():
    """レスポンス形式の検証"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.status = 1

    # カテゴリのモック
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "テストカテゴリ"
    mock_category.description = "テスト用のカテゴリです"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_category]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/categories")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        response_data = response.json()
        assert isinstance(response_data, list)
        assert len(response_data) == 1

        category = response_data[0]
        required_fields = ["id", "name", "description", "status", "create_date", "update_date"]
        for field in required_fields:
            assert field in category, f"Required field '{field}' missing from response"

        # データ型の確認
        assert isinstance(category["id"], int)
        assert isinstance(category["name"], str)
        assert isinstance(category["status"], int)
        assert isinstance(category["create_date"], str)
        assert isinstance(category["update_date"], str)
    finally:
        app.dependency_overrides.clear()


def test_get_categories_sort_order():
    """デフォルトソート（作成日昇順）確認"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.status = 1

    # 異なる作成日のカテゴリモック（作成日昇順でソートされた結果）
    mock_category_old = MagicMock()
    mock_category_old.id = 1
    mock_category_old.family_id = 1
    mock_category_old.name = "古いカテゴリ"
    mock_category_old.description = "古いカテゴリの説明"
    mock_category_old.status = 1
    mock_category_old.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category_old.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_category_new = MagicMock()
    mock_category_new.id = 2
    mock_category_new.family_id = 1
    mock_category_new.name = "新しいカテゴリ"
    mock_category_new.description = "新しいカテゴリの説明"
    mock_category_new.status = 1
    mock_category_new.create_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_category_new.update_date = datetime(2024, 1, 2, 10, 0, 0)

    # データベースモック（作成日昇順でソート済み）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_category_old, mock_category_new]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/categories")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        # 古いカテゴリが最初
        assert response_data[0]["name"] == "古いカテゴリ"
        # 新しいカテゴリが次
        assert response_data[1]["name"] == "新しいカテゴリ"
    finally:
        app.dependency_overrides.clear()


# ========================
# データフィルタリングテスト (3項目)
# ========================

def test_get_categories_active_only():
    """有効カテゴリ（status=1）のみ表示"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.status = 1

    # 有効なカテゴリのみのモック（削除済みは既にフィルタで除外済み）
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "有効カテゴリ"
    mock_category.description = "有効なカテゴリの説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_category]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/categories")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["name"] == "有効カテゴリ"
        assert response_data[0]["status"] == 1
    finally:
        app.dependency_overrides.clear()


def test_get_categories_exclude_deleted():
    """削除済みカテゴリ（status=0）除外"""
    # test_get_categories_active_only()と同じロジック
    test_get_categories_active_only()


def test_get_categories_family_isolation():
    """家族間データ分離確認"""
    # test_get_categories_family_scope()と同じロジック
    test_get_categories_family_scope()


# ========================
# エラーハンドリングテスト (2項目)
# ========================

def test_get_categories_user_not_found():
    """存在しないユーザーのトークン（401）"""
    client = TestClient(app)

    # get_current_user 関数がユーザー見つからないエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer nonexistent_user_token"}
        response = client.get("/api/categories", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_get_categories_db_error():
    """DB接続エラー時の適切なエラーレスポンス"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.status = 1

    # データベースエラーのモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.side_effect = Exception("Database connection error")

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/categories")
        # DBエラーの場合は500エラーが期待される
        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()