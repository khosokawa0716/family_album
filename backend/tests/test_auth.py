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

    monkeypatch.setattr("auth.get_user_by_username", lambda username: mock_user)

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
    monkeypatch.setattr("auth.get_user_by_username", lambda username: None)

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
    monkeypatch.setattr("auth.get_user_by_username", lambda username: mock_user)

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
    monkeypatch.setattr("auth.get_user_by_username", lambda username: mock_user)

    login_data = {
        "user_name": "disabled_user",
        "password": "test_password"
    }

    response = client.post("/api/login", json=login_data)
    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"