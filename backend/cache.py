"""Cache layer: Redis (Upstash) when REDIS_URL is set, otherwise an in-process TTL cache.

Every visitor reads the same market data, so responses are computed once and served from cache.
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from core.config import get_settings

log = logging.getLogger("wealthlens.cache")


class MemoryCache:
    backend = "memory"

    def __init__(self) -> None:
        self._d: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()
        self.hits = self.misses = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._d.get(key)
            if not item or item[0] < time.time():
                self._d.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return json.loads(item[1])

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            if len(self._d) > 5000:  # crude bound
                self._d.clear()
            self._d[key] = (time.time() + ttl, json.dumps(value, default=str))

    def get_raw(self, key: str) -> str | None:
        with self._lock:
            item = self._d.get(key)
            if not item or item[0] < time.time():
                self._d.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return item[1]

    def set_raw(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            if len(self._d) > 5000:
                self._d.clear()
            self._d[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._d.pop(key, None)

    def clear_prefix(self, prefix: str) -> None:
        with self._lock:
            for k in [k for k in self._d if k.startswith(prefix)]:
                del self._d[k]

    def ping(self) -> bool:
        return True


class RedisCache:
    backend = "redis"

    def __init__(self, url: str) -> None:
        import redis

        self.r = redis.Redis.from_url(url, socket_timeout=2, decode_responses=True)
        self.hits = self.misses = 0

    def get(self, key: str) -> Any | None:
        try:
            v = self.r.get(key)
        except Exception as e:
            log.warning("Redis get failed: %s", e)
            return None
        if v is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(v)

    def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            self.r.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception as e:
            log.warning("Redis set failed: %s", e)

    def get_raw(self, key: str) -> str | None:
        try:
            v = self.r.get(key)
        except Exception:
            return None
        if v is None:
            self.misses += 1
        else:
            self.hits += 1
        return v

    def set_raw(self, key: str, value: str, ttl: int) -> None:
        try:
            self.r.set(key, value, ex=ttl)
        except Exception:
            pass

    def delete(self, key: str) -> None:
        try:
            self.r.delete(key)
        except Exception:
            pass

    def clear_prefix(self, prefix: str) -> None:
        try:
            for k in self.r.scan_iter(f"{prefix}*", count=500):
                self.r.delete(k)
        except Exception:
            pass

    def ping(self) -> bool:
        try:
            return bool(self.r.ping())
        except Exception:
            return False


def _make_cache():
    url = get_settings().redis_url
    if url:
        c = RedisCache(url)
        if c.ping():
            log.info("Using Redis cache")
            return c
        log.warning("Redis unreachable, falling back to in-memory cache")
    return MemoryCache()


cache = _make_cache()


def cached(prefix: str, ttl: int = 300) -> Callable:
    """Cache a function's JSON-serialisable result keyed by its arguments."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            raw = json.dumps([args, kwargs], default=str, sort_keys=True)
            key = f"api:{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"
            hit = cache.get(key)
            if hit is not None:
                return hit
            value = fn(*args, **kwargs)
            cache.set(key, value, ttl)
            return value

        return wrapper

    return deco
