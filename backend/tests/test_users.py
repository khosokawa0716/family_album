from unittest.mock import MagicMock

def test_create_user_success(client, mock_db_session, monkeypatch):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    from models import User
    monkeypatch.setattr("routers.users.User", lambda **kwargs: mock_user)

    test_data = {
        "user_name": "test_user",
        "password": "test_password",
        "email": "test@example.com",
        "type": 0,
        "family_id": 1
    }

    response = client.post("/api/users", json=test_data)
    assert response.status_code == 200

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

def test_create_user_failure(client, mock_db_session, monkeypatch):
    mock_db_session.add.side_effect = Exception("Database error")
    mock_db_session.rollback.return_value = None

    mock_user = MagicMock()
    from models import User
    monkeypatch.setattr("routers.users.User", lambda **kwargs: mock_user)

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

    mock_db_session.rollback.assert_called_once()