import time

# ttl ==> Time to Live 

class TTLCache:
    """A dict whose entries expire after a fixed number of seconds."""

    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds
        # Each entry is key -> (expires_at, value)
        self.entries = {}

    def get(self, key):
        """Return the cached value, or None if it is missing or expired."""
        entry = self.entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        # monotonic() only counts forwards, which can jump when the clocks change
        if time.monotonic() > expires_at:
            del self.entries[key]  # expired, so forget it
            return None
        return value

    def set(self, key, value):
        """Store a value that expires ttl_seconds from now."""
        self.entries[key] = (time.monotonic() + self.ttl_seconds, value)
