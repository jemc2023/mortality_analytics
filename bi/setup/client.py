"""REST API client helpers for Apache Superset.

Provides session management, retry logic with exponential backoff,
and reusable request wrappers for consistent error handling across
all Superset API interactions.
"""

import time
import requests


class SessionManager:
    """Manages an authenticated requests.Session with retry logic.

    Encapsulates the session, base URL, and retry configuration so
    callers do not need to pass them on every request.
    """

    def __init__(
        self,
        base_url: str,
        session: requests.Session,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ):
        """Initialise the session manager.

        Args:
            base_url: Superset API base URL (e.g. http://localhost:8088).
            session: Authenticated requests.Session with auth headers.
            max_retries: Maximum retry attempts on transient failures.
            backoff_factor: Multiplier for exponential backoff delay.
        """
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _api_url(self, path: str) -> str:
        """Construct a full API URL from a relative path."""
        return f"{self.base_url}{path}"

    def _retry(self, request_fn, *args, **kwargs):
        """Execute a request with exponential-backoff retry on timeout.

        Args:
            request_fn: Bound method on self.session (e.g. self.session.get).
            *args: Positional args for the request.
            **kwargs: Keyword args for the request.

        Returns:
            requests.Response

        Raises:
            requests.Timeout: If all retries are exhausted.
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return request_fn(*args, timeout=30, **kwargs)
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    delay = self.backoff_factor ** attempt
                    time.sleep(delay)
        raise last_error  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API helpers
    # ------------------------------------------------------------------

    def get(self, path: str, params=None):
        """HTTP GET with retry."""
        return self._retry(self.session.get, self._api_url(path),
                          params=params)

    def post(self, path: str, json_data=None, files=None):
        """HTTP POST with retry."""
        return self._retry(self.session.post, self._api_url(path),
                          json=json_data, files=files)

    def put(self, path: str, json_data=None):
        """HTTP PUT with retry."""
        return self._retry(self.session.put, self._api_url(path),
                          json=json_data)


# ------------------------------------------------------------------
# Module-level helpers (for scripts that prefer plain functions)
# ------------------------------------------------------------------

def api_get(session: requests.Session, url: str,
             params=None, max_retries: int = 3,
             backoff_factor: float = 2.0) -> requests.Response:
    """Perform a GET request with retry on transient errors."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return session.get(url, params=params, timeout=30)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
    raise last_error  # type: ignore[misc]


def api_get_all(
    session: requests.Session,
    url: str,
    params: dict | None = None,
    page_size: int = 100,
) -> list[dict]:
    """Fetch all rows from a paginated Superset list endpoint."""
    rows: list[dict] = []
    page = 0
    base_params = dict(params or {})
    while True:
        request_params = {**base_params, "page": page, "page_size": page_size}
        resp = api_get(session, url, params=request_params)
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("result", [])
        rows.extend(batch)
        total = payload.get("count")
        if len(batch) < page_size or (isinstance(total, int) and len(rows) >= total):
            return rows
        page += 1


def api_post(session: requests.Session, url: str,
              json_data=None, files=None,
              max_retries: int = 3,
              backoff_factor: float = 2.0) -> requests.Response:
    """Perform a POST request with retry on transient errors."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return session.post(url, json=json_data, files=files, timeout=30)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
    raise last_error  # type: ignore[misc]


def api_put(session: requests.Session, url: str,
             json_data=None,
             max_retries: int = 3,
             backoff_factor: float = 2.0) -> requests.Response:
    """Perform a PUT request with retry on transient errors."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return session.put(url, json=json_data, timeout=30)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
    raise last_error  # type: ignore[misc]
