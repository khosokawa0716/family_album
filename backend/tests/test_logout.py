"""
ログアウトAPIのテストファイル

テスト観点:
1. 正常系テスト
   - 有効なトークンでのログアウト成功
   - レスポンスの形式確認

2. 異常系テスト
   - 無効なトークンでのログアウト失敗
   - トークンなしでのログアウト失敗
   - 期限切れトークンでのログアウト失敗

3. セキュリティテスト
   - 他ユーザーのトークンでのアクセス試行
   - 不正なフォーマットのトークン

4. 境界値テスト
   - 最大長トークン
   - 空文字トークン

テスト項目:
- test_logout_success: 正常なログアウト処理
- test_logout_invalid_token: 無効なトークンでのログアウト
- test_logout_no_token: トークンなしでのログアウト
- test_logout_expired_token: 期限切れトークンでのログアウト
- test_logout_malformed_token: 不正フォーマットのトークン
"""

from unittest.mock import MagicMock
import pytest


def test_logout_success(client, monkeypatch):
    """正常なログアウトテスト"""
    # JWTトークンのデコードをモック
    mock_payload = {"sub": "test_user", "exp": 9999999999}
    monkeypatch.setattr("auth.jwt.decode", lambda *args, **kwargs: mock_payload)

    # ユーザー情報のモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.status = 1
    monkeypatch.setattr("auth.get_user_by_username", lambda username: mock_user)

    headers = {"Authorization": "Bearer valid_token"}
    response = client.post("/api/logout", headers=headers)

    assert response.status_code == 200
    response_data = response.json()
    assert "message" in response_data
    assert response_data["message"] == "Successfully logged out"


def test_logout_no_token(client):
    """トークンなしでのログアウトテスト"""
    response = client.post("/api/logout")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_logout_invalid_token(client, monkeypatch):
    """無効なトークンでのログアウトテスト"""
    # JWTデコードエラーをモック
    from jose import JWTError
    monkeypatch.setattr("auth.jwt.decode", lambda *args, **kwargs: (_ for _ in ()).throw(JWTError()))

    headers = {"Authorization": "Bearer invalid_token"}
    response = client.post("/api/logout", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_logout_expired_token(client, monkeypatch):
    """期限切れトークンでのログアウトテスト"""
    # 期限切れのトークンペイロードをモック
    mock_payload = {"sub": "test_user", "exp": 1}  # 過去のタイムスタンプ
    monkeypatch.setattr("auth.jwt.decode", lambda *args, **kwargs: mock_payload)

    headers = {"Authorization": "Bearer expired_token"}
    response = client.post("/api/logout", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_logout_user_not_found(client, monkeypatch):
    """存在しないユーザーのトークンでのログアウトテスト"""
    # 有効なトークンだが存在しないユーザー
    mock_payload = {"sub": "nonexistent_user", "exp": 9999999999}
    monkeypatch.setattr("auth.jwt.decode", lambda *args, **kwargs: mock_payload)
    monkeypatch.setattr("auth.get_user_by_username", lambda username: None)

    headers = {"Authorization": "Bearer valid_token_invalid_user"}
    response = client.post("/api/logout", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"


def test_logout_disabled_user(client, monkeypatch):
    """無効化されたユーザーのトークンでのログアウトテスト"""
    mock_payload = {"sub": "disabled_user", "exp": 9999999999}
    monkeypatch.setattr("auth.jwt.decode", lambda *args, **kwargs: mock_payload)

    # 無効化されたユーザー情報のモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "disabled_user"
    mock_user.status = 0  # 無効化ステータス
    monkeypatch.setattr("auth.get_user_by_username", lambda username: mock_user)

    headers = {"Authorization": "Bearer valid_token_disabled_user"}
    response = client.post("/api/logout", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"


def test_logout_malformed_authorization_header(client):
    """不正なAuthorizationヘッダーでのテスト"""
    headers = {"Authorization": "InvalidFormat"}
    response = client.post("/api/logout", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_logout_empty_token(client):
    """空のトークンでのテスト"""
    headers = {"Authorization": "Bearer "}
    response = client.post("/api/logout", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"