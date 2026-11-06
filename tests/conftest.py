import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TOTAL_MESSAGES_PER_MINUTE", "3")
    with TestClient(create_app()) as test_client:
        yield test_client
