import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import create_app

PASSWORD = "correct horse battery staple"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(PASSWORD))
    monkeypatch.setenv("SESSION_SECRET", "test secret")
    monkeypatch.setenv("MESSAGES_PER_MINUTE", "3")
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def log_in(client):
    def _log_in(password=PASSWORD):
        return client.post("/api/login", json={"password": password})

    return _log_in
