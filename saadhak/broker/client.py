"""Thin HTTP layer over Alpaca. One place for auth, retries and errors."""
from __future__ import annotations

import time
from typing import Any

import httpx

from saadhak.config import settings


class AlpacaError(RuntimeError):
    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"{status} {url}: {body[:400]}")
        self.status, self.body, self.url = status, body, url


def request(method: str, url: str, *, params: dict | None = None,
            json: dict | None = None, retries: int = 3, timeout: float = 20.0) -> Any:
    s = settings()
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = httpx.request(method, url, params=params, json=json,
                              headers=s.auth_headers, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise AlpacaError(r.status_code, r.text, url)
            if r.status_code >= 400:
                raise AlpacaError(r.status_code, r.text, url)  # not retried below
            return r.json() if r.content else None
        except AlpacaError as e:
            last = e
            if e.status not in (429,) and e.status < 500:
                raise
            time.sleep(0.5 * (2 ** attempt))
        except httpx.HTTPError as e:
            last = e
            time.sleep(0.5 * (2 ** attempt))
    raise last  # type: ignore[misc]


def trading(path: str, **kw) -> Any:
    return request(kw.pop("method", "GET"), f"{settings().trading_base}{path}", **kw)


def data(path: str, **kw) -> Any:
    return request(kw.pop("method", "GET"), f"{settings().data_base}{path}", **kw)
