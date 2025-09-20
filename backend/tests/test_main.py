from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app, db
import pytest

def test_health_check(monkeypatch):
    # モックの返り値を用意
    mock_result = ("テストメッセージ",)
    mock_execute = MagicMock()
    mock_execute.fetchone.return_value = mock_result

    # db.session.executeをモック
    monkeypatch.setattr(db.session, "execute", lambda *a, **kw: mock_execute)

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "テストメッセージ"}

def test_create_user_success(monkeypatch):
    # db.sessionのモックを作成
    mock_session = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.refresh.return_value = None

    monkeypatch.setattr(db, "session", mock_session)

    # Userモデルのコンストラクタをモック
    from models import User
    monkeypatch.setattr("main.User", lambda **kwargs: mock_user)

    client = TestClient(app)
    test_data = {
        "user_name": "test_user",
        "password": "test_password",
        "email": "test@example.com",
        "type": 0,
        "family_id": 1
    }

    response = client.post("/api/users", json=test_data)
    assert response.status_code == 200

    # セッションのメソッドが呼ばれたことを確認
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()

def test_create_user_failure(monkeypatch):
    # db.sessionのモックを作成（例外を発生させる）
    mock_session = MagicMock()
    mock_session.add.side_effect = Exception("Database error")
    mock_session.rollback.return_value = None

    monkeypatch.setattr(db, "session", mock_session)

    # Userモデルのコンストラクタをモック
    mock_user = MagicMock()
    monkeypatch.setattr("main.User", lambda **kwargs: mock_user)

    client = TestClient(app)
    test_data = {
        "user_name": "test_user",
        "password": "test_password",
        "email": "test@example.com",
        "type": 0,
        "family_id": 1
    }

    response = client.post("/api/users", json=test_data)
    assert response.status_code == 400
    assert "User creation failed" in response.json()["detail"]

    # rollbackが呼ばれたことを確認
    mock_session.rollback.assert_called_once()

def test_login_success(monkeypatch):
    # パスワードハッシュ化のモック
    from passlib.context import CryptContext
    mock_pwd_context = MagicMock()
    mock_pwd_context.verify.return_value = True
    monkeypatch.setattr("main.pwd_context", mock_pwd_context)

    # JWTエンコードのモック
    monkeypatch.setattr("main.jwt.encode", lambda *args, **kwargs: "test_jwt_token")

    # ユーザー検索のモック
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

    monkeypatch.setattr("main.get_user_by_username", lambda username: mock_user)

    client = TestClient(app)
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

def test_login_invalid_username(monkeypatch):
    # ユーザーが見つからない場合のモック
    monkeypatch.setattr("main.get_user_by_username", lambda username: None)

    client = TestClient(app)
    login_data = {
        "user_name": "invalid_user",
        "password": "test_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_invalid_password(monkeypatch):
    # パスワード検証失敗のモック
    from passlib.context import CryptContext
    mock_pwd_context = MagicMock()
    mock_pwd_context.verify.return_value = False
    monkeypatch.setattr("main.pwd_context", mock_pwd_context)

    # ユーザー検索のモック
    mock_user = MagicMock()
    mock_user.user_name = "test_user"
    mock_user.password = "hashed_password"
    monkeypatch.setattr("main.get_user_by_username", lambda username: mock_user)

    client = TestClient(app)
    login_data = {
        "user_name": "test_user",
        "password": "wrong_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_disabled_user(monkeypatch):
    # パスワードハッシュ化のモック
    from passlib.context import CryptContext
    mock_pwd_context = MagicMock()
    mock_pwd_context.verify.return_value = True
    monkeypatch.setattr("main.pwd_context", mock_pwd_context)

    # 無効ユーザーのモック
    mock_user = MagicMock()
    mock_user.user_name = "disabled_user"
    mock_user.password = "hashed_password"
    mock_user.status = 0  # 無効ステータス
    monkeypatch.setattr("main.get_user_by_username", lambda username: mock_user)

    client = TestClient(app)
    login_data = {
        "user_name": "disabled_user",
        "password": "test_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"