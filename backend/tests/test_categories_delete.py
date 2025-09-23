"""
DELETE /api/categories/:id APIのテストファイル（カテゴリ削除・管理者のみ）

カテゴリ削除API仕様:
- 管理者権限（type=10）を持つ認証済みユーザーのみがカテゴリを削除可能
- family_idによるスコープ制限（他家族のカテゴリは削除不可）
- 論理削除（status=0に更新）
- カテゴリが存在しない場合は404エラー
- 既に削除済みの場合は404エラー

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 無効・期限切れトークンでのアクセス拒否
   - 管理者権限のないユーザーのアクセス拒否（type!=10）
   - 家族ID範囲でのアクセス制御（他家族のカテゴリは削除不可）
   - 削除済みユーザーでのアクセス拒否
   - 管理者権限を持つ有効ユーザーでのアクセス許可

2. 基本動作テスト
   - 有効なカテゴリの正常削除
   - レスポンス構造の検証
   - 削除後の状態確認（status=0）

3. データバリデーションテスト
   - 存在しないカテゴリIDでの404エラー
   - 既に削除済みカテゴリでの404エラー
   - 無効なID形式での422エラー
   - 異なる家族のカテゴリ削除時の404エラー

4. レスポンス形式テスト
   - 成功時のレスポンス構造
   - エラー時のレスポンス構造
   - Content-Typeの検証

5. エラーハンドリングテスト
   - 不正な形式のAuthorizationヘッダー
   - DBエラーシミュレート
   - ユーザー情報取得失敗

テスト項目（19項目）:

【認証・認可系】(8項目)
- test_delete_category_without_auth: 未認証でのアクセス拒否（403）
- test_delete_category_with_invalid_token: 無効トークンでのアクセス拒否（401）
- test_delete_category_with_expired_token: 期限切れトークンでのアクセス拒否（401）
- test_delete_category_non_admin_user: 管理者権限なしユーザーのアクセス拒否（403）
- test_delete_category_admin_user_success: 管理者権限ユーザーでのアクセス許可
- test_delete_category_family_scope: 異なる家族のカテゴリは削除不可（404）
- test_delete_category_deleted_user: 削除済みユーザーでのアクセス拒否（403）
- test_delete_category_malformed_header: 不正な形式のヘッダー（403）

【基本動作】(3項目)
- test_delete_category_success: 有効カテゴリの正常削除
- test_delete_category_response_format: レスポンス形式の検証
- test_delete_category_status_updated: 削除後の状態確認（status=0）

【データバリデーション】(5項目)
- test_delete_category_not_found: 存在しないカテゴリID（404）
- test_delete_category_already_deleted: 既に削除済みカテゴリ（404）
- test_delete_category_invalid_id_format: 無効なID形式（422）
- test_delete_category_negative_id: 負の値のID（422）
- test_delete_category_zero_id: ゼロのID（422）

【エラーハンドリング】(3項目)
- test_delete_category_user_not_found: 存在しないユーザーのトークン（401）
- test_delete_category_db_error: DB接続エラー時の適切なエラーレスポンス
- test_delete_category_concurrent_delete: 同時削除時の競合状態対応
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime

from main import app
from database import get_db
from dependencies import get_current_user


# ========================
# 認証・認可系テスト (8項目)
# ========================

def test_delete_category_without_auth():
    """未認証でのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.delete("/api/categories/1")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_delete_category_with_invalid_token():
    """無効トークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が例外を投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.delete("/api/categories/1", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_delete_category_with_expired_token():
    """期限切れトークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が期限切れエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer expired_token"}
        response = client.delete("/api/categories/1", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_delete_category_non_admin_user():
    """管理者権限なしユーザーのアクセス拒否（403）"""
    client = TestClient(app)

    # 管理者権限のないユーザー（type != 10）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.delete("/api/categories/1")
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"
    finally:
        app.dependency_overrides.clear()


def test_delete_category_admin_user_success():
    """管理者権限ユーザーでのアクセス許可"""
    client = TestClient(app)

    # 管理者権限のあるユーザー（type = 10）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10
    mock_user.status = 1

    # 削除対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "削除対象カテゴリ"
    mock_category.description = "削除対象の説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_category
    mock_db_session.query.return_value = mock_query
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        assert response.status_code == 200
        response_data = response.json()
        assert "message" in response_data
        assert "deleted successfully" in response_data["message"].lower()
        assert response_data["category_id"] == 1
    finally:
        app.dependency_overrides.clear()


def test_delete_category_family_scope():
    """異なる家族のカテゴリは削除不可（404）"""
    client = TestClient(app)

    # 認証ユーザー（family_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（他家族のデータは家族スコープで除外される）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 他家族のデータは除外される
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        assert response.status_code == 404  # 家族スコープ外は「見つからない」として処理
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_delete_category_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)

    # get_current_user 関数が無効ユーザーエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=403, detail="User account is disabled")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer disabled_user_token"}
        response = client.delete("/api/categories/1", headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is disabled"
    finally:
        app.dependency_overrides.clear()


def test_delete_category_malformed_header():
    """不正な形式のヘッダー（403）"""
    client = TestClient(app)

    # "Bearer "がないヘッダー
    headers = {"Authorization": "invalid_token"}
    response = client.delete("/api/categories/1", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # 空のヘッダー
    headers = {"Authorization": ""}
    response = client.delete("/api/categories/1", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # "Bearer"のみ
    headers = {"Authorization": "Bearer"}
    response = client.delete("/api/categories/1", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


# ========================
# 基本動作テスト (3項目)
# ========================

def test_delete_category_success():
    """有効カテゴリの正常削除"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "削除対象カテゴリ"
    mock_category.description = "削除対象の説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_category
    mock_db_session.query.return_value = mock_query
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        assert response.status_code == 200
        response_data = response.json()
        assert "message" in response_data
        assert "successfully" in response_data["message"].lower()
        assert response_data["category_id"] == 1

        # カテゴリのstatusが0に更新されることを確認
        assert mock_category.status == 0
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(mock_category)
    finally:
        app.dependency_overrides.clear()


def test_delete_category_response_format():
    """レスポンス形式の検証"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "テストカテゴリ"
    mock_category.description = "テスト説明"
    mock_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_category
    mock_db_session.query.return_value = mock_query
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        response_data = response.json()
        required_fields = ["message", "category_id"]
        for field in required_fields:
            assert field in response_data, f"Required field '{field}' missing from response"

        # データ型の確認
        assert isinstance(response_data["message"], str)
        assert isinstance(response_data["category_id"], int)
        assert response_data["category_id"] == 1
    finally:
        app.dependency_overrides.clear()


def test_delete_category_status_updated():
    """削除後の状態確認（status=0）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "削除対象カテゴリ"
    mock_category.status = 1
    updated_time = datetime(2024, 1, 2, 15, 30, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_category
    mock_db_session.query.return_value = mock_query
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        # update_dateが更新されることをシミュレート
        obj.update_date = updated_time

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        assert response.status_code == 200

        # カテゴリのstatusが0（削除）に更新されることを確認
        assert mock_category.status == 0

        # update_dateが更新されることを確認
        mock_db_session.refresh.assert_called_once_with(mock_category)
        mock_db_session.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


# ========================
# データバリデーションテスト (5項目)
# ========================

def test_delete_category_not_found():
    """存在しないカテゴリID（404）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（カテゴリが見つからない）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # カテゴリが存在しない
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_delete_category_already_deleted():
    """既に削除済みカテゴリ（404）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除済みカテゴリ（status=0）
    mock_deleted_category = MagicMock()
    mock_deleted_category.id = 1
    mock_deleted_category.family_id = 1
    mock_deleted_category.name = "削除済みカテゴリ"
    mock_deleted_category.status = 0  # 削除済み

    # データベースモック（status=0のカテゴリを返す）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_deleted_category
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        assert response.status_code == 404
        assert "already deleted" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_delete_category_invalid_id_format():
    """無効なID形式（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 文字列のIDでアクセス
        response = client.delete("/api/categories/abc")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_delete_category_negative_id():
    """負の値のID（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 負数のIDでアクセス
        response = client.delete("/api/categories/-1")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_delete_category_zero_id():
    """ゼロのID（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 0のIDでアクセス
        response = client.delete("/api/categories/0")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ========================
# エラーハンドリングテスト (3項目)
# ========================

def test_delete_category_user_not_found():
    """存在しないユーザーのトークン（401）"""
    client = TestClient(app)

    # get_current_user 関数がユーザー見つからないエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer nonexistent_user_token"}
        response = client.delete("/api/categories/1", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_delete_category_db_error():
    """DB接続エラー時の適切なエラーレスポンス"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースエラーのモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.side_effect = Exception("Database connection error")
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        # DBエラーの場合は500エラーが期待される
        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()


def test_delete_category_concurrent_delete():
    """同時削除時の競合状態対応"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # カテゴリ取得時は存在するが、削除実行時に既に削除済みの状況をシミュレート
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "競合テストカテゴリ"
    mock_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_category
    mock_db_session.query.return_value = mock_query

    # commit時に競合エラーを発生させる
    mock_db_session.commit.side_effect = Exception("Concurrent modification detected")

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/categories/1")
        # 競合エラーの場合は500エラーが期待される
        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()