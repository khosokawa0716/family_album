from unittest.mock import MagicMock
from main import app

def test_create_user_success(client):
    from datetime import datetime
    from models import User

    mock_db = MagicMock()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None

    # refresh をモック化してユーザーオブジェクトに必要な属性を設定
    def mock_refresh(user):
        user.id = 1
        user.create_date = datetime.now()
        user.update_date = datetime.now()
        user.status = 1

    mock_db.refresh.side_effect = mock_refresh

    # FastAPIの依存注入をオーバーライド
    from routers.users import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        test_data = {
            "user_name": "test_user",
            "password": "test_password",
            "email": "test@example.com",
            "type": 0,
            "family_id": 1
        }

        response = client.post("/api/users", json=test_data)
        assert response.status_code == 200

        response_data = response.json()
        assert response_data["user_name"] == "test_user"
        assert response_data["email"] == "test@example.com"
        assert response_data["type"] == 0
        assert response_data["family_id"] == 1

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    finally:
        app.dependency_overrides.clear()

def test_create_user_failure(client):
    mock_db = MagicMock()
    mock_db.add.side_effect = Exception("Database error")
    mock_db.rollback.return_value = None

    # FastAPIの依存注入をオーバーライド
    from routers.users import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
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

        mock_db.rollback.assert_called_once()
    finally:
        app.dependency_overrides.clear()