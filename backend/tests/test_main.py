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