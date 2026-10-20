"""Slows down password guessing: after too many failed sign-ins for one email,
further attempts are refused for a short while.

Kept in memory, so it resets when the server restarts. That's fine for one
server; a multi-server deployment would move this to Redis or the database.
"""
import time
from collections import defaultdict, deque

from app.core.config import get_settings

_failures: dict[str, deque] = defaultdict(deque)


def _recent(email: str) -> deque:
    window = get_settings().login_window_seconds
    q = _failures[email]
    now = time.monotonic()
    while q and now - q[0] > window:
        q.popleft()
    return q


def is_locked(email: str) -> bool:
    return len(_recent(email)) >= get_settings().login_max_attempts


def record_failure(email: str) -> None:
    _recent(email).append(time.monotonic())


def reset(email: str | None = None) -> None:
    if email is None:
        _failures.clear()
    else:
        _failures.pop(email, None)
