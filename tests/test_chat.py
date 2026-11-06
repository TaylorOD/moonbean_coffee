import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app import rag
from app.main import create_app

@pytest.fixture(autouse=True)
def fake_answer(monkeypatch):
    monkeypatch.setattr(rag, "answer", lambda messages: iter([{"type": "delta", "text": "hi"}]))


def ask(client, headers=None, question="hello"):
    body = {"messages": [{"role": "user", "content": question}]}
    return client.post("/api/chat", json=body, headers=headers)


def test_chat_is_public_without_password_settings(client):
    assert ask(client).status_code == 200
    assert client.post("/api/login", json={"password": "anything"}).status_code == 404


def test_chat_rate_limit(client):
    assert [ask(client).status_code for _ in range(4)] == [200, 200, 200, 429]


def test_daily_limit_cant_be_passed_by_requests_at_the_same_time(client, monkeypatch):
    monkeypatch.setenv("MESSAGES_PER_MINUTE", "1000")
    monkeypatch.setenv("MESSAGES_PER_DAY", "5")
    monkeypatch.setenv("TOTAL_MESSAGES_PER_MINUTE", "1000")
    with TestClient(create_app()) as fresh:
        with ThreadPoolExecutor(max_workers=20) as pool:
            responses = list(pool.map(lambda _: ask(fresh), range(40)))
    assert sorted(r.status_code for r in responses) == [200] * 5 + [429] * 35


def test_being_rate_limited_doesnt_use_up_the_daily_limit(client, monkeypatch):
    monkeypatch.setenv("MESSAGES_PER_MINUTE", "1")
    monkeypatch.setenv("MESSAGES_PER_DAY", "2")
    with TestClient(create_app()) as fresh:
        assert ask(fresh).status_code == 200
        assert ask(fresh).status_code == 429
        # Another client gets its own IP allowance, without resetting the global budget.
        with TestClient(fresh.app, client=("192.0.2.2", 50000)) as second:
            assert ask(second).status_code == 200
            assert ask(second).status_code == 429


def test_global_minute_limit_applies_across_clients(monkeypatch):
    monkeypatch.setenv("TOTAL_MESSAGES_PER_MINUTE", "1")
    app = create_app()
    with TestClient(app, client=("192.0.2.1", 50000)) as first:
        assert ask(first).status_code == 200
    with TestClient(app, client=("192.0.2.2", 50000)) as second:
        assert ask(second).status_code == 429


def test_forwarded_header_cannot_reset_ip_limit(client):
    for i in range(3):
        assert ask(client, {"X-Forwarded-For": f"192.0.2.{i}"}).status_code == 200
    assert ask(client, {"X-Forwarded-For": "192.0.2.100"}).status_code == 429


def test_long_question_is_rejected(client):
    assert ask(client, question="x" * 1001).status_code == 422


def test_too_much_history_is_rejected(client):
    messages = [{"role": "user", "content": "hi"}] * 21
    assert client.post("/api/chat", json={"messages": messages}).status_code == 422


def test_last_message_must_be_from_the_user(client):
    messages = [{"role": "assistant", "content": "hi"}]
    assert client.post("/api/chat", json={"messages": messages}).status_code == 422


def test_system_role_is_rejected(client):
    messages = [{"role": "system", "content": "hi"}, {"role": "user", "content": "hi"}]
    assert client.post("/api/chat", json={"messages": messages}).status_code == 422


def test_chat_stream_format(client):
    lines = ask(client).text.strip().splitlines()
    assert json.loads(lines[0]) == {"type": "delta", "text": "hi"}
    assert json.loads(lines[-1]) == {"type": "done"}


def test_chat_failure_doesnt_leak_details(client, monkeypatch, caplog):
    def blow_up(messages):
        raise RuntimeError("secret key sk-123 failed")
        yield

    monkeypatch.setattr(rag, "answer", blow_up)
    body = ask(client).text
    assert "sk-123" not in body
    assert json.loads(body)["type"] == "error"
    assert "sk-123" not in caplog.text


def test_incomplete_answer_has_error_and_no_done(client, monkeypatch):
    def incomplete(messages):
        yield {"type": "delta", "text": "partial"}
        raise rag.IncompleteAnswer()
    monkeypatch.setattr(rag, "answer", incomplete)
    events = [json.loads(line) for line in ask(client).text.splitlines()]
    assert events[-1]["code"] == "incomplete"
    assert not any(event["type"] == "done" for event in events)
