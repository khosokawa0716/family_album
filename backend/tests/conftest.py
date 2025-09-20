import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db_session(monkeypatch):
    mock_session = MagicMock()
    from database import db
    monkeypatch.setattr(db, "session", mock_session)
    return mock_session