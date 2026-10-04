"""JioFarm — Proxy Rotation & Session Manager."""

from __future__ import annotations

import itertools
import threading


class ProxyManager:
    """Thread-safe proxy rotator supporting single gateway or multiple proxy endpoints."""

    def __init__(self, raw: str = ""):
        self.raw = raw.strip()
        items = [p.strip() for p in self.raw.split(",") if p.strip()]
        self.proxies = items
        self._lock = threading.Lock()
        self._cycle = itertools.cycle(self.proxies) if self.proxies else None

    def has_proxy(self) -> bool:
        return bool(self.proxies)

    def get_proxy_dict(self) -> dict[str, str] | None:
        """Return requests-compatible proxies dict or None."""
        if not self._cycle:
            return None
        with self._lock:
            p = next(self._cycle)
        if not p.startswith(("http://", "https://", "socks5://")):
            p = f"http://{p}"
        return {"http": p, "https": p}
