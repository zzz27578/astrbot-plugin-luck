from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any, Callable


_JSON_CACHE: dict[str, dict[str, Any]] = {}
_JSON_CACHE_LOCK = threading.Lock()


def _clone_default(default):
    if callable(default):
        return default()
    return copy.deepcopy(default)


def load_json_cached(path: str | Path, default=None, *, normalize: Callable[[Any], Any] | None = None):
    target = Path(path)
    try:
        stat = target.stat()
    except OSError:
        return _clone_default({} if default is None else default)

    cache_key = str(target.resolve())
    signature = (stat.st_mtime_ns, stat.st_size)

    with _JSON_CACHE_LOCK:
        cached = _JSON_CACHE.get(cache_key)
        if cached and cached.get("signature") == signature:
            return copy.deepcopy(cached.get("value"))

    try:
        with open(target, "r", encoding="utf-8") as f:
            raw = json.load(f)
        value = normalize(raw) if callable(normalize) else raw
    except Exception:
        value = _clone_default({} if default is None else default)

    with _JSON_CACHE_LOCK:
        _JSON_CACHE[cache_key] = {
            "signature": signature,
            "value": copy.deepcopy(value),
        }
    return copy.deepcopy(value)


def invalidate_json_cache(path: str | Path):
    target = Path(path)
    try:
        cache_key = str(target.resolve())
    except OSError:
        cache_key = str(target)
    with _JSON_CACHE_LOCK:
        _JSON_CACHE.pop(cache_key, None)
