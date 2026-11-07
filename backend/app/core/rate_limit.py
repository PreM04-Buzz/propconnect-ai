"""A simple sliding-window limit per user, used to cap AI requests.

On a public site anyone who signs in can trigger paid OpenAI calls, so each user
gets a fixed number per hour. Kept in memory: fine for one server process.
"""
import time
from collections import defaultdict, deque

_calls: dict[str, deque] = defaultdict(deque)


def allow(key: str, limit: int, window_seconds: int = 3600) -> bool:
    now = time.monotonic()
    q = _calls[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def reset() -> None:
    _calls.clear()
