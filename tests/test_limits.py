from app.limits import RateLimiter


def test_rate_limiter_window_expires():
    now = [0]
    limiter = RateLimiter(1, 10, clock=lambda: now[0])
    limiter.record("a")
    assert limiter.is_blocked("a")
    now[0] = 11
    assert not limiter.is_blocked("a")


def test_cors_restricts_browser_origins(client):
    def preflight(origin):
        return client.options("/api/chat", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    site = "https://www.taylordorsett.com"
    assert preflight(site).headers["access-control-allow-origin"] == site
    assert "access-control-allow-origin" not in preflight("https://other.example").headers
