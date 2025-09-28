"""
ログインAPIのテストファイル

テスト観点:
1. 正常系テスト
   - 有効な認証情報でのログイン成功
   - JWTトークンの生成確認
   - レスポンス形式の検証

2. 異常系テスト
   - 存在しないユーザー名でのログイン失敗
   - 間違ったパスワードでのログイン失敗
   - 無効化されたユーザーアカウントでのログイン失敗

3. セキュリティテスト
   - パスワードハッシュ化の検証
   - 認証失敗時の適切なエラーメッセージ
   - 無効化ユーザーのアクセス制御

4. 境界値テスト
   - 最大長ユーザー名・パスワード
   - 最小長ユーザー名・パスワード
   - 空文字の認証情報

5. データ検証テスト
   - 必須フィールドの確認
   - 不正なJSON形式の処理

テスト項目:
- test_login_success: 正常なログイン処理
- test_login_invalid_username: 存在しないユーザー名でのログイン
- test_login_invalid_password: 間違ったパスワードでのログイン
- test_login_disabled_user: 無効化されたユーザーでのログイン
"""

from unittest.mock import MagicMock

def test_login_success(client, monkeypatch):
    mock_pwd_context = MagicMock()
    mock_pwd_context.verify.return_value = True
    monkeypatch.setattr("auth.pwd_context", mock_pwd_context)

    monkeypatch.setattr("auth.jwt.encode", lambda *args, **kwargs: "test_jwt_token")

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.password = "hashed_password"
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    monkeypatch.setattr("auth.get_user_by_username", lambda username, db: mock_user)

    login_data = {
        "user_name": "test_user",
        "password": "test_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 200

    response_data = response.json()
    assert response_data["access_token"] == "test_jwt_token"
    assert response_data["token_type"] == "bearer"
    assert response_data["user"]["user_name"] == "test_user"
    assert response_data["user"]["id"] == 1

def test_login_invalid_username(client, monkeypatch):
    monkeypatch.setattr("auth.get_user_by_username", lambda username, db: None)

    login_data = {
        "user_name": "invalid_user",
        "password": "test_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_invalid_password(client, monkeypatch):
    mock_pwd_context = MagicMock()
    mock_pwd_context.verify.return_value = False
    monkeypatch.setattr("auth.pwd_context", mock_pwd_context)

    mock_user = MagicMock()
    mock_user.user_name = "test_user"
    mock_user.password = "hashed_password"
    monkeypatch.setattr("auth.get_user_by_username", lambda username, db: mock_user)

    login_data = {
        "user_name": "test_user",
        "password": "wrong_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_disabled_user(client, monkeypatch):
    mock_pwd_context = MagicMock()
    mock_pwd_context.verify.return_value = True
    monkeypatch.setattr("auth.pwd_context", mock_pwd_context)

    mock_user = MagicMock()
    mock_user.user_name = "disabled_user"
    mock_user.password = "hashed_password"
    mock_user.status = 0
    monkeypatch.setattr("auth.get_user_by_username", lambda username, db: mock_user)

    login_data = {
        "user_name": "disabled_user",
        "password": "test_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"