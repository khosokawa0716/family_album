from unittest.mock import MagicMock

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI backend!"}

def test_health_check(client, monkeypatch):
    mock_result = ("テストメッセージ",)
    mock_execute = MagicMock()
    mock_execute.fetchone.return_value = mock_result

    from database import db
    monkeypatch.setattr(db.session, "execute", lambda *a, **kw: mock_execute)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "テストメッセージ"}