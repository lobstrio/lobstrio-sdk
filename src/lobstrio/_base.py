from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

from lobstrio.exceptions import APIError, AuthError, NotFoundError, RateLimitError

DEFAULT_BASE_URL = "https://api.lobstr.io/v1/"
DEFAULT_TIMEOUT = 30.0


def _get_config_path() -> Path:
    """Get the lobstr config file path (matches lobstrio-cli)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "lobstr" / "config.toml"


def _resolve_token() -> str | None:
    """Resolve API token: LOBSTR_TOKEN env var -> config file."""
    env = os.environ.get("LOBSTR_TOKEN")
    if env:
        return env
    path = _get_config_path()
    if not path.exists():
        return None
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    return cfg.get("auth", {}).get("token")


def _extract_error_message(body: dict, fallback: str) -> str:
    """Extract error message from the API's various error response shapes."""
    # Shape 1: {"error": "message"}
    msg = body.get("error")
    if msg:
        return msg
    # Shape 2: {"errors": {"message": "...", "type": "...", "code": N}}
    errors = body.get("errors")
    if isinstance(errors, dict):
        msg = errors.get("message")
        if msg:
            return msg
    # Fallback
    return fallback


def _raise_for_status(resp: httpx.Response) -> None:
    """Raise typed exceptions for HTTP error responses."""
    if resp.status_code < 400:
        return

    body: dict = {}
    try:
        body = resp.json()
    except Exception:
        pass

    msg = _extract_error_message(body, resp.text)

    if resp.status_code == 401:
        raise AuthError(401, msg or "Authentication failed", body)
    if resp.status_code == 404:
        raise NotFoundError(404, msg or "Not found", body)
    if resp.status_code == 429:
        retry_after = resp.headers.get("retry-after")
        raise RateLimitError(429, msg or "Rate limited", body, retry_after=retry_after)
    raise APIError(resp.status_code, msg, body)
