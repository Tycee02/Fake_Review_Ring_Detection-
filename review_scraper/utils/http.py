from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from config import Settings


class HttpClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.log = logging.getLogger("http")
        self.client = httpx.Client(
            timeout=httpx.Timeout(settings.timeout_seconds),
            follow_redirects=True,
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-NG,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            },
            limits=httpx.Limits(max_connections=settings.concurrency, max_keepalive_connections=settings.concurrency),
        )

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.get(url, **kwargs)
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt >= self.settings.max_retries:
                        response.raise_for_status()
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else (
                        2 ** attempt + random.uniform(0, 1.5)
                    )
                    self.log.warning("Transient HTTP %s for %s; sleeping %.1fs", response.status_code, url, delay)
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                time.sleep(max(0.0, self.settings.delay_seconds + random.uniform(0, 0.75)))
                return response
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
                last_exc = exc
                if attempt >= self.settings.max_retries:
                    raise
                delay = 2 ** attempt + random.uniform(0, 1.5)
                self.log.warning("Network error for %s: %s; retrying in %.1fs", url, exc, delay)
                time.sleep(delay)
        raise last_exc or RuntimeError("HTTP request failed")

    def close(self) -> None:
        self.client.close()
