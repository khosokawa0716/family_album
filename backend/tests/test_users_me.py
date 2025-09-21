"""
GET /api/users/me APIのテストファイル

テスト観点:
1. 正常系テスト
   - 有効なJWTトークンでのユーザー情報取得成功
   - レスポンス形式の検証
   - ユーザー情報の正確性確認

2. 異常系テスト
   - 認証トークンなしでのアクセス失敗
   - 無効なJWTトークンでのアクセス失敗
   - 期限切れトークンでのアクセス失敗
   - 存在しないユーザーのトークンでのアクセス失敗

3. セキュリティテスト
   - パスワード情報の非表示確認
   - 他ユーザーの情報へのアクセス制御
   - 無効化されたユーザーのアクセス制御

4. 境界値テスト
   - 不正な形式のAuthorizationヘッダー
   - 空のAuthorizationヘッダー

テスト項目:
- test_get_current_user_success: 正常なユーザー情報取得
- test_get_current_user_no_token: トークンなしでのアクセス
- test_get_current_user_invalid_token: 無効なトークンでのアクセス
- test_get_current_user_expired_token: 期限切れトークンでのアクセス
- test_get_current_user_malformed_header: 不正な形式のヘッダー
- test_get_current_user_disabled_user: 無効化されたユーザーでのアクセス
"""

from unittest.mock import MagicMock
import pytest


def test_get_current_user_success(client):
    """有効なJWTトークンでのユーザー情報取得成功テスト"""
    # モックユーザーを作成
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer test_jwt_token"}
    response = client.get("/api/users/me", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == 1
    assert response_data["user_name"] == "test_user"
    assert response_data["email"] == "test@example.com"
    assert response_data["type"] == 0
    assert response_data["family_id"] == 1
    assert response_data["status"] == 1
    # パスワードが含まれていないことを確認
    assert "password" not in response_data


def test_get_current_user_no_token(client):
    """認証トークンなしでのアクセス失敗テスト"""
    response = client.get("/api/users/me")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_get_current_user_invalid_token(client, monkeypatch):
    """無効なJWTトークンでのアクセス失敗テスト"""
    from fastapi import HTTPException

    # get_current_user 関数が例外を投げるようにモック
    def mock_get_current_user(_):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    monkeypatch.setattr("routers.users.get_current_user", mock_get_current_user)

    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_current_user_expired_token(client, monkeypatch):
    """期限切れトークンでのアクセス失敗テスト"""
    from fastapi import HTTPException

    # get_current_user 関数が期限切れエラーを投げるようにモック
    def mock_get_current_user(_):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    monkeypatch.setattr("routers.users.get_current_user", mock_get_current_user)

    headers = {"Authorization": "Bearer expired_token"}
    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_current_user_malformed_header(client):
    """不正な形式のAuthorizationヘッダーでのアクセス失敗テスト"""
    # "Bearer "がないヘッダー
    headers = {"Authorization": "test_jwt_token"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # 空のヘッダー
    headers = {"Authorization": ""}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # "Bearer"のみ
    headers = {"Authorization": "Bearer"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_get_current_user_user_not_found(client, monkeypatch):
    """存在しないユーザーのトークンでのアクセス失敗テスト"""
    from fastapi import HTTPException

    # get_current_user 関数がユーザー見つからないエラーを投げるようにモック
    def mock_get_current_user(_):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    monkeypatch.setattr("routers.users.get_current_user", mock_get_current_user)

    headers = {"Authorization": "Bearer test_jwt_token"}
    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_current_user_disabled_user(client):
    """無効化されたユーザーでのアクセス失敗テスト"""
    # 無効化されたユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "disabled_user"
    mock_user.email = "disabled@example.com"
    mock_user.status = 0  # 無効化状態

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer test_jwt_token"}
    response = client.get("/api/users/me", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"


def test_get_current_user_no_username_in_token(client, monkeypatch):
    """トークンにユーザー名がない場合のアクセス失敗テスト"""
    from fastapi import HTTPException

    # get_current_user 関数がユーザー名なしエラーを投げるようにモック
    def mock_get_current_user(_):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    monkeypatch.setattr("routers.users.get_current_user", mock_get_current_user)

    headers = {"Authorization": "Bearer test_jwt_token"}
    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"