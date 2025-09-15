from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app, db

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