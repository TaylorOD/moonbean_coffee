import pytest

from app import auth
from app.limits import RateLimiter
from app.main import create_app

SITE = "https://www.taylordorsett.com"


def test_app_refuses_to_start_without_a_password(monkeypatch):
    monkeypatch.setattr("app.main.load_dotenv", lambda: None)
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    with pytest.raises(RuntimeError):
        create_app()


def test_password_is_hashed_with_argon2id():
    hashed = auth.hash_password("hunter2hunter2")
    assert hashed.startswith("$argon2id$")
    assert "hunter2" not in hashed
    assert auth.password_matches("hunter2hunter2", hashed)
    assert not auth.password_matches("nope", hashed)


def test_wrong_password(log_in):
    response = log_in("nope")
    assert response.status_code == 401
    assert "token" not in response.json()


def test_right_password_gets_a_token(log_in):
    assert log_in().json()["token"]


def test_login_locks_after_five_failures_even_with_the_right_password(log_in):
    for _ in range(5):
        assert log_in("nope").status_code == 401
    assert log_in("nope").status_code == 429
    assert log_in().status_code == 429


def test_token_stops_working_when_the_password_changes():
    token = auth.Sessions("secret", "old hash").create()
    assert auth.Sessions("secret", "old hash").read(token)
    assert auth.Sessions("secret", "new hash").read(token) is None


def test_only_the_site_can_call_it_from_a_browser(client):
    def preflight(origin):
        return client.options(
            "/api/login",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )

    assert preflight(SITE).headers["access-control-allow-origin"] == SITE
    assert "access-control-allow-origin" not in preflight("https://evil.example").headers


def test_rate_limiter_window_expires():
    now = [0]
    limiter = RateLimiter(1, 10, clock=lambda: now[0])
    limiter.record("a")
    assert limiter.is_blocked("a")
    now[0] = 11
    assert not limiter.is_blocked("a")
