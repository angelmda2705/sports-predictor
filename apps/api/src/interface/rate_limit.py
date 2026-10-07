"""Rate limiter simple de ventana fija, en memoria.

⚠️ Para producción multi-instancia se reemplaza por un limitador respaldado en
Redis (ver docker-compose). Este sirve para el MVP local y para proteger los
endpoints sensibles de auth (login/registro) contra fuerza bruta básica.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class FixedWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Devuelve True si la petición está dentro del límite para ``key``."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            hits = [t for t in self._hits[key] if t > cutoff]
            if len(hits) >= self._max:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True
