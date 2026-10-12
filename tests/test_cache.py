import time

from commute_mcp.cache import TTLCache


class FakeClock:
    """Stands in for time.monotonic so tests control time instead of sleeping."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_cache(monkeypatch, ttl_seconds):
    clock = FakeClock()
    monkeypatch.setattr(time, "monotonic", clock)
    return TTLCache(ttl_seconds), clock


def test_get_missing_key_returns_none():
    cache = TTLCache(30)
    assert cache.get("nothing here") is None


def test_get_returns_value_before_expiry(monkeypatch):
    cache, clock = make_cache(monkeypatch, 30)
    cache.set("GLD", "board")
    clock.now += 29
    assert cache.get("GLD") == "board"


def test_get_returns_none_after_expiry(monkeypatch):
    cache, clock = make_cache(monkeypatch, 30)
    cache.set("GLD", "board")
    clock.now += 31
    assert cache.get("GLD") is None


def test_expired_entry_is_removed(monkeypatch):
    cache, clock = make_cache(monkeypatch, 30)
    cache.set("GLD", "board")
    clock.now += 31
    cache.get("GLD")
    assert "GLD" not in cache.entries


def test_set_again_resets_expiry(monkeypatch):
    cache, clock = make_cache(monkeypatch, 30)
    cache.set("GLD", "old board")
    clock.now += 20
    cache.set("GLD", "new board")
    clock.now += 20  # 40s after the first set, but only 20s after the second
    assert cache.get("GLD") == "new board"
