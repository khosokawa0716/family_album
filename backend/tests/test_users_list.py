"""
GET /api/users APIのテストファイル（ユーザー一覧取得・管理者のみ）

管理者の識別方法: User.type = 10 が管理者、type = 0 が一般ユーザー

テスト観点:
1. 正常系テスト
   - 管理者権限（type=10）でのユーザー一覧取得成功
   - レスポンス形式の検証（配列、ユーザーオブジェクトの構造）
   - 全ユーザー情報の取得確認

2. 認証・認可テスト
   - 認証トークンなしでのアクセス失敗
   - 無効なJWTトークンでのアクセス失敗
   - 期限切れトークンでのアクセス失敗
   - 一般ユーザー（type=0）でのアクセス失敗
   - 無効化された管理者ユーザーでのアクセス失敗

3. データ検証テスト
   - ユーザー情報にパスワードが含まれていないことの確認
   - 返却されるユーザー情報の完全性確認
   - 無効化されたユーザーも含まれることの確認

4. エラーハンドリングテスト
   - 不正な形式のAuthorizationヘッダー
   - 存在しないユーザーのトークン

5. セキュリティテスト
   - 管理者以外のユーザータイプでのアクセス制御
   - トークン偽造時のアクセス拒否
   - 機密情報の非表示確認

注意: ページネーション機能とソート機能は現在未実装です。
将来的に実装予定の機能:
- クエリパラメータによるページネーション（page, limit）
- ソート機能（sort, order）

テスト項目:
- test_get_users_success_as_admin: 管理者による正常なユーザー一覧取得
- test_get_users_no_token: 認証トークンなしでのアクセス失敗
- test_get_users_invalid_token: 無効なトークンでのアクセス失敗
- test_get_users_expired_token: 期限切れトークンでのアクセス失敗
- test_get_users_non_admin_user: 一般ユーザーでのアクセス失敗
- test_get_users_disabled_admin: 無効化された管理者でのアクセス失敗
- test_get_users_malformed_header: 不正な形式のヘッダーでのアクセス失敗
- test_get_users_user_not_found: 存在しないユーザーのトークン
- test_get_users_response_format: レスポンス形式の検証
- test_get_users_no_password_in_response: パスワード情報の非表示確認
- test_get_users_includes_disabled_users: 無効化ユーザーも含まれることの確認
"""

from unittest.mock import MagicMock
import pytest


def test_get_users_success_as_admin(client):
    """管理者による正常なユーザー一覧取得テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.email = "admin@example.com"
    mock_admin_user.type = 10  # 管理者
    mock_admin_user.family_id = 1
    mock_admin_user.status = 1

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    response = client.get("/api/users", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)


def test_get_users_no_token(client):
    """認証トークンなしでのアクセス失敗テスト"""
    response = client.get("/api/users")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_get_users_invalid_token(client, monkeypatch):
    """無効なトークンでのアクセス失敗テスト"""
    from fastapi import HTTPException

    # get_current_user 関数が例外を投げるようにモック
    def mock_get_current_user(_):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    monkeypatch.setattr("routers.users.get_current_user", mock_get_current_user)

    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/users", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_users_expired_token(client, monkeypatch):
    """期限切れトークンでのアクセス失敗テスト"""
    from fastapi import HTTPException

    # get_current_user 関数が期限切れエラーを投げるようにモック
    def mock_get_current_user(_):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    monkeypatch.setattr("routers.users.get_current_user", mock_get_current_user)

    headers = {"Authorization": "Bearer expired_token"}
    response = client.get("/api/users", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_users_non_admin_user(client):
    """一般ユーザーでのアクセス失敗テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "regular_user"
    mock_user.email = "user@example.com"
    mock_user.type = 0  # 一般ユーザー
    mock_user.family_id = 1
    mock_user.status = 1

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    response = client.get("/api/users", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions. Admin access required."


def test_get_users_disabled_admin(client):
    """無効化された管理者でのアクセス失敗テスト"""
    # 無効化された管理者ユーザーのモック
    mock_disabled_admin = MagicMock()
    mock_disabled_admin.id = 3
    mock_disabled_admin.user_name = "disabled_admin"
    mock_disabled_admin.email = "disabled_admin@example.com"
    mock_disabled_admin.type = 10  # 管理者
    mock_disabled_admin.family_id = 1
    mock_disabled_admin.status = 0  # 無効化状態

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_disabled_admin

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer disabled_admin_token"}
    response = client.get("/api/users", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"


def test_get_users_malformed_header(client):
    """不正な形式のAuthorizationヘッダーでのアクセス失敗テスト"""
    # "Bearer "がないヘッダー
    headers = {"Authorization": "invalid_token"}
    response = client.get("/api/users", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # 空のヘッダー
    headers = {"Authorization": ""}
    response = client.get("/api/users", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # "Bearer"のみ
    headers = {"Authorization": "Bearer"}
    response = client.get("/api/users", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_get_users_user_not_found(client, monkeypatch):
    """存在しないユーザーのトークンでのアクセス失敗テスト"""
    from fastapi import HTTPException

    # get_current_user 関数がユーザー見つからないエラーを投げるようにモック
    def mock_get_current_user(_):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    monkeypatch.setattr("routers.users.get_current_user", mock_get_current_user)

    headers = {"Authorization": "Bearer nonexistent_user_token"}
    response = client.get("/api/users", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_users_response_format(client, monkeypatch):
    """レスポンス形式の検証テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # ユーザーリストのモック
    mock_user1 = MagicMock()
    mock_user1.id = 1
    mock_user1.user_name = "admin_user"
    mock_user1.email = "admin@example.com"
    mock_user1.type = 10
    mock_user1.family_id = 1
    mock_user1.status = 1
    mock_user1.create_date = "2023-01-01T00:00:00"
    mock_user1.update_date = "2023-01-01T00:00:00"

    mock_user2 = MagicMock()
    mock_user2.id = 2
    mock_user2.user_name = "regular_user"
    mock_user2.email = "user@example.com"
    mock_user2.type = 0
    mock_user2.family_id = 1
    mock_user2.status = 1
    mock_user2.create_date = "2023-01-02T00:00:00"
    mock_user2.update_date = "2023-01-02T00:00:00"

    mock_users = [mock_user1, mock_user2]

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # データベースセッションのモック
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.all.return_value = mock_users
    mock_session.query.return_value = mock_query
    monkeypatch.setattr("routers.users.db.session", mock_session)

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    response = client.get("/api/users", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    # 各ユーザーオブジェクトの構造確認
    for user in response_data:
        assert "id" in user
        assert "user_name" in user
        assert "email" in user
        assert "type" in user
        assert "family_id" in user
        assert "status" in user
        assert "create_date" in user
        assert "update_date" in user


def test_get_users_no_password_in_response(client, monkeypatch):
    """パスワード情報の非表示確認テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # ユーザーリストのモック（パスワード情報を含む）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.password = "hashed_password"  # パスワード情報
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # データベースセッションのモック
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.all.return_value = [mock_user]
    mock_session.query.return_value = mock_query
    monkeypatch.setattr("routers.users.db.session", mock_session)

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    response = client.get("/api/users", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()

    # パスワード情報が含まれていないことを確認
    for user in response_data:
        assert "password" not in user


def test_get_users_includes_disabled_users(client, monkeypatch):
    """無効化ユーザーも含まれることの確認テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # ユーザーリストのモック（有効・無効ユーザー含む）
    mock_active_user = MagicMock()
    mock_active_user.id = 2
    mock_active_user.user_name = "active_user"
    mock_active_user.email = "active@example.com"
    mock_active_user.type = 0
    mock_active_user.family_id = 1
    mock_active_user.status = 1  # 有効
    mock_active_user.create_date = "2023-01-01T00:00:00"
    mock_active_user.update_date = "2023-01-01T00:00:00"

    mock_disabled_user = MagicMock()
    mock_disabled_user.id = 3
    mock_disabled_user.user_name = "disabled_user"
    mock_disabled_user.email = "disabled@example.com"
    mock_disabled_user.type = 0
    mock_disabled_user.family_id = 1
    mock_disabled_user.status = 0  # 無効
    mock_disabled_user.create_date = "2023-01-02T00:00:00"
    mock_disabled_user.update_date = "2023-01-02T00:00:00"

    mock_users = [mock_active_user, mock_disabled_user]

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # データベースセッションのモック
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.all.return_value = mock_users
    mock_session.query.return_value = mock_query
    monkeypatch.setattr("routers.users.db.session", mock_session)

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    response = client.get("/api/users", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2

    # 有効・無効両方のユーザーが含まれていることを確認
    statuses = [user["status"] for user in response_data]
    assert 1 in statuses  # 有効ユーザー
    assert 0 in statuses  # 無効ユーザー