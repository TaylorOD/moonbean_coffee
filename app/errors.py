"""Public error messages. Never return provider exception text to a visitor."""
from openai import APITimeoutError, RateLimitError

from app.rag import IncompleteAnswer


def public_error(error):
    if isinstance(error, IncompleteAnswer):
        return "incomplete", "That answer was cut short. Please try again."
    if isinstance(error, (APITimeoutError, TimeoutError)):
        return "timeout", "The handbook is taking too long to answer. Please try again."
    if isinstance(error, RateLimitError):
        if error.code in {"insufficient_quota", "billing_hard_limit_reached"}:
            return "budget", "Ask has used its AI allowance for now. The handbook is still open to read."
        return "busy", "Our AI service is busy. Please give it a minute and try again."
    return "unavailable", "Ask is unavailable right now. Please try again later or read the handbook."
