import json

import pytest

from app import auth, rag

PASSWORD = "correct horse battery staple"


@pytest.fixture(autouse=True)
def fake_answer(monkeypatch):
    monkeypatch.setattr(rag, "answer", lambda messages: iter([{"type": "delta", "text": "hi"}]))


@pytest.fixture
def headers(log_in):
    return {"Authorization": f"Bearer {log_in().json()['token']}"}


def ask(client, headers=None, question="hello"):
    body = {"messages": [{"role": "user", "content": question}]}
    return client.post("/api/chat", json=body, headers=headers)


def test_chat_needs_a_token(client):
    assert ask(client).status_code == 401


def test_forged_token_is_rejected(client):
    assert ask(client, {"Authorization": "Bearer forged.token.value"}).status_code == 401


def test_token_from_another_secret_is_rejected(client):
    other = auth.Sessions("different secret", auth.hash_password(PASSWORD))
    assert ask(client, {"Authorization": f"Bearer {other.create()}"}).status_code == 401


def test_right_password_gets_a_working_token(client, headers):
    assert ask(client, headers).status_code == 200


def test_chat_rate_limit(client, headers):
    assert [ask(client, headers).status_code for _ in range(4)] == [200, 200, 200, 429]


def test_long_question_is_rejected(client, headers):
    assert ask(client, headers, "x" * 1001).status_code == 422


def test_too_much_history_is_rejected(client, headers):
    messages = [{"role": "user", "content": "hi"}] * 21
    assert client.post("/api/chat", json={"messages": messages}, headers=headers).status_code == 422


def test_last_message_must_be_from_the_user(client, headers):
    messages = [{"role": "assistant", "content": "hi"}]
    assert client.post("/api/chat", json={"messages": messages}, headers=headers).status_code == 422


def test_system_role_is_rejected(client, headers):
    messages = [{"role": "system", "content": "hi"}, {"role": "user", "content": "hi"}]
    assert client.post("/api/chat", json={"messages": messages}, headers=headers).status_code == 422


def test_chat_stream_format(client, headers):
    lines = ask(client, headers).text.strip().splitlines()
    assert json.loads(lines[0]) == {"type": "delta", "text": "hi"}


def test_chat_failure_doesnt_leak_details(client, headers, monkeypatch):
    def blow_up(messages):
        raise RuntimeError("secret key sk-123 failed")
        yield

    monkeypatch.setattr(rag, "answer", blow_up)
    body = ask(client, headers).text
    assert "sk-123" not in body
    assert json.loads(body)["type"] == "error"
