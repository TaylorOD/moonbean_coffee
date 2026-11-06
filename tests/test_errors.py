import httpx
from openai import APITimeoutError, RateLimitError

from app.errors import public_error


def test_quota_and_throttle_get_different_messages():
    response = httpx.Response(429, request=httpx.Request("POST", "https://example.com"))
    quota = RateLimitError("private provider details", response=response, body={"code": "insufficient_quota"})
    busy = RateLimitError("private provider details", response=response, body={"code": "rate_limit_exceeded"})
    assert public_error(quota)[0] == "budget"
    assert public_error(busy)[0] == "busy"
    assert "private" not in public_error(quota)[1]


def test_timeout_has_a_safe_message():
    error = APITimeoutError(request=httpx.Request("POST", "https://example.com"))
    assert public_error(error)[0] == "timeout"
