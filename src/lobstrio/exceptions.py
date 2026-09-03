from __future__ import annotations


class APIError(Exception):
    """Base exception for all Lobstr.io API errors."""

    def __init__(self, status_code: int, message: str, body: dict[str, object] | None = None) -> None:
        self.status_code = status_code
        self.message = message
        self.body = body or {}
        super().__init__(f"[{status_code}] {message}")


class AuthError(APIError):
    """Raised on 401 Unauthorized responses."""


class NotFoundError(APIError):
    """Raised on 404 Not Found responses."""


class RateLimitError(APIError):
    """Raised on 429 Too Many Requests responses."""

    def __init__(
        self, status_code: int, message: str, body: dict[str, object] | None = None, retry_after: str | None = None,
    ) -> None:
        super().__init__(status_code, message, body)
        self.retry_after = retry_after


class RunTimeout(TimeoutError):
    """Raised when a run does not finish within the wait timeout.

    Subclasses the built-in ``TimeoutError`` so it can be caught either way.
    The run itself is not aborted — it keeps running server-side and can be
    re-attached later with ``runs.wait(run_id)`` / ``runs.get(run_id)``.
    """

    def __init__(self, run_id: str, timeout: float) -> None:
        self.run_id = run_id
        self.timeout = timeout
        super().__init__(f"Run {run_id} did not finish within {timeout}s")
