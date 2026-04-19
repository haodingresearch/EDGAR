"""SEC-compliant HTTP client with rate limiting and retries.

The SEC requires automated EDGAR access to declare a User-Agent that identifies
the requester (name + contact email) and to stay below 10 requests per second
per their fair-access policy: https://www.sec.gov/os/accessing-edgar-data

Rather than hard-code an email, the client reads ``EDGAR_USER_AGENT`` from the
environment. Missing or malformed values raise loudly so researchers don't
accidentally impersonate someone else's contact.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from threading import Lock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEC_MAX_RPS = 10
DEFAULT_RPS = 8.0


class UserAgentError(RuntimeError):
    """Raised when EDGAR_USER_AGENT is missing or malformed."""


def require_user_agent() -> str:
    ua = os.environ.get("EDGAR_USER_AGENT", "").strip()
    if not ua or " " not in ua or "@" not in ua:
        raise UserAgentError(
            "EDGAR_USER_AGENT is not set or malformed.\n"
            "SEC fair-access policy requires declaring a contact, e.g.:\n"
            "    export EDGAR_USER_AGENT='Jane Researcher jane@example.edu'\n"
            "See https://www.sec.gov/os/accessing-edgar-data"
        )
    return ua


class SECClient:
    """Thread-safe throttled HTTP client for SEC endpoints."""

    def __init__(self, rps: float = DEFAULT_RPS, user_agent: str | None = None):
        if rps > SEC_MAX_RPS:
            raise ValueError(f"rps must not exceed SEC's policy of {SEC_MAX_RPS}")
        self.user_agent = user_agent or require_user_agent()
        self._min_interval = 1.0 / rps
        self._last_request = 0.0
        self._lock = Lock()
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov",
            }
        )
        retry = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({"GET", "HEAD"}),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        return s

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

    def get(self, url: str, *, stream: bool = False, timeout: float = 30.0) -> requests.Response:
        self._throttle()
        # "Host" header is SEC-specific; requests sets it automatically for other hosts
        headers = None
        if "www.sec.gov" not in url:
            headers = {k: v for k, v in self._session.headers.items() if k != "Host"}
        resp = self._session.get(url, stream=stream, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return resp

    def download(self, url: str, dest: Path | str, *, chunk_size: int = 65536) -> Path:
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        resp = self.get(url, stream=True)
        tmp = dest_path.with_suffix(dest_path.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest_path)
        return dest_path

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> SECClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
