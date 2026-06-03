import time
import threading
from typing import Any

_TTL_SECONDS = 10 * 60
_MAX_ENTRIES = 64
_store: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def _normalize(topic: str) -> str:
    return topic.strip().lower()


def get(topic: str) -> Any | None:
    key = _normalize(topic)
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        ts, value = entry
        if time.time() - ts > _TTL_SECONDS:
            _store.pop(key, None)
            return None
        return value


def set_(topic: str, value: Any) -> None:
    key = _normalize(topic)
    with _lock:
        if len(_store) >= _MAX_ENTRIES:
            oldest = min(_store.items(), key=lambda kv: kv[1][0])[0]
            _store.pop(oldest, None)
        _store[key] = (time.time(), value)
