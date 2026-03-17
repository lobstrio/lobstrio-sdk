from __future__ import annotations


class APIError(Exception):
    """Base exception for all Lobstr.io API errors."""

    def __init__(self, status_code: int, message: str, body: dict | None = None) -> None:
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
        self, status_code: int, message: str, body: dict | None = None, retry_after: str | None = None,
    ) -> None:
        super().__init__(status_code, message, body)
        self.retry_after = retry_after
