from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _resolve_credits(value: Any) -> float | None:
    """Normalize credits fields that can be int, float, dict, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        v = value.get("current", value.get("legacy"))
        return float(v) if v is not None else None
    return None


@dataclass
class Crawler:
    """A scraping crawler (template)."""

    id: str
    name: str
    slug: str
    description: str | None
    credits_per_row: float | None
    credits_per_email: float | None
    max_concurrency: int
    account: bool
    has_email_verification: bool
    # `account` above is kept as a plain bool for backward compatibility — code
    # already checking `if crawler.account:` must not break. It cannot carry the
    # platform though: `linkedin-sync` and `sales-nav-sync` are both "LinkedIn"
    # to a human but distinct account types to the API, and attaching the wrong
    # one fails as a generic 404 (`AccountDoesNotExist` rewritten to
    # `HTTPNotFound`, indistinguishable from a bad hash). `account_type` is the
    # slug from ``account.type`` in the API response (`None` when the crawler
    # needs no account) — added here alongside `account` rather than replacing
    # it, so this widening cannot break an existing truthy/falsy check.
    is_public: bool
    is_premium: bool
    is_available: bool
    has_issues: bool
    rank: int | None
    # Detail-endpoint fields (None when from list endpoint)
    default_worker_stats: dict[str, Any] | None = None
    email_worker_stats: dict[str, Any] | None = None
    input_params: list[dict[str, Any]] = field(default_factory=list)
    result_fields: list[str] = field(default_factory=list)
    account_type: str | None = None
    # Untouched API payload, so callers that need a field the dataclass drops or
    # renames (e.g. the raw credits dict, or `result`/`input` under their API keys)
    # can still reach it.
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Crawler:
        return cls(
            raw=data,
            id=data["id"],
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            description=data.get("description"),
            credits_per_row=_resolve_credits(data.get("credits_per_row")),
            credits_per_email=_resolve_credits(data.get("credits_per_email")),
            max_concurrency=data.get("max_concurrency", 1),
            account=bool(data.get("account")),
            has_email_verification=data.get("has_email_verification", False),
            is_public=data.get("is_public", True),
            is_premium=data.get("is_premium", False),
            is_available=data.get("is_available", True),
            has_issues=data.get("has_issues", False),
            rank=data.get("rank"),
            default_worker_stats=data.get("default_worker_stats"),
            email_worker_stats=data.get("email_worker_stats"),
            input_params=data.get("input", []),
            result_fields=data.get("result", []),
            account_type=(
                data["account"].get("type")
                if isinstance(data.get("account"), dict)
                else None
            ),
        )


@dataclass
class CrawlerAttribute:
    """A result attribute (column) produced by a crawler."""

    name: str
    type: str
    example: Any
    function: str
    is_main: bool
    description: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CrawlerAttribute:
        return cls(
            name=data["name"],
            type=data.get("type", ""),
            example=data.get("example"),
            function=data.get("function", ""),
            is_main=data.get("is_main", False),
            description=data.get("description", ""),
        )


@dataclass
class CrawlerParams:
    """Parameters accepted by a crawler."""

    task_params: dict[str, Any]
    squid_params: dict[str, Any]
    functions: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CrawlerParams:
        task = data.get("task", {})
        squid = data.get("squid", {})
        # Functions may be nested inside squid params or at top level. Do NOT
        # mutate `squid` (it belongs to `data`, which we keep verbatim in `raw`).
        functions: dict[str, Any] = {}
        squid_params = squid
        if isinstance(squid, dict) and "functions" in squid:
            functions = squid["functions"]
            squid_params = {k: v for k, v in squid.items() if k != "functions"}
        return cls(
            task_params=task,
            squid_params=squid_params,
            functions=functions,
            raw=data,
        )
